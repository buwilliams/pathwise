from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException

from pathwise.core.season import get_pack, list_packs, packs_root

router = APIRouter(prefix="/seasons", tags=["seasons"])


def _pack_summary(p: Any) -> dict[str, Any]:
    return {
        "id": p.id,
        "name": p.name,
        "summary": p.summary,
        "version": p.version,
        "age_min": p.age_min,
        "age_max": p.age_max,
    }


@router.get("")
def list_all() -> list[dict[str, Any]]:
    return [_pack_summary(p) for p in list_packs(packs_root())]


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
