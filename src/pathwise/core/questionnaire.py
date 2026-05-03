from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from pathwise.core.questionnaire_schema import DataField, Question, Questionnaire
from pathwise.core.season import SeasonPack
from pathwise.core.store import FileStore


@dataclass
class CompletionStatus:
    answered: int
    required_total: int
    optional_total: int
    missing_required: list[str]

    @property
    def is_complete(self) -> bool:
        return not self.missing_required

    @property
    def percent(self) -> int:
        if self.required_total == 0:
            return 100
        return int(round(100 * (self.required_total - len(self.missing_required)) / self.required_total))

    def to_dict(self) -> dict[str, Any]:
        return {
            "answered": self.answered,
            "required_total": self.required_total,
            "optional_total": self.optional_total,
            "missing_required": list(self.missing_required),
            "percent": self.percent,
            "is_complete": self.is_complete,
        }


class AnswerValidationError(ValueError):
    pass


def coerce_answer(
    key: str, field: DataField, question: Question, raw: Any
) -> Any:
    """Validate and coerce a raw answer value against its data-model type.

    The data-model type is the source of truth; ``question.input.kind`` only
    decides UI rendering. Bounds (min/max) are pulled from the data field —
    UI overrides on the question's input are presentational only.
    """
    if raw is None or raw == "":
        if question.required:
            raise AnswerValidationError(f"{key}: required")
        return None

    t = field.type

    if t == "yes_no":
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str) and raw.lower() in ("yes", "y", "true", "1"):
            return True
        if isinstance(raw, str) and raw.lower() in ("no", "n", "false", "0"):
            return False
        raise AnswerValidationError(f"{key}: expected yes/no")

    if t in ("number", "money", "hours", "scale"):
        try:
            value = float(raw)
        except (TypeError, ValueError) as exc:
            raise AnswerValidationError(f"{key}: expected number") from exc
        if field.min is not None and value < field.min:
            raise AnswerValidationError(f"{key}: must be >= {field.min}")
        if field.max is not None and value > field.max:
            raise AnswerValidationError(f"{key}: must be <= {field.max}")
        if value.is_integer():
            return int(value)
        return value

    if t == "string":
        if not isinstance(raw, str):
            raise AnswerValidationError(f"{key}: expected text")
        coerced = raw.strip()
        if field.values is not None and coerced not in field.values:
            raise AnswerValidationError(
                f"{key}: must be one of {sorted(field.values)}"
            )
        return coerced

    if t == "string_set":
        if isinstance(raw, str):
            raw = [raw]
        if not isinstance(raw, list):
            raise AnswerValidationError(f"{key}: expected list")
        if field.values is not None:
            allowed = set(field.values)
            for v in raw:
                if v not in allowed:
                    raise AnswerValidationError(
                        f"{key}: invalid choice {v!r}; must be subset of "
                        f"{sorted(allowed)}"
                    )
        return list(raw)

    raise AnswerValidationError(f"{key}: unknown data type {t!r}")


def _missing(value: Any) -> bool:
    return value in (None, "", [])


def _compute_completion(
    questionnaire: Questionnaire, answers: dict[str, Any]
) -> CompletionStatus:
    required = questionnaire.required_keys(answers)
    visible = questionnaire.visible_question_keys(answers)
    missing = sorted(k for k in required if _missing(answers.get(k)))
    optional_total = len(visible) - len(required)
    answered = sum(
        1
        for k in visible
        if not _missing(answers.get(k))
    )
    return CompletionStatus(
        answered=answered,
        required_total=len(required),
        optional_total=max(optional_total, 0),
        missing_required=missing,
    )


class QuestionnaireService:
    def __init__(self, store: FileStore) -> None:
        self.store = store

    def get_answers(self, user_id: str, season_id: str) -> dict[str, Any]:
        return self.store.read_json(self.store.answers_path(user_id, season_id))

    def _coerce(self, pack: SeasonPack, key: str, raw: Any) -> Any:
        q = pack.questionnaire
        if key not in q.data_model:
            raise AnswerValidationError(f"{key}: not in data model")
        if key not in q.questions:
            raise AnswerValidationError(f"{key}: not asked in this revision")
        return coerce_answer(key, q.data_model[key], q.questions[key], raw)

    def set_answer(
        self,
        user_id: str,
        pack: SeasonPack,
        key: str,
        raw_value: Any,
        *,
        now: float | None = None,
    ) -> Any:
        coerced = self._coerce(pack, key, raw_value)
        now = now if now is not None else time.time()

        current = self.get_answers(user_id, pack.id)
        current[key] = coerced
        self.store.write_json(self.store.answers_path(user_id, pack.id), current)
        self.store.write_json(
            self.store.answers_meta_path(user_id, pack.id),
            {"pack_version": pack.version, "updated_at": now},
        )
        self.store.append_jsonl(
            self.store.answers_history_path(user_id, pack.id),
            {"at": now, "key": key, "value": coerced, "pack_version": pack.version},
        )
        return coerced

    def set_answers(
        self,
        user_id: str,
        pack: SeasonPack,
        values: dict[str, Any],
        *,
        now: float | None = None,
    ) -> dict[str, Any]:
        # Validate all up front before writing any.
        coerced: dict[str, Any] = {}
        for key, raw in values.items():
            coerced[key] = self._coerce(pack, key, raw)

        now = now if now is not None else time.time()
        current = self.get_answers(user_id, pack.id)
        current.update(coerced)
        self.store.write_json(self.store.answers_path(user_id, pack.id), current)
        self.store.write_json(
            self.store.answers_meta_path(user_id, pack.id),
            {"pack_version": pack.version, "updated_at": now},
        )
        for key, value in coerced.items():
            self.store.append_jsonl(
                self.store.answers_history_path(user_id, pack.id),
                {"at": now, "key": key, "value": value, "pack_version": pack.version},
            )
        return current

    def completion(self, user_id: str, pack: SeasonPack) -> CompletionStatus:
        answers = self.get_answers(user_id, pack.id)
        return _compute_completion(pack.questionnaire, answers)
