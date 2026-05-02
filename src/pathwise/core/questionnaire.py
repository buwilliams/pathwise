from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from pathwise.core.season import Question, SeasonPack
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


class AnswerValidationError(ValueError):
    pass


def coerce_answer(question: Question, raw: Any) -> Any:
    """Validate and coerce a raw answer value against its question's type."""
    if raw is None or raw == "":
        if question.required:
            raise AnswerValidationError(f"{question.key}: required")
        return None

    t = question.type
    if t == "yes_no":
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str) and raw.lower() in ("yes", "y", "true", "1"):
            return True
        if isinstance(raw, str) and raw.lower() in ("no", "n", "false", "0"):
            return False
        raise AnswerValidationError(f"{question.key}: expected yes/no")

    if t in ("number", "money", "hours", "scale"):
        try:
            value = float(raw)
        except (TypeError, ValueError) as exc:
            raise AnswerValidationError(f"{question.key}: expected number") from exc
        if question.min is not None and value < question.min:
            raise AnswerValidationError(
                f"{question.key}: must be >= {question.min}"
            )
        if question.max is not None and value > question.max:
            raise AnswerValidationError(
                f"{question.key}: must be <= {question.max}"
            )
        # money / scale stored as int when exact
        if value.is_integer():
            return int(value)
        return value

    if t == "single_choice":
        valid = {o.value for o in (question.options or [])}
        if raw not in valid:
            raise AnswerValidationError(
                f"{question.key}: must be one of {sorted(valid)}"
            )
        return raw

    if t == "multi_choice":
        if isinstance(raw, str):
            raw = [raw]
        if not isinstance(raw, list):
            raise AnswerValidationError(f"{question.key}: expected list")
        valid = {o.value for o in (question.options or [])}
        for v in raw:
            if v not in valid:
                raise AnswerValidationError(
                    f"{question.key}: invalid choice {v!r}; must be subset of {sorted(valid)}"
                )
        return list(raw)

    if t == "text":
        if not isinstance(raw, str):
            raise AnswerValidationError(f"{question.key}: expected text")
        return raw.strip()

    raise AnswerValidationError(f"{question.key}: unknown question type {t!r}")


class QuestionnaireService:
    def __init__(self, store: FileStore) -> None:
        self.store = store

    def get_answers(self, user_id: str, season_id: str) -> dict[str, Any]:
        return self.store.read_json(self.store.answers_path(user_id, season_id))

    def set_answer(
        self,
        user_id: str,
        pack: SeasonPack,
        key: str,
        raw_value: Any,
        *,
        now: float | None = None,
    ) -> Any:
        question = pack.question(key)  # KeyError if unknown
        coerced = coerce_answer(question, raw_value)
        now = now if now is not None else time.time()

        current = self.get_answers(user_id, pack.id)
        current[key] = coerced
        self.store.write_json(self.store.answers_path(user_id, pack.id), current)
        self.store.append_jsonl(
            self.store.answers_history_path(user_id, pack.id),
            {"at": now, "key": key, "value": coerced},
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
        # Validate all up front before writing any
        coerced: dict[str, Any] = {}
        for key, raw in values.items():
            question = pack.question(key)
            coerced[key] = coerce_answer(question, raw)

        now = now if now is not None else time.time()
        current = self.get_answers(user_id, pack.id)
        current.update(coerced)
        self.store.write_json(self.store.answers_path(user_id, pack.id), current)
        for key, value in coerced.items():
            self.store.append_jsonl(
                self.store.answers_history_path(user_id, pack.id),
                {"at": now, "key": key, "value": value},
            )
        return current

    def completion(self, user_id: str, pack: SeasonPack) -> CompletionStatus:
        answers = self.get_answers(user_id, pack.id)
        required = pack.required_keys()
        missing = sorted(k for k in required if answers.get(k) in (None, "", []))
        optional_total = len(pack.questions) - len(required)
        return CompletionStatus(
            answered=sum(1 for v in answers.values() if v not in (None, "", [])),
            required_total=len(required),
            optional_total=optional_total,
            missing_required=missing,
        )
