from __future__ import annotations

import pytest

from pathwise.core.predicate import PredicateError, evaluate, validate


# ─────────────── Validate ───────────────


class TestValidate:
    def test_none_and_empty_ok(self) -> None:
        validate(None)
        validate({})

    def test_must_be_object(self) -> None:
        with pytest.raises(PredicateError):
            validate([])
        with pytest.raises(PredicateError):
            validate("foo")

    def test_unknown_combinator(self) -> None:
        with pytest.raises(PredicateError):
            validate({"$xor": [{"a": 1}]})

    def test_unknown_op(self) -> None:
        with pytest.raises(PredicateError):
            validate({"a": {"$matches": "x"}})

    def test_in_must_be_list(self) -> None:
        with pytest.raises(PredicateError):
            validate({"a": {"$in": "x"}})

    def test_all_must_be_list(self) -> None:
        with pytest.raises(PredicateError):
            validate({"$all": {"a": 1}})

    def test_nested_combinators_ok(self) -> None:
        validate(
            {
                "$any": [
                    {"a": 1},
                    {"$all": [{"b": {"$gt": 5}}, {"$not": {"c": 0}}]},
                ]
            }
        )


# ─────────────── Evaluate ───────────────


class TestEvaluate:
    def test_empty_always_true(self) -> None:
        assert evaluate(None, {}) is True
        assert evaluate({}, {"a": 1}) is True

    def test_equality_primitive(self) -> None:
        assert evaluate({"has_car": True}, {"has_car": True}) is True
        assert evaluate({"has_car": True}, {"has_car": False}) is False
        assert evaluate({"has_car": True}, {}) is False  # missing

    def test_eq_op(self) -> None:
        assert evaluate({"x": {"$eq": 5}}, {"x": 5}) is True
        assert evaluate({"x": {"$eq": 5}}, {"x": 6}) is False

    def test_ne_op(self) -> None:
        assert evaluate({"x": {"$ne": 5}}, {"x": 6}) is True
        assert evaluate({"x": {"$ne": 5}}, {"x": 5}) is False

    def test_in_nin(self) -> None:
        assert evaluate({"x": {"$in": [1, 2, 3]}}, {"x": 2}) is True
        assert evaluate({"x": {"$in": [1, 2, 3]}}, {"x": 9}) is False
        assert evaluate({"x": {"$nin": [1, 2, 3]}}, {"x": 9}) is True
        assert evaluate({"x": {"$nin": [1, 2, 3]}}, {"x": 2}) is False

    def test_numeric_ops(self) -> None:
        assert evaluate({"x": {"$gt": 5}}, {"x": 6}) is True
        assert evaluate({"x": {"$gt": 5}}, {"x": 5}) is False
        assert evaluate({"x": {"$gte": 5}}, {"x": 5}) is True
        assert evaluate({"x": {"$lt": 5}}, {"x": 4}) is True
        assert evaluate({"x": {"$lte": 5}}, {"x": 5}) is True

    def test_numeric_ops_against_missing_are_false(self) -> None:
        # Missing actuals never satisfy ordering ops.
        assert evaluate({"x": {"$gt": 5}}, {}) is False
        assert evaluate({"x": {"$lt": 5}}, {}) is False

    def test_implicit_and_across_keys(self) -> None:
        pred = {"a": 1, "b": {"$gt": 5}}
        assert evaluate(pred, {"a": 1, "b": 6}) is True
        assert evaluate(pred, {"a": 1, "b": 4}) is False
        assert evaluate(pred, {"a": 2, "b": 6}) is False

    def test_all(self) -> None:
        pred = {"$all": [{"a": 1}, {"b": 2}]}
        assert evaluate(pred, {"a": 1, "b": 2}) is True
        assert evaluate(pred, {"a": 1, "b": 3}) is False

    def test_any(self) -> None:
        pred = {"$any": [{"a": 1}, {"b": 2}]}
        assert evaluate(pred, {"a": 0, "b": 2}) is True
        assert evaluate(pred, {"a": 0, "b": 0}) is False

    def test_not(self) -> None:
        assert evaluate({"$not": {"a": 1}}, {"a": 2}) is True
        assert evaluate({"$not": {"a": 1}}, {"a": 1}) is False

    def test_combinator_nesting(self) -> None:
        pred = {
            "$any": [
                {"role": "admin"},
                {"$all": [{"role": "user"}, {"verified": True}]},
            ]
        }
        assert evaluate(pred, {"role": "admin"}) is True
        assert evaluate(pred, {"role": "user", "verified": True}) is True
        assert evaluate(pred, {"role": "user", "verified": False}) is False
        assert evaluate(pred, {"role": "guest"}) is False
