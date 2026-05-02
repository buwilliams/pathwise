from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class ConsoleSmsSender:
    """Dev-mode SMS sender that prints messages to the server log instead of sending.

    Used automatically when no Twilio credentials are configured.
    """

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send(self, to_phone_e164: str, body: str) -> None:
        self.sent.append((to_phone_e164, body))
        banner = "─" * 60
        logger.warning(
            "\n%s\n[ConsoleSmsSender] would SMS %s:\n  %s\n%s",
            banner,
            to_phone_e164,
            body,
            banner,
        )
