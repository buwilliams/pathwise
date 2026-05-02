from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from pathwise.api.deps import CurrentUserId, StoreDep
from pathwise.core.questionnaire import (
    AnswerValidationError,
    QuestionnaireService,
)
from pathwise.core.season import get_pack

router = APIRouter(prefix="/seasons/{season_id}/answers", tags=["questionnaire"])


class SetAnswersRequest(BaseModel):
    answers: dict[str, Any] = Field(default_factory=dict)


@router.get("")
def get_answers(
    season_id: str, store: StoreDep, user_id: CurrentUserId
) -> dict[str, Any]:
    try:
        pack = get_pack(season_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    qs = QuestionnaireService(store)
    answers = qs.get_answers(user_id, pack.id)
    completion = qs.completion(user_id, pack)
    return {"answers": answers, "completion": asdict(completion)}


@router.put("")
def put_answers(
    season_id: str,
    req: SetAnswersRequest,
    store: StoreDep,
    user_id: CurrentUserId,
) -> dict[str, Any]:
    try:
        pack = get_pack(season_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    qs = QuestionnaireService(store)
    try:
        merged = qs.set_answers(user_id, pack, req.answers)
    except (AnswerValidationError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    completion = qs.completion(user_id, pack)
    return {"answers": merged, "completion": asdict(completion)}
