from __future__ import annotations

import logging
import time
from pathlib import Path

from pathwise.core.ids import generate_otp_code, hash_token
from pathwise.core.store import FileStore

logger = logging.getLogger(__name__)


class ConsoleVerifier:
    """Dev-mode verifier. Generates a 6-digit code locally, prints it to the
    log, persists hash + expiry + attempts to flat files via the FileStore.

    The flat-file persistence is what lets the CLI (`pathwise auth send-code`
    in one process, `pathwise auth verify` in another) share OTP state.
    Single-use semantics: a successful check deletes the record.
    """

    def __init__(
        self,
        store: FileStore,
        otp_dir: Path,
        ttl_seconds: int = 600,
        max_attempts: int = 5,
    ) -> None:
        self.store = store
        self.otp_dir = otp_dir
        self.ttl_seconds = ttl_seconds
        self.max_attempts = max_attempts
        # In-memory log used by tests to discover the most recent code.
        self.sent: list[tuple[str, str]] = []

    def _path(self, phone_e164: str) -> Path:
        return self.otp_dir / f"{hash_token(phone_e164)}.json"

    def start(self, phone_e164: str, *, now: float | None = None) -> None:
        now = now if now is not None else time.time()
        code = generate_otp_code()
        self.store.write_json(
            self._path(phone_e164),
            {
                "phone_hash": hash_token(phone_e164),
                "code_hash": hash_token(code),
                "expires_at": now + self.ttl_seconds,
                "attempts": 0,
            },
        )
        self.sent.append((phone_e164, code))
        banner = "─" * 60
        logger.warning(
            "\n%s\n[ConsoleVerifier] dev OTP for %s: %s\n%s",
            banner, phone_e164, code, banner,
        )

    def check(self, phone_e164: str, code: str, *, now: float | None = None) -> None:
        # Local import to avoid a forward-reference cycle on
        # pathwise.core.auth's exception classes.
        from pathwise.core.auth import (
            CodeExpiredError, InvalidCodeError, TooManyAttemptsError,
        )

        now = now if now is not None else time.time()
        path = self._path(phone_e164)
        record = self.store.read_json(path)
        if not record:
            raise InvalidCodeError("No code was sent for this number.")

        if now > record["expires_at"]:
            raise CodeExpiredError("Code has expired. Request a new one.")

        attempts = int(record.get("attempts", 0))
        if attempts >= self.max_attempts:
            raise TooManyAttemptsError("Too many incorrect attempts.")

        if hash_token(code) != record["code_hash"]:
            record["attempts"] = attempts + 1
            self.store.write_json(path, record)
            raise InvalidCodeError("Incorrect code.")

        # Success — single-use consumption.
        path.unlink(missing_ok=True)
