from __future__ import annotations

from dataclasses import asdict
from typing import Any, Literal

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from pathwise.api.deps import AuthServiceDep, CurrentUserId, ProfileServiceDep
from pathwise.core.ids import user_id_for_phone, normalize_phone

router = APIRouter(prefix="/me", tags=["profile"])


Gender = Literal["male", "female", "non-binary"]


class CreateProfileRequest(BaseModel):
    phone: str
    first_name: str = Field(..., min_length=1, max_length=64)
    gender: Gender
    zip_code: str | None = Field(default=None, max_length=10)


class UpdateProfileRequest(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=64)
    gender: Gender | None = None
    zip_code: str | None = Field(default=None, max_length=10)


class ProfileResponse(BaseModel):
    user_id: str
    first_name: str
    gender: Gender
    phone_e164: str
    zip_code: str | None
    created_at: float
    updated_at: float


@router.post("/onboard", response_model=ProfileResponse)
def onboard(
    req: CreateProfileRequest,
    profiles: ProfileServiceDep,
    user_id: CurrentUserId,
) -> ProfileResponse:
    try:
        phone_e164 = normalize_phone(req.phone)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if user_id_for_phone(phone_e164) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Phone does not match the verified session.",
        )
    try:
        profile = profiles.create(
            phone_e164=phone_e164,
            first_name=req.first_name,
            gender=req.gender,
            zip_code=req.zip_code,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ProfileResponse(**asdict(profile))


@router.get("", response_model=ProfileResponse)
def me(profiles: ProfileServiceDep, user_id: CurrentUserId) -> ProfileResponse:
    profile = profiles.get(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="No profile yet.")
    return ProfileResponse(**asdict(profile))


@router.patch("", response_model=ProfileResponse)
def update(
    req: UpdateProfileRequest,
    profiles: ProfileServiceDep,
    user_id: CurrentUserId,
) -> ProfileResponse:
    try:
        profile = profiles.update(
            user_id,
            first_name=req.first_name,
            gender=req.gender,
            zip_code=req.zip_code,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ProfileResponse(**asdict(profile))


@router.get("/seasons")
def my_seasons(
    user_id: CurrentUserId,
    profiles: ProfileServiceDep,
) -> dict[str, Any]:
    """Seasons this user has touched: plan counts, latest plan timestamp,
    whether any chat history exists. Drives the home page + history view.
    """
    from pathwise.api.deps import get_store
    from pathwise.core.season import list_packs, packs_root

    store = get_store()
    out = []
    for pack in list_packs(packs_root()):
        versions = store.list_plan_versions(user_id, pack.id)
        if not versions:
            continue
        latest_meta = store.read_json(
            store.plan_meta_path(user_id, pack.id, versions[-1])
        )
        chat_versions = sum(
            1
            for v in versions
            if store.chat_history_path(user_id, pack.id, v).exists()
        )
        out.append(
            {
                "season_id": pack.id,
                "name": pack.name,
                "summary": pack.summary,
                "age_min": pack.age_min,
                "age_max": pack.age_max,
                "plan_count": len(versions),
                "latest_version": versions[-1],
                "latest_at": latest_meta.get("generated_at"),
                "chat_count": chat_versions,
            }
        )
    return {"seasons": out}


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    profiles: ProfileServiceDep,
    auth: AuthServiceDep,
    user_id: CurrentUserId,
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """Permanently delete the current user's profile, answers, plans, events.

    Also revokes the bearer token used to make this request.
    """
    profiles.delete(user_id)
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[len("bearer ") :].strip()
        auth.revoke_session(token)
