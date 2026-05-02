from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from pathwise.config import Settings
from pathwise.core.ids import (
    generate_otp_code,
    generate_session_token,
    hash_token,
    user_id_for_phone,
)
from pathwise.core.store import FileStore
from pathwise.sms.base import SmsSender


class AuthError(Exception):
    pass


class RateLimitedError(AuthError):
    pass


class InvalidCodeError(AuthError):
    pass


class CodeExpiredError(AuthError):
    pass


class TooManyAttemptsError(AuthError):
    pass


@dataclass
class StartCodeResult:
    sent: bool
    next_allowed_at: float | None = None


@dataclass
class VerifyResult:
    session_token: str
    user_id: str
    needs_onboarding: bool


@dataclass
class Session:
    token_hash: str
    user_id: str
    created_at: float
    expires_at: float


class AuthService:
    """OTP send + verify, session create + lookup. All flat-file."""

    def __init__(
        self,
        store: FileStore,
        settings: Settings,
        sms: SmsSender,
        sms_template: str = (
            "Your Pathwise code is {code}. It expires in 10 minutes."
        ),
    ) -> None:
        self.store = store
        self.settings = settings
        self.sms = sms
        self.sms_template = sms_template

    # ------------------------------------------------------------------
    # OTP
    # ------------------------------------------------------------------

    def _otp_path(self, phone_e164: str) -> Any:
        return self.settings.otp_dir / f"{hash_token(phone_e164)}.json"

    def start(self, phone_e164: str, *, now: float | None = None) -> StartCodeResult:
        now = now if now is not None else time.time()
        path = self._otp_path(phone_e164)
        record = self.store.read_json(path)

        # Rate limit: max N codes per rolling hour.
        sent_at: list[float] = list(record.get("sent_at", []))
        sent_at = [t for t in sent_at if now - t < 3600]
        if len(sent_at) >= self.settings.pathwise_otp_max_per_hour:
            next_allowed = sent_at[0] + 3600
            raise RateLimitedError(
                f"Too many codes requested. Try again at {next_allowed}"
            )

        code = generate_otp_code()
        sent_at.append(now)
        new_record = {
            "phone_hash": hash_token(phone_e164),
            "code_hash": hash_token(code),
            "expires_at": now + self.settings.pathwise_otp_ttl_seconds,
            "attempts": 0,
            "sent_at": sent_at,
        }
        self.store.write_json(path, new_record)
        self.sms.send(phone_e164, self.sms_template.format(code=code))
        return StartCodeResult(sent=True)

    def verify(
        self, phone_e164: str, code: str, *, now: float | None = None
    ) -> VerifyResult:
        now = now if now is not None else time.time()
        path = self._otp_path(phone_e164)
        record = self.store.read_json(path)
        if not record:
            raise InvalidCodeError("No code was sent for this number.")

        if now > record["expires_at"]:
            raise CodeExpiredError("Code has expired. Request a new one.")

        attempts = int(record.get("attempts", 0))
        if attempts >= self.settings.pathwise_otp_max_verify_attempts:
            raise TooManyAttemptsError("Too many incorrect attempts.")

        if hash_token(code) != record["code_hash"]:
            record["attempts"] = attempts + 1
            self.store.write_json(path, record)
            raise InvalidCodeError("Incorrect code.")

        # Success — invalidate the OTP and create a session.
        path.unlink(missing_ok=True)
        user_id = user_id_for_phone(phone_e164)
        token = self._create_session(user_id, now=now)
        return VerifyResult(
            session_token=token,
            user_id=user_id,
            needs_onboarding=not self.store.user_exists(user_id),
        )

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def _session_path(self, token: str) -> Any:
        return self.settings.sessions_dir / f"{hash_token(token)}.json"

    def _create_session(self, user_id: str, *, now: float) -> str:
        token = generate_session_token()
        path = self._session_path(token)
        self.store.write_json(
            path,
            {
                "user_id": user_id,
                "created_at": now,
                "expires_at": now + self.settings.pathwise_session_ttl_seconds,
            },
        )
        return token

    def resolve_session(self, token: str, *, now: float | None = None) -> Session | None:
        now = now if now is not None else time.time()
        path = self._session_path(token)
        record = self.store.read_json(path)
        if not record:
            return None
        if now > record["expires_at"]:
            path.unlink(missing_ok=True)
            return None
        return Session(
            token_hash=hash_token(token),
            user_id=record["user_id"],
            created_at=record["created_at"],
            expires_at=record["expires_at"],
        )

    def revoke_session(self, token: str) -> None:
        self._session_path(token).unlink(missing_ok=True)
