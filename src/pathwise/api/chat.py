from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from pathwise.api.deps import CurrentUserId, StoreDep
from pathwise.core.chat import ChatError, ChatService, render_chat_for_prompt
from pathwise.core.plan import PlanError, generate_plan
from pathwise.core.profile import ProfileService

router = APIRouter(
    prefix="/seasons/{season_id}/plans/{version}/chat",
    tags=["chat"],
)


class SendMessageRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)


@router.get("")
def history(
    season_id: str, version: int, store: StoreDep, user_id: CurrentUserId
) -> dict[str, Any]:
    chat = ChatService(store)
    turns = chat.history(user_id, season_id, version)
    return {"turns": [asdict(t) for t in turns]}


@router.post("")
def send(
    season_id: str,
    version: int,
    req: SendMessageRequest,
    store: StoreDep,
    user_id: CurrentUserId,
) -> dict[str, Any]:
    chat = ChatService(store)
    try:
        assistant = chat.send(
            user_id=user_id,
            season_id=season_id,
            version=version,
            user_text=req.text,
        )
    except ChatError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"assistant": asdict(assistant)}


@router.post("/regenerate")
def regenerate(
    season_id: str,
    version: int,
    store: StoreDep,
    user_id: CurrentUserId,
) -> dict[str, Any]:
    """Generate a new plan version that folds in the conversation about plan v.

    The chat history attached to plan v becomes the seed for plan v+1. Old plan
    + chat stay in history; the user lands on the new plan.
    """
    profile = ProfileService(store).get(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="No profile.")

    chat = ChatService(store)
    turns = chat.history(user_id, season_id, version)
    if not any(t.role == "user" for t in turns):
        raise HTTPException(
            status_code=400,
            detail="No conversation to regenerate from. Ask a question first.",
        )

    chat_context = render_chat_for_prompt(turns, profile.first_name)
    try:
        new_plan = generate_plan(
            user_id=user_id,
            season_id=season_id,
            store=store,
            chat_context=chat_context,
        )
    except PlanError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "version": new_plan.version,
        "markdown": new_plan.markdown,
        "sources": new_plan.sources,
    }
