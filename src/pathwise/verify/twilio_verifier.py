from __future__ import annotations

import logging

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

logger = logging.getLogger(__name__)


class TwilioVerifier:
    """Production verifier. Delegates code generation, delivery, expiry,
    attempt counting, and A2P 10DLC compliance to Twilio's Verify API.

    Cost: ~$0.05 per successful verification. No phone number to rent or
    register separately; Verify uses Twilio's managed sender pool.
    """

    def __init__(self, account_sid: str, auth_token: str, service_sid: str) -> None:
        self._client = Client(account_sid, auth_token)
        self._service_sid = service_sid

    def start(self, phone_e164: str, *, now: float | None = None) -> None:
        # Local import for the same cycle-avoidance reason as ConsoleVerifier.
        from pathwise.core.auth import TooManyAttemptsError

        try:
            v = self._client.verify.v2.services(self._service_sid).verifications.create(
                to=phone_e164, channel="sms",
            )
        except TwilioRestException as exc:
            if exc.status == 429:
                raise TooManyAttemptsError(
                    "Too many verification requests. Try again later."
                ) from exc
            raise
        logger.info(
            "[TwilioVerifier] start sid=%s to=%s status=%s",
            v.sid, phone_e164, v.status,
        )

    def check(self, phone_e164: str, code: str, *, now: float | None = None) -> None:
        from pathwise.core.auth import (
            InvalidCodeError, TooManyAttemptsError,
        )

        try:
            check = (
                self._client.verify.v2.services(self._service_sid)
                .verification_checks.create(to=phone_e164, code=code)
            )
        except TwilioRestException as exc:
            if exc.status == 404:
                # No active verification for this number.
                raise InvalidCodeError("No code was sent for this number.") from exc
            if exc.status == 429:
                raise TooManyAttemptsError("Too many incorrect attempts.") from exc
            raise

        if check.status == "approved":
            return  # success

        # Twilio Verify doesn't distinguish wrong-code from expired-code in
        # the response — both come back as "pending" or "canceled". We
        # surface a generic message.
        raise InvalidCodeError("Incorrect or expired code.")
