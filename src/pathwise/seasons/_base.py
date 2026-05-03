"""Per-revision logic surface.

Each season revision lives in its own directory under
``seasons/<season>/revisions/<rev>/`` and ships a ``logic.py`` exporting
``make_logic() -> SeasonLogic``. ``SeasonLogic`` binds the loaded ``SeasonPack``
to whatever per-revision behavior that revision needs.

``BaseLogic`` is the default for revisions whose math matches the original
build-independence v0_4_0 model. New models with different state shapes
override the relevant methods.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from pathwise.core.season import SeasonPack, load_pack


class SeasonLogic(Protocol):
    pack: SeasonPack

    def compute_life_state(self, answers: dict[str, Any]) -> Any: ...

    def score(self, life: Any, research_data: dict[str, Any]) -> list[Any]: ...

    def build_plan_context(
        self,
        *,
        profile: Any,
        answers: dict[str, Any],
        life: Any,
        scored: list[Any],
        research_data: dict[str, Any],
        chat_context: str,
    ) -> dict[str, Any]: ...


class BaseLogic:
    """Default per-revision logic. Delegates everything to ``core/``.

    Revisions that don't need to change behavior subclass this with no
    overrides and just set ``REVISION_DIR``. Revisions that change the
    model override ``compute_life_state``, ``score``, and
    ``build_plan_context`` as needed.
    """

    REVISION_DIR: Path

    def __init__(self, pack: SeasonPack) -> None:
        self.pack = pack
        # Back-reference so callers with a SeasonPack can reach behavior.
        pack.logic = self

    @classmethod
    def make(cls) -> "BaseLogic":
        pack = load_pack(cls.REVISION_DIR)
        return cls(pack)

    def compute_life_state(self, answers: dict[str, Any]) -> Any:
        from pathwise.core.life_state import compute_life_state

        return compute_life_state(answers)

    def score(self, life: Any, research_data: dict[str, Any]) -> list[Any]:
        from pathwise.core.momentum import score_all

        return score_all(self.pack.scenarios, life, self.pack.weights, research_data)

    def build_plan_context(
        self,
        *,
        profile: Any,
        answers: dict[str, Any],
        life: Any,
        scored: list[Any],
        research_data: dict[str, Any],
        chat_context: str,
    ) -> dict[str, Any]:
        """Default v0_4_0-style context builder. Returns the dict that will
        be handed to the plan-prompt template."""
        from pathwise.core.plan import _format_answer, _pretty_json, _question_views

        paths_by_bucket: dict[str, list[Any]] = {
            "fast_freedom": [],
            "compounding_freedom": [],
            "skill_leverage": [],
        }
        for s in scored:
            paths_by_bucket.setdefault(s.bucket, []).append(s)

        return {
            "profile": profile,
            "answers": answers,
            "questions": _question_views(self.pack, answers),
            "life_state": self.life_state_to_meta(life),
            "research_json": _pretty_json(research_data),
            "scored_scenarios": scored,
            "paths_by_bucket": paths_by_bucket,
            "format_answer": _format_answer,
            "chat_context": chat_context,
        }

    def life_state_to_meta(self, life: Any) -> dict[str, Any]:
        """JSON-friendly view of the life-state. Override per revision."""
        from pathwise.core.plan import _life_state_view

        return _life_state_view(life)

    def scored_to_meta(self, scored: list[Any]) -> list[dict[str, Any]]:
        """JSON-friendly view of the scored items. Override per revision."""
        out: list[dict[str, Any]] = []
        for s in scored:
            out.append({
                "id": s.id,
                "label": s.label,
                "viable": s.viable,
                "fails": s.fails,
                "momentum": s.momentum,
                "cash_flow_monthly": s.cash_flow_monthly,
                "buffer_months": s.risk_buffer_months,
                "income_monthly": s.income_monthly,
            })
        return out
