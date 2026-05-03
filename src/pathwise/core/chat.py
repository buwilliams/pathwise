"""Post-plan chat: user can talk to Claude about their generated plan.

The system prompt is the season's voice + the full Emma life-strategy essay
+ their plan markdown + the structured meta (life-state, scored scenarios,
research bundle). All cached so every follow-up turn after the first is cheap.

Conversation history is persisted as a JSONL log per (user, season, version)
so refresh / new-device works without losing context.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from pathwise.config import Settings, get_settings
from pathwise.core.plan import read_plan
from pathwise.core.profile import ProfileService
from pathwise.core.season import SeasonPack, get_pack
from pathwise.core.store import FileStore
from pathwise.llm.client import call_chat

logger = logging.getLogger(__name__)


class ChatError(Exception):
    pass


@dataclass
class ChatTurn:
    role: str  # "user" | "assistant"
    text: str
    at: float


def render_chat_for_prompt(turns: list["ChatTurn"], first_name: str) -> str:
    """Format a chat history as a transcript for inclusion in the plan prompt."""
    if not turns:
        return ""
    lines: list[str] = []
    for t in turns:
        speaker = first_name if t.role == "user" else "Planner"
        lines.append(f"**{speaker}:** {t.text.strip()}")
    return "\n\n".join(lines)


def _pack_model_essay(pack: SeasonPack) -> str:
    """Load the season's formalized-conjecture markdown if present.

    Each revision bundles its model at ``model.md`` at the revision root.
    Returns an empty string if no essay is bundled.
    """
    path = pack.pack_dir / "model.md"
    return path.read_text() if path.exists() else ""


def _build_system_prompt(
    pack: SeasonPack,
    plan_text: str,
    plan_meta: dict[str, Any],
    profile_first_name: str,
) -> str:
    """Compose the cached system block.

    Order matters for cache stability: nothing dynamic before the last byte.
    Render: voice → essay → plan markdown → structured meta → chat rules.
    """
    voice = pack.prompt_path("system").read_text()
    essay = _pack_model_essay(pack)

    import json

    meta_view = {
        "version": plan_meta.get("version"),
        "life_state": plan_meta.get("life_state"),
        "scored_scenarios": plan_meta.get("scored_scenarios"),
        "research_data": plan_meta.get("research_data"),
        "sources": plan_meta.get("sources"),
    }

    return f"""{voice}

# The full life-strategy model (reference)

You operate on the model below. Use it to ground your reasoning when {profile_first_name} asks "why" or "what if".

---

{essay}

---

# {profile_first_name}'s plan (v{plan_meta.get("version", "?")})

This is the plan they're looking at right now. They may ask you to clarify, push back, or explore alternatives. Stay consistent with it unless they give you new information that changes the math.

---

{plan_text}

---

# What we computed for them (structured)

```json
{json.dumps(meta_view, indent=2, sort_keys=True, default=str)}
```

# How to chat with them

- They've already read the plan. Don't re-explain it unless they ask. Answer the actual question.
- Be brief. Most replies should be 2-5 sentences. Lists only when they help.
- If they're considering a tradeoff, do the math out loud with their real numbers from above. Don't make up new numbers.
- If they push toward something the plan flagged as not-viable, name the specific failure (cash flow, buffer, time) and what would have to change for it to pencil.
- If they push back on the recommended path, treat it as a signal that an assumption may be wrong — re-derive from their numbers and the falsifiability conditions in the essay; don't just defend the current recommendation.
- When discussing a choice, name its recoverability in passing when relevant (e.g. "this one's easy to step back from" / "this one's hard to undo"). Recoverability is a real factor, not a footnote.
- If they ask something the plan + research can't answer (e.g. "is X program any good?"), say what you do know, and tell them what they'd need to find out.
- Use their first name occasionally, not every turn.
"""


class ChatService:
    """Load/append history, call the LLM, return + persist the assistant turn."""

    def __init__(self, store: FileStore, settings: Settings | None = None) -> None:
        self.store = store
        self.settings = settings or get_settings()

    def history(
        self, user_id: str, season_id: str, version: int
    ) -> list[ChatTurn]:
        path = self.store.chat_history_path(user_id, season_id, version)
        records = self.store.read_jsonl(path)
        return [
            ChatTurn(role=r["role"], text=r["text"], at=r["at"])
            for r in records
            if r.get("role") in ("user", "assistant") and r.get("text")
        ]

    def send(
        self,
        *,
        user_id: str,
        season_id: str,
        version: int,
        user_text: str,
    ) -> ChatTurn:
        if not user_text.strip():
            raise ChatError("Empty message.")

        profile = ProfileService(self.store).get(user_id)
        if profile is None:
            raise ChatError(f"No profile for user_id={user_id}")

        # Confirms plan exists and gives us markdown + meta for the prompt.
        try:
            plan_text, plan_meta = read_plan(user_id, season_id, version, self.store)
        except Exception as exc:
            raise ChatError(f"Plan v{version} not found.") from exc

        # Route to the same revision the plan was generated under, so the
        # voice / system prompt / model essay match what the user has been
        # reading. Falls back to latest only if a pre-revision plan slipped
        # through the backfill.
        plan_revision = plan_meta.get("pack_version")
        pack = get_pack(season_id, revision=plan_revision)

        history = self.history(user_id, season_id, version)
        # Append the new user turn before calling so it's in-context
        api_messages: list[dict[str, Any]] = [
            {"role": t.role, "content": t.text} for t in history
        ]
        api_messages.append({"role": "user", "content": user_text.strip()})

        system_prompt = _build_system_prompt(
            pack=pack,
            plan_text=plan_text,
            plan_meta=plan_meta,
            profile_first_name=profile.first_name,
        )

        result = call_chat(
            system_prompt=system_prompt,
            messages=api_messages,
            model=self.settings.pathwise_chat_model,
        )

        now = time.time()
        path = self.store.chat_history_path(user_id, season_id, version)
        # Persist user turn first, then assistant turn — preserves causal order
        # if anything goes wrong between them.
        self.store.append_jsonl(
            path,
            {
                "role": "user",
                "text": user_text.strip(),
                "at": now,
                "pack_version": pack.version,
            },
        )
        assistant = ChatTurn(role="assistant", text=result.text, at=time.time())
        self.store.append_jsonl(
            path,
            {
                "role": "assistant",
                "text": assistant.text,
                "at": assistant.at,
                "usage": result.usage,
                "pack_version": pack.version,
            },
        )
        return assistant
