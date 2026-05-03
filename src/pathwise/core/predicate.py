"""Tiny predicate evaluator for ``when`` clauses on steps and questions.

The schema language is JSON-only — no expressions, no functions.

Atoms map a data-model field name to either a primitive (equality), or an
operator object:

    {"has_car": true}
    {"home_emotional_cost": {"$in": ["tense", "hard"]}}
    {"current_savings": {"$gte": 1000}}

Combinators apply to whole sub-predicates:

    {"$all": [<pred>, <pred>, ...]}      # AND
    {"$any": [<pred>, <pred>, ...]}      # OR
    {"$not": <pred>}

Anything else raises ``PredicateError`` at validation/parse time so the
revision fails to load rather than blowing up at runtime.
"""

from __future__ import annotations

from typing import Any

COMPARISON_OPS = {"$eq", "$ne", "$gt", "$gte", "$lt", "$lte", "$in", "$nin"}
COMBINATORS = {"$all", "$any", "$not"}


class PredicateError(ValueError):
    pass


def validate(predicate: Any) -> None:
    """Raise PredicateError if the structure is malformed. Does not look at
    actual data — only at the predicate shape."""
    if predicate is None:
        return
    if not isinstance(predicate, dict):
        raise PredicateError(f"predicate must be an object, got {type(predicate).__name__}")
    if not predicate:
        return  # empty {} = always true

    for key, value in predicate.items():
        if key in COMBINATORS:
            _validate_combinator(key, value)
        elif key.startswith("$"):
            raise PredicateError(f"unknown combinator {key!r}")
        else:
            _validate_field_clause(key, value)


def _validate_combinator(op: str, value: Any) -> None:
    if op == "$not":
        validate(value)
        return
    if not isinstance(value, list):
        raise PredicateError(f"{op} expects a list of predicates")
    for sub in value:
        validate(sub)


def _validate_field_clause(field: str, value: Any) -> None:
    if isinstance(value, dict):
        if not value:
            raise PredicateError(f"empty operator object on field {field!r}")
        for op in value:
            if op not in COMPARISON_OPS:
                raise PredicateError(
                    f"unknown comparison operator {op!r} on field {field!r}"
                )
            if op in {"$in", "$nin"} and not isinstance(value[op], list):
                raise PredicateError(f"{op} expects a list on field {field!r}")


def evaluate(predicate: Any, answers: dict[str, Any]) -> bool:
    """Return whether the predicate matches the given answers.

    Caller must have validated the predicate first (or be willing to swallow
    ``PredicateError`` raised on malformed structure).
    """
    if predicate is None or predicate == {}:
        return True
    if not isinstance(predicate, dict):
        raise PredicateError(f"predicate must be an object, got {type(predicate).__name__}")

    # An object is an implicit AND across its keys.
    for key, value in predicate.items():
        if key == "$all":
            if not all(evaluate(sub, answers) for sub in value):
                return False
        elif key == "$any":
            if not any(evaluate(sub, answers) for sub in value):
                return False
        elif key == "$not":
            if evaluate(value, answers):
                return False
        else:
            if not _eval_field(key, value, answers):
                return False
    return True


def _eval_field(field: str, clause: Any, answers: dict[str, Any]) -> bool:
    actual = answers.get(field)
    if isinstance(clause, dict):
        for op, expected in clause.items():
            if not _eval_op(op, actual, expected):
                return False
        return True
    return actual == clause


def _eval_op(op: str, actual: Any, expected: Any) -> bool:
    if op == "$eq":
        return actual == expected
    if op == "$ne":
        return actual != expected
    if op == "$in":
        return actual in expected
    if op == "$nin":
        return actual not in expected
    # Numeric comparisons against missing/None evaluate to False.
    if actual is None or expected is None:
        return False
    if op == "$gt":
        return actual > expected
    if op == "$gte":
        return actual >= expected
    if op == "$lt":
        return actual < expected
    if op == "$lte":
        return actual <= expected
    raise PredicateError(f"unknown comparison operator {op!r}")
