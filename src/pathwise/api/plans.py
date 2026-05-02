from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from pathwise.api.deps import CurrentUserId, StoreDep
from pathwise.core.plan import (
    PlanError,
    generate_plan,
    list_plans,
    read_plan,
)

router = APIRouter(prefix="/seasons/{season_id}/plans", tags=["plans"])


@router.post("")
def create(season_id: str, store: StoreDep, user_id: CurrentUserId) -> dict[str, Any]:
    try:
        result = generate_plan(user_id=user_id, season_id=season_id, store=store)
    except PlanError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "version": result.version,
        "markdown": result.markdown,
        "sources": result.sources,
    }


@router.get("")
def index(season_id: str, store: StoreDep, user_id: CurrentUserId) -> dict[str, Any]:
    versions = list_plans(user_id, season_id, store)
    return {"versions": versions}


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
