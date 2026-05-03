from __future__ import annotations

import pytest

from pathwise.core.questionnaire import (
    AnswerValidationError,
    QuestionnaireService,
    coerce_answer,
)
from pathwise.core.season import get_pack
from pathwise.core.store import FileStore

UID = "abcdef0123456789abcdef0123456789"
PACK = get_pack("build-independence")


class TestCoerce:
    def test_money(self) -> None:
        q = PACK.question("current_savings")
        assert coerce_answer(q, "1500") == 1500
        assert coerce_answer(q, 1500.5) == 1500.5

    def test_money_negative_rejected(self) -> None:
        q = PACK.question("current_savings")
        with pytest.raises(AnswerValidationError):
            coerce_answer(q, -10)

    def test_yes_no(self) -> None:
        q = PACK.question("lives_with_parents")
        assert coerce_answer(q, "yes") is True
        assert coerce_answer(q, "no") is False
        assert coerce_answer(q, True) is True

    def test_single_choice(self) -> None:
        q = PACK.question("hours_preference")
        assert coerce_answer(q, "more") == "more"
        with pytest.raises(AnswerValidationError):
            coerce_answer(q, "elsewhere")

    def test_multi_choice(self) -> None:
        q = PACK.question("car_purpose")
        assert coerce_answer(q, ["work", "school"]) == ["work", "school"]
        assert coerce_answer(q, "work") == ["work"]
        with pytest.raises(AnswerValidationError):
            coerce_answer(q, ["bogus"])

    def test_scale_bounds(self) -> None:
        q = PACK.question("move_out_urgency")
        assert coerce_answer(q, 3) == 3
        with pytest.raises(AnswerValidationError):
            coerce_answer(q, 0)
        with pytest.raises(AnswerValidationError):
            coerce_answer(q, 6)

    def test_required_blank_rejected(self) -> None:
        q = PACK.question("current_savings")
        with pytest.raises(AnswerValidationError):
            coerce_answer(q, "")

    def test_optional_blank_returns_none(self) -> None:
        q = PACK.question("car_purpose")
        assert coerce_answer(q, "") is None

    def test_home_emotional_cost_choices(self) -> None:
        q = PACK.question("home_emotional_cost")
        for choice in ("peaceful", "fine", "tense", "hard"):
            assert coerce_answer(q, choice) == choice
        with pytest.raises(AnswerValidationError):
            coerce_answer(q, "miserable")


class TestService:
    def test_set_then_get(self, store: FileStore) -> None:
        qs = QuestionnaireService(store)
        qs.set_answer(UID, PACK, "current_savings", "10000")
        qs.set_answer(UID, PACK, "lives_with_parents", "yes")
        assert qs.get_answers(UID, PACK.id) == {
            "current_savings": 10000,
            "lives_with_parents": True,
        }

    def test_set_answers_atomic_validation(self, store: FileStore) -> None:
        qs = QuestionnaireService(store)
        with pytest.raises(AnswerValidationError):
            qs.set_answers(
                UID,
                PACK,
                {"current_savings": "1000", "hours_preference": "bogus"},
            )
        # nothing should have been written
        assert qs.get_answers(UID, PACK.id) == {}

    def test_history_appended(self, store: FileStore) -> None:
        qs = QuestionnaireService(store)
        qs.set_answer(UID, PACK, "current_savings", "1000")
        qs.set_answer(UID, PACK, "current_savings", "1500")
        history = store.read_jsonl(store.answers_history_path(UID, PACK.id))
        assert [h["value"] for h in history] == [1000, 1500]

    def test_completion_tracking(self, store: FileStore) -> None:
        qs = QuestionnaireService(store)
        status = qs.completion(UID, PACK)
        assert status.percent == 0
        assert not status.is_complete

        # Set just one required
        qs.set_answer(UID, PACK, "current_savings", "1000")
        status = qs.completion(UID, PACK)
        assert "current_savings" not in status.missing_required
        assert status.percent > 0
