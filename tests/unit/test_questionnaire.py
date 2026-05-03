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
QN = PACK.questionnaire


def _coerce(key: str, raw):
    return coerce_answer(key, QN.data_model[key], QN.questions[key], raw)


class TestCoerce:
    def test_money(self) -> None:
        assert _coerce("current_savings", "1500") == 1500
        assert _coerce("current_savings", 1500.5) == 1500.5

    def test_money_negative_rejected(self) -> None:
        with pytest.raises(AnswerValidationError):
            _coerce("current_savings", -10)

    def test_yes_no(self) -> None:
        assert _coerce("lives_with_parents", "yes") is True
        assert _coerce("lives_with_parents", "no") is False
        assert _coerce("lives_with_parents", True) is True

    def test_single_choice(self) -> None:
        assert _coerce("hours_preference", "more") == "more"
        with pytest.raises(AnswerValidationError):
            _coerce("hours_preference", "elsewhere")

    def test_multi_choice(self) -> None:
        assert _coerce("car_purpose", ["work", "school"]) == ["work", "school"]
        assert _coerce("car_purpose", "work") == ["work"]
        with pytest.raises(AnswerValidationError):
            _coerce("car_purpose", ["bogus"])

    def test_scale_bounds(self) -> None:
        assert _coerce("move_out_urgency", 3) == 3
        with pytest.raises(AnswerValidationError):
            _coerce("move_out_urgency", 0)
        with pytest.raises(AnswerValidationError):
            _coerce("move_out_urgency", 6)

    def test_required_blank_rejected(self) -> None:
        with pytest.raises(AnswerValidationError):
            _coerce("current_savings", "")

    def test_optional_blank_returns_none(self) -> None:
        assert _coerce("car_purpose", "") is None

    def test_home_emotional_cost_choices(self) -> None:
        for choice in ("peaceful", "fine", "tense", "hard"):
            assert _coerce("home_emotional_cost", choice) == choice
        with pytest.raises(AnswerValidationError):
            _coerce("home_emotional_cost", "miserable")


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
                UID, PACK,
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
        assert all(h["pack_version"] == PACK.version for h in history)

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

    def test_completion_respects_when(self, store: FileStore) -> None:
        """move_out_urgency is gated on lives_with_parents=true. It must be
        hidden (and so absent from missing_required) until the user answers
        lives_with_parents=true."""
        qs = QuestionnaireService(store)

        # Empty answers: lives_with_parents is unset, so move_out_urgency is hidden.
        baseline = qs.completion(UID, PACK)
        assert "move_out_urgency" not in baseline.missing_required

        qs.set_answer(UID, PACK, "lives_with_parents", "no")
        after_no = qs.completion(UID, PACK)
        assert "move_out_urgency" not in after_no.missing_required

        qs.set_answer(UID, PACK, "lives_with_parents", "yes")
        after_yes = qs.completion(UID, PACK)
        assert "move_out_urgency" in after_yes.missing_required

    def test_unknown_key_rejected(self, store: FileStore) -> None:
        qs = QuestionnaireService(store)
        with pytest.raises(AnswerValidationError):
            qs.set_answer(UID, PACK, "no_such_field", "1000")
