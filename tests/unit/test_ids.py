from __future__ import annotations

import pytest

from pathwise.core.ids import (
    generate_otp_code,
    generate_session_token,
    hash_token,
    normalize_phone,
    user_id_for_phone,
)


class TestNormalizePhone:
    def test_us_number_with_country_code(self) -> None:
        assert normalize_phone("+1 202 555 0100") == "+12025550100"

    def test_us_number_without_country_code(self) -> None:
        assert normalize_phone("202-555-0100") == "+12025550100"

    def test_idempotent(self) -> None:
        once = normalize_phone("(202) 555-0100")
        twice = normalize_phone(once)
        assert once == twice == "+12025550100"

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            normalize_phone("not-a-number")

    def test_unallocated_area_code_rejected(self) -> None:
        with pytest.raises(ValueError):
            normalize_phone("+15555550100")


class TestUserId:
    def test_deterministic(self) -> None:
        a = user_id_for_phone("+12025550100")
        b = user_id_for_phone("+12025550100")
        assert a == b

    def test_different_phones_differ(self) -> None:
        a = user_id_for_phone("+12025550100")
        b = user_id_for_phone("+12025550101")
        assert a != b

    def test_length_32_hex(self) -> None:
        uid = user_id_for_phone("+12025550100")
        assert len(uid) == 32
        int(uid, 16)


class TestTokens:
    def test_session_token_unique(self) -> None:
        tokens = {generate_session_token() for _ in range(100)}
        assert len(tokens) == 100

    def test_otp_six_digits(self) -> None:
        for _ in range(50):
            code = generate_otp_code()
            assert len(code) == 6
            assert code.isdigit()

    def test_hash_token_deterministic(self) -> None:
        assert hash_token("hello") == hash_token("hello")
        assert hash_token("hello") != hash_token("world")
        assert len(hash_token("x")) == 64
