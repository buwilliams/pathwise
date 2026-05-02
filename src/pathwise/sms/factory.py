from __future__ import annotations

from pathwise.config import Settings
from pathwise.sms.base import SmsSender
from pathwise.sms.console_sender import ConsoleSmsSender
from pathwise.sms.twilio_sender import TwilioSmsSender


def build_sms_sender(settings: Settings) -> SmsSender:
    if settings.twilio_enabled:
        return TwilioSmsSender(
            account_sid=settings.twilio_account_sid,
            auth_token=settings.twilio_auth_token,
            from_number=settings.twilio_from_number,
        )
    return ConsoleSmsSender()
