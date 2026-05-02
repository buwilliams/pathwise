from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status

from pathwise.api.deps import CurrentUserId, StoreDep
from pathwise.core.plan import (
    PlanError,
    PlanJobAlreadyRunning,
    list_plans,
    plan_job_status,
    read_plan,
    start_plan_job,
)

router = APIRouter(prefix="/seasons/{season_id}/plans", tags=["plans"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def create(
    season_id: str, store: StoreDep, user_id: CurrentUserId
) -> dict[str, Any]:
    """Kick off plan generation in the background. Returns immediately with
    the job's start time. Poll GET /status to track progress.
    """
    try:
        return start_plan_job(
            user_id=user_id, season_id=season_id, store=store
        )
    except PlanJobAlreadyRunning as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except PlanError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/status")
def status_endpoint(
    season_id: str, store: StoreDep, user_id: CurrentUserId
) -> dict[str, Any]:
    """Polling endpoint. Returns whether a plan job is in flight and (when
    not generating) the latest plan version + the most recent failure error.
    """
    return plan_job_status(user_id, season_id, store)


@router.get("")
def index(season_id: str, store: StoreDep, user_id: CurrentUserId) -> dict[str, Any]:
    versions = list_plans(user_id, season_id, store)
    enriched = []
    for v in versions:
        meta = store.read_json(store.plan_meta_path(user_id, season_id, v))
        chat_path = store.chat_history_path(user_id, season_id, v)
        chat_msgs = 0
        if chat_path.exists():
            chat_msgs = len(store.read_jsonl(chat_path))
        enriched.append(
            {
                "version": v,
                "generated_at": meta.get("generated_at"),
                "model_plan": meta.get("model_plan"),
                "chat_messages": chat_msgs,
            }
        )
    return {"versions": enriched}


@router.get("/latest")
def latest(season_id: str, store: StoreDep, user_id: CurrentUserId) -> dict[str, Any]:
    versions = list_plans(user_id, season_id, store)
    if not versions:
        raise HTTPException(status_code=404, detail="No plans generated yet.")
    return _read(season_id, versions[-1], store, user_id)


@router.get("/{version}")
def show(
    season_id: str, version: int, store: StoreDep, user_id: CurrentUserId
) -> dict[str, Any]:
    versions = list_plans(user_id, season_id, store)
    if version not in versions:
        raise HTTPException(status_code=404, detail=f"Plan v{version} not found.")
    return _read(season_id, version, store, user_id)


def _read(season_id: str, version: int, store: Any, user_id: str) -> dict[str, Any]:
    markdown, meta = read_plan(user_id, season_id, version, store)
    return {"version": version, "markdown": markdown, "meta": meta}
