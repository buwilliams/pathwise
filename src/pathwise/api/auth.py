from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from pathwise.api.deps import AuthServiceDep
from pathwise.core.auth import (
    CodeExpiredError,
    InvalidCodeError,
    RateLimitedError,
    TooManyAttemptsError,
)
from pathwise.core.ids import normalize_phone

router = APIRouter(prefix="/auth", tags=["auth"])


class StartCodeRequest(BaseModel):
    phone: str = Field(..., min_length=4, max_length=32)


class StartCodeResponse(BaseModel):
    sent: bool


class VerifyCodeRequest(BaseModel):
    phone: str
    code: str = Field(..., min_length=4, max_length=12)


class VerifyCodeResponse(BaseModel):
    session_token: str
    needs_onboarding: bool


def _normalize_or_400(phone: str) -> str:
    try:
        return normalize_phone(phone)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.post("/start", response_model=StartCodeResponse)
def start(req: StartCodeRequest, auth: AuthServiceDep) -> StartCodeResponse:
    phone = _normalize_or_400(req.phone)
    try:
        auth.start(phone)
    except RateLimitedError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)
        ) from exc
    return StartCodeResponse(sent=True)


@router.post("/verify", response_model=VerifyCodeResponse)
def verify(req: VerifyCodeRequest, auth: AuthServiceDep) -> VerifyCodeResponse:
    phone = _normalize_or_400(req.phone)
    try:
        result = auth.verify(phone, req.code)
    except (InvalidCodeError, CodeExpiredError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc
    except TooManyAttemptsError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)
        ) from exc
    return VerifyCodeResponse(
        session_token=result.session_token,
        needs_onboarding=result.needs_onboarding,
    )
