from __future__ import annotations

from dataclasses import asdict
from typing import Literal

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
