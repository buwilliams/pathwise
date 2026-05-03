from __future__ import annotations

import logging

from pathwise.config import Settings
from pathwise.core.store import FileStore
from pathwise.verify.base import Verifier
from pathwise.verify.console_verifier import ConsoleVerifier

logger = logging.getLogger(__name__)


def build_verifier(settings: Settings, store: FileStore) -> Verifier:
    """Pick the right Verifier given current settings.

    Returns ``TwilioVerifier`` if Verify-API credentials are configured,
    else ``ConsoleVerifier`` (which prints codes to the log and persists
    them locally for dev workflows).
    """
    if settings.twilio_verify_enabled:
        # Local import so we only pull in the Twilio SDK when actually used.
        from pathwise.verify.twilio_verifier import TwilioVerifier

        logger.info("[verify] using TwilioVerifier (service=%s)", settings.twilio_verify_service_sid)
        return TwilioVerifier(
            account_sid=settings.twilio_account_sid,
            auth_token=settings.twilio_auth_token,
            service_sid=settings.twilio_verify_service_sid,
        )
    logger.warning("[verify] using ConsoleVerifier (dev mode — codes go to the log)")
    return ConsoleVerifier(
        store=store,
        otp_dir=settings.otp_dir,
        ttl_seconds=settings.pathwise_otp_ttl_seconds,
        max_attempts=settings.pathwise_otp_max_verify_attempts,
    )
