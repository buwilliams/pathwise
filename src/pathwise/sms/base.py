from __future__ import annotations

from typing import Protocol


class SmsSender(Protocol):
    def send(self, to_phone_e164: str, body: str) -> None: ...
