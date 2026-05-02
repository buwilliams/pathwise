"""Research orchestration — turn profile + answers into a grounded numbers bundle.

The model is asked (via ``prompts/research.md``) to produce a single JSON
object with the structure described there. We parse defensively: if the model
wraps the JSON in markdown fences or adds prose, we extract the largest JSON
object substring.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from typing import Any

from pathwise.core.profile import Profile
from pathwise.core.season import SeasonPack
from pathwise.llm.client import call_with_research
from pathwise.llm.templates import render_template

logger = logging.getLogger(__name__)


@dataclass
class ResearchBundle:
    data: dict[str, Any]
    sources: list[str]
    raw_text: str
    usage: dict[str, int]

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def _extract_json(text: str) -> dict[str, Any]:
    """Pull the first balanced JSON object out of arbitrary model output."""
    # Strip ```json fences if present
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        candidate = fenced.group(1)
    else:
        # Find first '{' and walk to its matching '}'
        start = text.find("{")
        if start < 0:
            return {}
        depth = 0
        end = -1
        in_string = False
        escape = False
        for i, ch in enumerate(text[start:], start=start):
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end < 0:
            return {}
        candidate = text[start:end]

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        logger.warning("Research output was not valid JSON; returning empty bundle")
        return {}


def run_research(
    *,
    pack: SeasonPack,
    profile: Profile,
    answers: dict[str, Any],
    model: str,
) -> ResearchBundle:
    system_prompt = pack.prompt_path("system").read_text()
    user_prompt = render_template(
        pack.prompt_path("research"),
        {"profile": profile, "answers": answers, "pack": pack},
    )
    result = call_with_research(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
    )
    data = _extract_json(result.text)
    return ResearchBundle(
        data=data,
        sources=result.sources,
        raw_text=result.text,
        usage=result.usage,
    )
