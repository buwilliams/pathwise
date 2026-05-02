"""End-to-end plan generation orchestrator.

Pipeline:
    answers + profile + season pack
    → deterministic life-state                          (life_state.py)
    → LLM web-search research bundle                    (llm/research.py)
    → deterministic scenario instantiation + scoring    (momentum.py)
    → LLM plan synthesis                                (llm/client.call_plain)
    → versioned save (plan_vN.md + plan_vN.meta.json)
"""

from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass
from typing import Any

from pathwise.config import Settings, get_settings
from pathwise.core.life_state import compute_life_state
from pathwise.core.momentum import score_all
from pathwise.core.profile import Profile, ProfileService
from pathwise.core.questionnaire import QuestionnaireService
from pathwise.core.season import SeasonPack, get_pack
from pathwise.core.store import FileStore
from pathwise.llm.client import call_plain
from pathwise.llm.research import ResearchBundle, run_research
from pathwise.llm.templates import render_template

logger = logging.getLogger(__name__)


class PlanError(Exception):
    pass


@dataclass
class GeneratedPlan:
    version: int
    markdown: str
    sources: list[str]
    meta_path: str
    plan_path: str


def _format_answer(question: Any, value: Any) -> str:
    """Pretty-print an answer value for display in a prompt."""
    if value is True:
        return "yes"
    if value is False:
        return "no"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    if question.type == "money":
        return f"${value:,}"
    return str(value)


def generate_plan(
    *,
    user_id: str,
    season_id: str,
    store: FileStore,
    settings: Settings | None = None,
    research_bundle: ResearchBundle | None = None,
    skip_research: bool = False,
) -> GeneratedPlan:
    """Generate a new plan version. ``research_bundle`` lets callers (and tests)
    inject a pre-built bundle and skip the live LLM web-search call."""
    settings = settings or get_settings()

    profile_service = ProfileService(store)
    profile = profile_service.get(user_id)
    if profile is None:
        raise PlanError(f"No profile for user_id={user_id}")

    pack = get_pack(season_id)

    qs = QuestionnaireService(store)
    answers = qs.get_answers(user_id, pack.id)
    completion = qs.completion(user_id, pack)
    if not completion.is_complete:
        raise PlanError(
            f"Questionnaire incomplete: missing required keys "
            f"{completion.missing_required}"
        )

    life = compute_life_state(answers)

    started = time.monotonic()
    logger.info(
        "plan.generate start user=%s season=%s plan_model=%s research_model=%s skip_research=%s",
        user_id, pack.id, settings.pathwise_plan_model,
        settings.pathwise_research_model, skip_research,
    )

    if research_bundle is None and not skip_research:
        research_bundle = run_research(
            pack=pack,
            profile=profile,
            answers=answers,
            model=settings.pathwise_research_model,
        )
        # Cache the research bundle for transparency / debugging
        ts = time.strftime("%Y-%m-%dT%H-%M-%S")
        research_path = store.research_dir(user_id, pack.id) / f"{ts}.json"
        store.write_json(research_path, research_bundle.to_json())
    elif research_bundle is None:
        logger.info("plan.generate skipping research (skip_research=True)")
        research_bundle = ResearchBundle(data={}, sources=[], raw_text="", usage={})

    scored = score_all(pack.scenarios, life, pack.weights, research_bundle.data)
    logger.info("plan.generate scored %d scenarios", len(scored))

    plan_prompt = render_template(
        pack.prompt_path("plan"),
        {
            "profile": profile,
            "answers": answers,
            "questions": pack.questions,
            "life_state": _life_state_view(life),
            "research_json": _pretty_json(research_bundle.data),
            "scored_scenarios": scored,
            "format_answer": _format_answer,
        },
    )

    system_prompt = pack.prompt_path("system").read_text()
    result = call_plain(
        system_prompt=system_prompt,
        user_prompt=plan_prompt,
        model=settings.pathwise_plan_model,
    )

    version = store.next_plan_version(user_id, pack.id)
    plan_path = store.plan_path(user_id, pack.id, version)
    meta_path = store.plan_meta_path(user_id, pack.id, version)

    store.write_text(plan_path, result.text)
    store.write_json(
        meta_path,
        {
            "version": version,
            "generated_at": time.time(),
            "season_id": pack.id,
            "pack_version": pack.version,
            "model_plan": settings.pathwise_plan_model,
            "model_research": settings.pathwise_research_model,
            "sources": research_bundle.sources,
            "research_data": research_bundle.data,
            "life_state": _life_state_view(life),
            "scored_scenarios": [
                {
                    "id": s.id,
                    "label": s.label,
                    "viable": s.viable,
                    "fails": s.fails,
                    "momentum": s.momentum,
                    "cash_flow_monthly": s.cash_flow_monthly,
                    "buffer_months": s.risk_buffer_months,
                    "income_monthly": s.income_monthly,
                }
                for s in scored
            ],
            "usage_research": research_bundle.usage,
            "usage_plan": result.usage,
        },
    )
    store.append_jsonl(
        store.events_path(user_id),
        {
            "event": "plan.generated",
            "at": time.time(),
            "season_id": pack.id,
            "version": version,
        },
    )
    logger.info(
        "plan.generate done user=%s season=%s v=%d in %.1fs",
        user_id, pack.id, version, time.monotonic() - started,
    )

    return GeneratedPlan(
        version=version,
        markdown=result.text,
        sources=research_bundle.sources,
        meta_path=str(meta_path),
        plan_path=str(plan_path),
    )


# ---------------------------------------------------------------------------
# View helpers (kept here so the orchestrator owns the prompt-context shape)
# ---------------------------------------------------------------------------


def _life_state_view(life: Any) -> dict[str, Any]:
    return {
        "cash_flow_monthly": round(life.cash_flow_monthly, 0),
        "assets": round(life.assets, 0),
        "monthly_obligations": round(life.monthly_obligations, 0),
        "risk_buffer_months": round(life.risk_buffer_months, 1),
        "buffer_status": life.buffer_status,
        "productive_time_band": life.productive_time_band,
        "current_income_monthly": round(life.current_income_monthly, 0),
        "top_value": life.top_value,
        "move_out_urgency": life.move_out_urgency,
        "has_car": life.has_car,
        "lives_with_parents": life.lives_with_parents,
        "emergency_fund_floor": round(life.emergency_fund_floor, 0),
        "monthly_pressure_comfort": life.monthly_pressure_comfort,
        "interested_in_training": life.interested_in_training,
    }


def _pretty_json(data: dict[str, Any]) -> str:
    import json

    return json.dumps(data, indent=2, sort_keys=True)


def list_plans(user_id: str, season_id: str, store: FileStore) -> list[int]:
    return store.list_plan_versions(user_id, season_id)


def read_plan(
    user_id: str, season_id: str, version: int, store: FileStore
) -> tuple[str, dict[str, Any]]:
    text = store.read_text(store.plan_path(user_id, season_id, version))
    meta = store.read_json(store.plan_meta_path(user_id, season_id, version))
    return text, meta
