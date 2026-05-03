from __future__ import annotations

import pytest

from pathwise.core.questionnaire_schema import Questionnaire


def _base() -> dict:
    """Minimal valid questionnaire — single step, single question."""
    return {
        "schema_version": 1,
        "data_model": {
            "savings": {"type": "money", "min": 0},
        },
        "questions": {
            "savings": {
                "prompt": "How much?",
                "input": {"kind": "money", "min": 0},
            },
        },
        "steps": [
            {"id": "s1", "title": "S1", "questions": ["savings"]},
        ],
    }


class TestHappyPath:
    def test_loads(self) -> None:
        q = Questionnaire.model_validate(_base())
        assert list(q.questions) == ["savings"]
        assert q.required_keys() == {"savings"}

    def test_required_filtered_by_step_when(self) -> None:
        raw = _base()
        raw["data_model"]["has_car"] = {"type": "yes_no"}
        raw["questions"]["has_car"] = {
            "prompt": "Car?",
            "input": {"kind": "yes_no"},
        }
        raw["steps"][0]["questions"].append("has_car")
        raw["steps"].append(
            {
                "id": "s2", "title": "S2", "questions": [],
                "when": {"has_car": True},
            }
        )
        # Add a question whose data_model is satisfied
        raw["data_model"]["car_ok"] = {"type": "yes_no"}
        raw["questions"]["car_ok"] = {
            "prompt": "Ok?", "input": {"kind": "yes_no"},
        }
        raw["steps"][1]["questions"].append("car_ok")
        q = Questionnaire.model_validate(raw)

        # When has_car is unset, step s2 is hidden — car_ok is NOT required.
        assert q.required_keys({}) == {"savings", "has_car"}
        # When has_car is true, step s2 is visible — car_ok joins required.
        assert q.required_keys({"has_car": True}) == {"savings", "has_car", "car_ok"}

    def test_required_filtered_by_question_when(self) -> None:
        raw = _base()
        raw["data_model"]["max_months"] = {"type": "number", "min": 0, "max": 60}
        raw["questions"]["max_months"] = {
            "prompt": "Months?",
            "input": {"kind": "number", "min": 0, "max": 60},
            "when": {"savings": {"$gte": 1000}},
        }
        raw["steps"][0]["questions"].append("max_months")
        q = Questionnaire.model_validate(raw)

        assert q.required_keys({"savings": 500}) == {"savings"}
        assert q.required_keys({"savings": 1500}) == {"savings", "max_months"}


class TestFailures:
    def test_question_without_data_model(self) -> None:
        raw = _base()
        raw["questions"]["unknown"] = {
            "prompt": "?", "input": {"kind": "text"},
        }
        raw["steps"][0]["questions"].append("unknown")
        with pytest.raises(ValueError, match="no matching data_model"):
            Questionnaire.model_validate(raw)

    def test_step_references_unknown_question(self) -> None:
        raw = _base()
        raw["steps"][0]["questions"].append("ghost")
        with pytest.raises(ValueError, match="unknown question"):
            Questionnaire.model_validate(raw)

    def test_question_in_two_steps(self) -> None:
        raw = _base()
        raw["steps"].append({"id": "s2", "title": "S2", "questions": ["savings"]})
        with pytest.raises(ValueError, match="multiple steps"):
            Questionnaire.model_validate(raw)

    def test_question_not_in_any_step(self) -> None:
        raw = _base()
        raw["data_model"]["orphan"] = {"type": "yes_no"}
        raw["questions"]["orphan"] = {
            "prompt": "?", "input": {"kind": "yes_no"},
        }
        with pytest.raises(ValueError, match="not assigned to any step"):
            Questionnaire.model_validate(raw)

    def test_input_kind_incompatible_with_type(self) -> None:
        raw = _base()
        raw["questions"]["savings"]["input"] = {"kind": "yes_no"}
        with pytest.raises(ValueError, match="incompatible"):
            Questionnaire.model_validate(raw)

    def test_choice_input_requires_options(self) -> None:
        raw = _base()
        raw["data_model"]["mood"] = {
            "type": "string",
            "values": ["happy", "sad"],
        }
        raw["questions"]["mood"] = {
            "prompt": "?", "input": {"kind": "single_choice"},
        }
        raw["steps"][0]["questions"].append("mood")
        with pytest.raises(ValueError, match="requires options"):
            Questionnaire.model_validate(raw)

    def test_options_must_match_data_model_values(self) -> None:
        raw = _base()
        raw["data_model"]["mood"] = {"type": "string", "values": ["happy"]}
        raw["questions"]["mood"] = {
            "prompt": "?",
            "input": {
                "kind": "single_choice",
                "options": [{"value": "extreme", "label": "Extreme"}],
            },
        }
        raw["steps"][0]["questions"].append("mood")
        with pytest.raises(ValueError, match="not in data_model values"):
            Questionnaire.model_validate(raw)

    def test_malformed_when(self) -> None:
        raw = _base()
        raw["questions"]["savings"]["when"] = {"$xor": []}
        with pytest.raises(ValueError):
            Questionnaire.model_validate(raw)
