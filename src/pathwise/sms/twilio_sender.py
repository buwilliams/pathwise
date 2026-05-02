from __future__ import annotations

import logging

from twilio.rest import Client

logger = logging.getLogger(__name__)


class TwilioSmsSender:
    def __init__(self, account_sid: str, auth_token: str, from_number: str) -> None:
        self._client = Client(account_sid, auth_token)
        self._from = from_number

    def send(self, to_phone_e164: str, body: str) -> None:
        msg = self._client.messages.create(
            to=to_phone_e164, from_=self._from, body=body
        )
        logger.info(
            "[TwilioSmsSender] sent sid=%s to=%s status=%s",
            msg.sid,
            to_phone_e164,
            msg.status,
        )
