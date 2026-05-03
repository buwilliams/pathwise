from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException

from pathwise.core.season import (
    SeasonPack,
    get_pack,
    latest_revision,
    list_revisions,
    list_seasons,
)

router = APIRouter(prefix="/seasons", tags=["seasons"])


def _pack_summary(p: SeasonPack) -> dict[str, Any]:
    return {
        "id": p.id,
        "name": p.name,
        "summary": p.summary,
        "version": p.version,
        "revision": p.revision,
        "available_revisions": list_revisions(p.id),
        "age_min": p.age_min,
        "age_max": p.age_max,
    }


@router.get("")
def list_all() -> list[dict[str, Any]]:
    return [
        {
            "id": s.id,
            "name": s.name,
            "summary": s.summary,
            "version": s.version,
            "revision": s.revision,
            "available_revisions": s.available_revisions,
            "age_min": s.age_min,
            "age_max": s.age_max,
        }
        for s in list_seasons()
    ]


@router.get("/{season_id}")
def show(season_id: str) -> dict[str, Any]:
    try:
        p = get_pack(season_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {**_pack_summary(p), "sections": [asdict(s) for s in p.sections]}


@router.get("/{season_id}/questions")
def questions(season_id: str) -> dict[str, Any]:
    try:
        p = get_pack(season_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "season_id": p.id,
        "revision": p.revision,
        "sections": [asdict(s) for s in p.sections],
        "questions": [
            {
                "key": q.key,
                "section": q.section,
                "type": q.type,
                "prompt": q.prompt,
                "help": q.help,
                "required": q.required,
                "options": [asdict(o) for o in q.options] if q.options else None,
                "min": q.min,
                "max": q.max,
                "unit": q.unit,
                "placeholder": q.placeholder,
            }
            for q in p.questions
        ],
    }


@router.get("/{season_id}/revision")
def revision_info(season_id: str) -> dict[str, Any]:
    """Just the revision metadata. Cheaper than /seasons/{id} when the UI
    only needs to know what the latest revision is and what's available."""
    try:
        latest = latest_revision(season_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "season_id": season_id,
        "latest_revision": latest,
        "available_revisions": list_revisions(season_id),
    }
