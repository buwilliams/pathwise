from __future__ import annotations

from pathlib import Path

import pytest

from pathwise.config import Settings
from pathwise.core.auth import (
    AuthService,
    CodeExpiredError,
    InvalidCodeError,
    RateLimitedError,
    TooManyAttemptsError,
)
from pathwise.core.store import FileStore
from pathwise.verify.console_verifier import ConsoleVerifier


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        pathwise_data_dir=tmp_path,
        pathwise_otp_ttl_seconds=600,
        pathwise_otp_max_per_hour=3,
        pathwise_otp_max_verify_attempts=5,
        pathwise_session_ttl_seconds=3600,
    )


@pytest.fixture
def auth(settings: Settings) -> AuthService:
    settings.users_dir.mkdir(parents=True, exist_ok=True)
    settings.otp_dir.mkdir(parents=True, exist_ok=True)
    settings.sessions_dir.mkdir(parents=True, exist_ok=True)
    store = FileStore(settings.users_dir)
    verifier = ConsoleVerifier(
        store=store,
        otp_dir=settings.otp_dir,
        ttl_seconds=settings.pathwise_otp_ttl_seconds,
        max_attempts=settings.pathwise_otp_max_verify_attempts,
    )
    return AuthService(store, settings, verifier)


PHONE = "+12025550100"


def _last_code_sent(auth: AuthService) -> str:
    verifier: ConsoleVerifier = auth.verifier  # type: ignore[assignment]
    return verifier.sent[-1][1]


class TestStartCode:
    def test_sends_a_code(self, auth: AuthService) -> None:
        auth.start(PHONE)
        verifier: ConsoleVerifier = auth.verifier  # type: ignore[assignment]
        assert len(verifier.sent) == 1
        assert verifier.sent[0][0] == PHONE

    def test_rate_limit_after_max_per_hour(self, auth: AuthService) -> None:
        for _ in range(3):
            auth.start(PHONE, now=1000.0)
        with pytest.raises(RateLimitedError):
            auth.start(PHONE, now=1001.0)

    def test_rate_limit_window_resets(self, auth: AuthService) -> None:
        for _ in range(3):
            auth.start(PHONE, now=1000.0)
        # > 3600s later, should be allowed again
        auth.start(PHONE, now=1000.0 + 3601)


class TestVerify:
    def test_happy_path_returns_session(self, auth: AuthService) -> None:
        auth.start(PHONE, now=1000.0)
        code = _last_code_sent(auth)
        result = auth.verify(PHONE, code, now=1010.0)
        assert result.session_token
        assert result.user_id
        assert result.needs_onboarding is True  # no profile yet

    def test_session_resolves(self, auth: AuthService) -> None:
        auth.start(PHONE, now=1000.0)
        code = _last_code_sent(auth)
        result = auth.verify(PHONE, code, now=1010.0)
        session = auth.resolve_session(result.session_token, now=1020.0)
        assert session is not None
        assert session.user_id == result.user_id

    def test_expired_session_returns_none(self, auth: AuthService) -> None:
        auth.start(PHONE, now=1000.0)
        code = _last_code_sent(auth)
        result = auth.verify(PHONE, code, now=1010.0)
        # session ttl is 3600s in fixture
        assert auth.resolve_session(result.session_token, now=1010.0 + 3601) is None

    def test_unknown_token_returns_none(self, auth: AuthService) -> None:
        assert auth.resolve_session("bogus") is None

    def test_no_code_sent_raises(self, auth: AuthService) -> None:
        with pytest.raises(InvalidCodeError):
            auth.verify(PHONE, "123456")

    def test_wrong_code_raises_and_increments(self, auth: AuthService) -> None:
        auth.start(PHONE, now=1000.0)
        with pytest.raises(InvalidCodeError):
            auth.verify(PHONE, "000000", now=1001.0)
        with pytest.raises(InvalidCodeError):
            auth.verify(PHONE, "000001", now=1002.0)

    def test_too_many_attempts(self, auth: AuthService) -> None:
        auth.start(PHONE, now=1000.0)
        for i in range(5):
            with pytest.raises(InvalidCodeError):
                auth.verify(PHONE, f"00000{i}", now=1000.0 + i)
        with pytest.raises(TooManyAttemptsError):
            auth.verify(PHONE, "999999", now=1010.0)

    def test_expired_code(self, auth: AuthService) -> None:
        auth.start(PHONE, now=1000.0)
        code = _last_code_sent(auth)
        with pytest.raises(CodeExpiredError):
            auth.verify(PHONE, code, now=1000.0 + 700)  # ttl is 600

    def test_otp_consumed_on_success(self, auth: AuthService) -> None:
        auth.start(PHONE, now=1000.0)
        code = _last_code_sent(auth)
        auth.verify(PHONE, code, now=1010.0)
        # second verify with same code should fail
        with pytest.raises(InvalidCodeError):
            auth.verify(PHONE, code, now=1020.0)


class TestRevoke:
    def test_revoke_invalidates_session(self, auth: AuthService) -> None:
        auth.start(PHONE, now=1000.0)
        code = _last_code_sent(auth)
        result = auth.verify(PHONE, code, now=1010.0)
        auth.revoke_session(result.session_token)
        assert auth.resolve_session(result.session_token) is None
