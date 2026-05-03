"""Phone-number verification surface.

Two implementations:

* ``ConsoleVerifier`` — dev mode. Generates a 6-digit code locally,
  prints it to the server log, persists hash + expiry + attempts to
  flat files. No external service.
* ``TwilioVerifier`` — production. Delegates to Twilio's Verify API.
  Twilio owns the code, expiry, attempt counting, and A2P 10DLC
  compliance. Costs ~$0.05 per verification.

The ``AuthService`` wraps a verifier with rate-limit-by-phone (cheaper
than paying Twilio for spam) and session creation. Verifier
implementations raise the same ``AuthError`` subclasses regardless of
which backend you're on, so the API/CLI layer doesn't have to know.
"""

from __future__ import annotations

from typing import Protocol


class Verifier(Protocol):
    def start(self, phone_e164: str, *, now: float | None = None) -> None:
        """Send a verification code to the given phone. Raises on transport
        failure or when the verifier itself is rate-limited."""

    def check(self, phone_e164: str, code: str, *, now: float | None = None) -> None:
        """Verify the code. Returns None on success. Raises one of
        ``InvalidCodeError`` / ``CodeExpiredError`` / ``TooManyAttemptsError``
        on failure."""
