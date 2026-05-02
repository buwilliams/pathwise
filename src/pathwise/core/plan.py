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
import threading
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


# A lock file older than this is treated as a crashed job and cleaned up
# on the next status check. 15 min covers a slow Opus + research pipeline
# with comfortable headroom.
STALE_LOCK_AGE_SECONDS = 15 * 60


class PlanError(Exception):
    pass


class PlanJobAlreadyRunning(PlanError):
    """Raised when a plan-generation job is requested while one is in flight
    for the same (user, season). Maps to HTTP 409 in the API layer."""


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
    chat_context: str | None = None,
) -> GeneratedPlan:
    """Generate a new plan version.

    ``research_bundle`` lets callers (and tests) inject a pre-built bundle and
    skip the live LLM web-search call.

    ``chat_context`` is an optional pre-rendered transcript of the conversation
    the user had about the previous plan version. When present, it's threaded
    into the synthesis prompt so the new plan reflects what was discussed.
    """
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

    # Group scored scenarios by named path bucket for the three-paths output.
    paths_by_bucket: dict[str, list[Any]] = {
        "fast_freedom": [],
        "compounding_freedom": [],
        "skill_leverage": [],
    }
    for s in scored:
        paths_by_bucket.setdefault(s.bucket, []).append(s)

    plan_prompt = render_template(
        pack.prompt_path("plan"),
        {
            "profile": profile,
            "answers": answers,
            "questions": pack.questions,
            "life_state": _life_state_view(life),
            "research_json": _pretty_json(research_bundle.data),
            "scored_scenarios": scored,
            "paths_by_bucket": paths_by_bucket,
            "format_answer": _format_answer,
            "chat_context": chat_context or "",
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


_HOME_EMOTIONAL_LABELS = {0.0: "peaceful", 1.0: "fine", 2.0: "tense", 3.0: "hard"}


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
        "home_emotional_cost": life.home_emotional_cost,
        "home_emotional_label": _HOME_EMOTIONAL_LABELS.get(
            life.home_emotional_cost, "fine"
        ),
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


# ---------------------------------------------------------------------------
# Async plan-generation jobs
# ---------------------------------------------------------------------------


def _record_failure(
    *,
    store: FileStore,
    jobs_log_path: Any,
    started: float,
    error: str,
    chat_context: bool = False,
) -> None:
    store.append_jsonl(
        jobs_log_path,
        {
            "started_at": started,
            "finished_at": time.time(),
            "status": "failed",
            "error": error,
            "from_chat": chat_context,
        },
    )


def _clear_stale_lock(
    *,
    store: FileStore,
    lock_path: Any,
    jobs_log_path: Any,
    existing: dict[str, Any],
) -> None:
    """A lock file older than the threshold means the server probably died
    mid-job. Record the failure and clean up so a fresh job can start."""
    _record_failure(
        store=store,
        jobs_log_path=jobs_log_path,
        started=existing.get("started_at", time.time()),
        error="Server appears to have crashed mid-job (lock file is stale).",
        chat_context=bool(existing.get("from_chat")),
    )
    lock_path.unlink(missing_ok=True)


def _run_plan_job(
    *,
    user_id: str,
    season_id: str,
    store: FileStore,
    settings: Settings,
    chat_context: str | None,
    lock_path: Any,
    jobs_log_path: Any,
    started: float,
) -> None:
    """Worker thread body. Runs synchronously; success removes the lock and
    appends a success record. Any exception is caught + recorded so the
    status endpoint can surface it."""
    try:
        result = generate_plan(
            user_id=user_id,
            season_id=season_id,
            store=store,
            settings=settings,
            chat_context=chat_context,
        )
        store.append_jsonl(
            jobs_log_path,
            {
                "started_at": started,
                "finished_at": time.time(),
                "status": "succeeded",
                "version": result.version,
                "from_chat": chat_context is not None,
            },
        )
    except Exception as exc:
        logger.exception("plan_job failed user=%s season=%s", user_id, season_id)
        _record_failure(
            store=store,
            jobs_log_path=jobs_log_path,
            started=started,
            error=str(exc),
            chat_context=chat_context is not None,
        )
    finally:
        lock_path.unlink(missing_ok=True)


def start_plan_job(
    *,
    user_id: str,
    season_id: str,
    store: FileStore,
    settings: Settings | None = None,
    chat_context: str | None = None,
) -> dict[str, Any]:
    """Kick off a plan-generation job in a background thread. Returns
    immediately with the job's start time. Raises PlanJobAlreadyRunning if
    a non-stale job is already in flight for this (user, season).
    """
    settings = settings or get_settings()
    lock_path = store.plan_job_lock_path(user_id, season_id)
    jobs_log_path = store.plan_jobs_log_path(user_id, season_id)

    existing = store.read_json(lock_path)
    if existing:
        age = time.time() - existing.get("started_at", 0)
        if age < STALE_LOCK_AGE_SECONDS:
            raise PlanJobAlreadyRunning(
                f"A plan is already being generated for this season "
                f"(started ~{int(age)}s ago)."
            )
        _clear_stale_lock(
            store=store, lock_path=lock_path,
            jobs_log_path=jobs_log_path, existing=existing,
        )

    started = time.time()
    store.write_json(
        lock_path,
        {
            "started_at": started,
            "season_id": season_id,
            "from_chat": chat_context is not None,
        },
    )

    threading.Thread(
        target=_run_plan_job,
        kwargs={
            "user_id": user_id,
            "season_id": season_id,
            "store": store,
            "settings": settings,
            "chat_context": chat_context,
            "lock_path": lock_path,
            "jobs_log_path": jobs_log_path,
            "started": started,
        },
        daemon=True,
        name=f"plan-job-{user_id[:8]}-{season_id}",
    ).start()

    return {
        "started_at": started,
        "season_id": season_id,
        "from_chat": chat_context is not None,
    }


def plan_job_status(
    user_id: str, season_id: str, store: FileStore
) -> dict[str, Any]:
    """Current state of plan generation for a (user, season).

    Returns either:
        {generating: True,  started_at, from_chat}
        {generating: False, latest_version, last_error}

    Stale locks are auto-cleared on read so the next call sees a clean state.
    """
    lock_path = store.plan_job_lock_path(user_id, season_id)
    jobs_log_path = store.plan_jobs_log_path(user_id, season_id)

    existing = store.read_json(lock_path)
    if existing:
        age = time.time() - existing.get("started_at", 0)
        if age < STALE_LOCK_AGE_SECONDS:
            return {
                "generating": True,
                "started_at": existing.get("started_at"),
                "from_chat": bool(existing.get("from_chat")),
                "last_error": None,
            }
        _clear_stale_lock(
            store=store, lock_path=lock_path,
            jobs_log_path=jobs_log_path, existing=existing,
        )

    versions = store.list_plan_versions(user_id, season_id)
    history = store.read_jsonl(jobs_log_path)
    last_error: str | None = None
    if history:
        last = history[-1]
        if last.get("status") == "failed":
            last_error = last.get("error")
    return {
        "generating": False,
        "latest_version": versions[-1] if versions else None,
        "last_error": last_error,
    }
