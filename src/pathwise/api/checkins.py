"""Weekly check-in endpoints.

The longitudinal-policy loop (roadmap.md #1): users post a tiny
observation now and then; the system records it and tells them whether
any component of their life-state has been drifting downward long enough
to be worth a re-think. See ``core/checkin.py``.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from pathwise.api.deps import CurrentUserId, StoreDep
from pathwise.core.checkin import (
    DEFAULT_FALLING_STREAK,
    KNOWN_COMPONENTS,
    CheckinError,
    CheckinService,
)

router = APIRouter(
    prefix="/seasons/{season_id}/checkins",
    tags=["checkins"],
)


class CheckinRequest(BaseModel):
    b: float | None = Field(
        default=None, ge=0, le=168, description="Buffer hours per week"
    )
    eta: float | None = Field(
        default=None, ge=-2, le=2, description="Net emotional impact (-2..+2)"
    )
    zeta: float | None = Field(
        default=None, ge=1, le=5, description="Fitness practice (1..5)"
    )
    q: float | None = Field(
        default=None, ge=1, le=5, description="Quality of time / energy (1..5)"
    )
    note: str | None = Field(default=None, max_length=500)


def _observations(req: CheckinRequest) -> dict[str, float]:
    raw = {k: getattr(req, k) for k in KNOWN_COMPONENTS}
    return {k: v for k, v in raw.items() if v is not None}


@router.post("")
def record(
    season_id: str,
    req: CheckinRequest,
    store: StoreDep,
    user_id: CurrentUserId,
) -> dict[str, Any]:
    obs = _observations(req)
    if not obs:
        raise HTTPException(
            status_code=400,
            detail="provide at least one of: " + ", ".join(KNOWN_COMPONENTS),
        )
    try:
        checkin = CheckinService(store).record(
            user_id=user_id,
            season_id=season_id,
            observations=obs,
            note=req.note,
        )
    except CheckinError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "at": checkin.at,
        "observations": checkin.observations,
        "note": checkin.note,
    }


@router.get("")
def list_checkins(
    season_id: str,
    store: StoreDep,
    user_id: CurrentUserId,
    limit: int = Query(default=50, ge=1, le=500),
) -> dict[str, Any]:
    checkins = CheckinService(store).list(user_id, season_id)
    trimmed = checkins[-limit:]
    return {
        "checkins": [
            {
                "at": c.at,
                "observations": c.observations,
                "note": c.note,
            }
            for c in trimmed
        ],
        "total": len(checkins),
    }


@router.get("/drift")
def drift(
    season_id: str,
    store: StoreDep,
    user_id: CurrentUserId,
    falling_streak: int = Query(default=DEFAULT_FALLING_STREAK, ge=2, le=10),
) -> dict[str, Any]:
    report = CheckinService(store).drift(
        user_id, season_id, falling_streak=falling_streak
    )
    return report.to_jsonable()
