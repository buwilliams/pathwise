from __future__ import annotations

import hashlib
import secrets

import phonenumbers


def normalize_phone(phone: str, default_region: str = "US") -> str:
    """Parse and normalize a phone number to E.164 form (e.g. +15551234567).

    Raises ValueError if the input cannot be parsed as a valid number.
    """
    try:
        parsed = phonenumbers.parse(phone, default_region)
    except phonenumbers.NumberParseException as exc:
        raise ValueError(f"Invalid phone number: {phone!r}") from exc
    if not phonenumbers.is_valid_number(parsed):
        raise ValueError(f"Invalid phone number: {phone!r}")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def user_id_for_phone(phone_e164: str) -> str:
    """Derive a stable 32-char hex user_id from an E.164 phone number.

    Same input → same id, no DB lookup needed for partitioning.
    """
    digest = hashlib.sha256(phone_e164.encode("utf-8")).hexdigest()
    return digest[:32]


def hash_token(token: str) -> str:
    """Hash a session/OTP token for at-rest storage. Full sha256 hex."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_session_token() -> str:
    """Cryptographically random opaque session token (URL-safe, ~43 chars)."""
    return secrets.token_urlsafe(32)


def generate_otp_code() -> str:
    """6-digit numeric OTP, zero-padded."""
    return f"{secrets.randbelow(1_000_000):06d}"
