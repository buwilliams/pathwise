"""Pydantic models for the per-revision ``questionnaire.json`` schema.

Three concerns are kept separate by design:

* ``data_model`` — the durable contract between the questionnaire and the
  deterministic core. Adding or removing a key here means a new revision.
* ``questions`` — UI presentation per data-model field (prompt, help,
  required, input widget). Free to vary across revisions without changing
  the data shape.
* ``steps`` — ordered groups that drive the wizard UI.

Cross-validation runs at load time: every ``questions`` key must have a
matching ``data_model`` entry, every step must reference real questions,
every ``input.kind`` must be compatible with the data field's ``type``,
and every ``when`` predicate must be structurally valid.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pathwise.core.predicate import validate as validate_predicate

DataType = Literal[
    "money", "number", "hours", "scale", "yes_no", "string", "string_set"
]
InputKind = Literal[
    "money", "number", "hours", "scale", "yes_no", "text",
    "single_choice", "multi_choice",
]

# Which UI widgets are valid for each data-model type. Restricting this at
# load time prevents revisions from declaring (e.g.) a money field rendered
# as a multi_choice picker, which would silently accept the wrong shape.
_COMPATIBLE_INPUTS: dict[str, set[str]] = {
    "money": {"money"},
    "number": {"number"},
    "hours": {"hours"},
    "scale": {"scale"},
    "yes_no": {"yes_no"},
    "string": {"text", "single_choice"},
    "string_set": {"multi_choice"},
}


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DataField(_Strict):
    type: DataType
    min: float | None = None
    max: float | None = None
    # For string / string_set: the allowed values (None = any string).
    values: list[str] | None = None
    unit: str | None = None


class Option(_Strict):
    value: str
    label: str


class Input(_Strict):
    kind: InputKind
    placeholder: str | None = None
    options: list[Option] | None = None
    # Numeric inputs may override the data-model min/max for UI bounds; if
    # absent, the data-model bounds apply.
    min: float | None = None
    max: float | None = None
    unit: str | None = None


When = Annotated[dict[str, Any] | None, Field(default=None)]


class Question(_Strict):
    prompt: str
    help: str | None = None
    required: bool = True
    input: Input
    when: When = None

    @model_validator(mode="after")
    def _check_when(self) -> "Question":
        validate_predicate(self.when)
        return self


class Step(_Strict):
    id: str
    title: str
    blurb: str | None = None
    questions: list[str]
    when: When = None

    @model_validator(mode="after")
    def _check_when(self) -> "Step":
        validate_predicate(self.when)
        return self


class Questionnaire(_Strict):
    schema_version: int
    data_model: dict[str, DataField]
    questions: dict[str, Question]
    steps: list[Step]

    @model_validator(mode="after")
    def _cross_validate(self) -> "Questionnaire":
        # Every question must have a matching data-model field.
        for qkey in self.questions:
            if qkey not in self.data_model:
                raise ValueError(
                    f"question {qkey!r} has no matching data_model entry"
                )

        # Each input.kind must be compatible with its data field's type.
        for qkey, q in self.questions.items():
            field_type = self.data_model[qkey].type
            allowed = _COMPATIBLE_INPUTS[field_type]
            if q.input.kind not in allowed:
                raise ValueError(
                    f"question {qkey!r}: input.kind={q.input.kind!r} is "
                    f"incompatible with data type {field_type!r} "
                    f"(allowed: {sorted(allowed)})"
                )
            # Choice inputs must declare options; non-choice inputs must not.
            needs_options = q.input.kind in {"single_choice", "multi_choice"}
            if needs_options and not q.input.options:
                raise ValueError(f"question {qkey!r}: {q.input.kind} requires options")
            if not needs_options and q.input.options:
                raise ValueError(
                    f"question {qkey!r}: options not allowed for {q.input.kind}"
                )
            # If the data field constrains values, every option must be in it.
            if q.input.options and self.data_model[qkey].values is not None:
                allowed_values = set(self.data_model[qkey].values or [])
                for opt in q.input.options:
                    if opt.value not in allowed_values:
                        raise ValueError(
                            f"question {qkey!r}: option {opt.value!r} not in "
                            f"data_model values {sorted(allowed_values)}"
                        )

        # Steps reference real questions, with no duplicates and no orphans.
        seen: set[str] = set()
        for step in self.steps:
            for qkey in step.questions:
                if qkey not in self.questions:
                    raise ValueError(
                        f"step {step.id!r} references unknown question {qkey!r}"
                    )
                if qkey in seen:
                    raise ValueError(
                        f"question {qkey!r} appears in multiple steps"
                    )
                seen.add(qkey)
        unreferenced = set(self.questions) - seen
        if unreferenced:
            raise ValueError(
                f"questions not assigned to any step: {sorted(unreferenced)}"
            )

        return self

    def required_keys(self, answers: dict[str, Any] | None = None) -> set[str]:
        """Set of question keys whose answers are required given current
        answers (i.e., visible after evaluating predicates)."""
        from pathwise.core.predicate import evaluate

        answers = answers or {}
        out: set[str] = set()
        for step in self.steps:
            if not evaluate(step.when, answers):
                continue
            for qkey in step.questions:
                q = self.questions[qkey]
                if not evaluate(q.when, answers):
                    continue
                if q.required:
                    out.add(qkey)
        return out

    def visible_question_keys(self, answers: dict[str, Any] | None = None) -> set[str]:
        from pathwise.core.predicate import evaluate

        answers = answers or {}
        out: set[str] = set()
        for step in self.steps:
            if not evaluate(step.when, answers):
                continue
            for qkey in step.questions:
                if evaluate(self.questions[qkey].when, answers):
                    out.add(qkey)
        return out
