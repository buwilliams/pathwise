from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from pathwise.config import Settings, get_settings
from pathwise.core.auth import AuthService
from pathwise.core.profile import ProfileService
from pathwise.core.store import FileStore
from pathwise.verify.factory import build_verifier


@lru_cache(maxsize=1)
def get_store() -> FileStore:
    return FileStore(get_settings().users_dir)


@lru_cache(maxsize=1)
def get_profile_service() -> ProfileService:
    return ProfileService(get_store())


@lru_cache(maxsize=1)
def get_auth_service() -> AuthService:
    settings = get_settings()
    store = get_store()
    return AuthService(store, settings, build_verifier(settings, store))


SettingsDep = Annotated[Settings, Depends(get_settings)]
StoreDep = Annotated[FileStore, Depends(get_store)]
ProfileServiceDep = Annotated[ProfileService, Depends(get_profile_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def current_user_id(
    auth: AuthServiceDep,
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token"
        )
    token = authorization[len("bearer ") :].strip()
    session = auth.resolve_session(token)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )
    return session.user_id


CurrentUserId = Annotated[str, Depends(current_user_id)]
