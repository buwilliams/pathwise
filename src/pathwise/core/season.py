from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

QuestionType = Literal[
    "single_choice",
    "multi_choice",
    "number",
    "money",
    "hours",
    "scale",
    "yes_no",
    "text",
]


@dataclass
class QuestionOption:
    value: str
    label: str


@dataclass
class Question:
    key: str
    prompt: str
    type: QuestionType
    section: str
    required: bool = True
    help: str | None = None
    options: list[QuestionOption] | None = None
    min: float | None = None
    max: float | None = None
    unit: str | None = None
    placeholder: str | None = None


@dataclass
class Section:
    id: str
    title: str
    blurb: str | None = None


@dataclass
class Scenario:
    id: str
    label: str
    description: str
    car: bool
    moves_out: bool
    income_growth: bool


@dataclass
class SeasonPack:
    id: str
    name: str
    summary: str
    version: str
    pack_dir: Path
    sections: list[Section]
    questions: list[Question]
    weights: dict[str, float]
    scenarios: list[Scenario]
    prompts_dir: Path
    age_min: int | None = None
    age_max: int | None = None

    def question(self, key: str) -> Question:
        for q in self.questions:
            if q.key == key:
                return q
        raise KeyError(key)

    def question_keys(self) -> list[str]:
        return [q.key for q in self.questions]

    def required_keys(self) -> set[str]:
        return {q.key for q in self.questions if q.required}

    def prompt_path(self, name: str) -> Path:
        return self.prompts_dir / f"{name}.md"


def _load_yaml(path: Path) -> Any:
    with open(path) as f:
        return yaml.safe_load(f)


def load_pack(pack_dir: Path) -> SeasonPack:
    pack_dir = pack_dir.resolve()
    if not pack_dir.is_dir():
        raise FileNotFoundError(pack_dir)

    with open(pack_dir / "pack.toml", "rb") as f:
        meta = tomllib.load(f)

    pack_meta = meta["pack"]

    questions_raw = _load_yaml(pack_dir / "questions.yaml")
    sections = [Section(**s) for s in questions_raw.get("sections", [])]
    questions: list[Question] = []
    for q in questions_raw["questions"]:
        opts = q.pop("options", None)
        question = Question(
            **{**q, "options": [QuestionOption(**o) for o in opts] if opts else None}
        )
        questions.append(question)

    weights = _load_yaml(pack_dir / "weights.yaml")["weights"]
    scenarios = [Scenario(**s) for s in _load_yaml(pack_dir / "scenarios.yaml")["scenarios"]]

    return SeasonPack(
        id=pack_meta["id"],
        name=pack_meta["name"],
        summary=pack_meta["summary"],
        version=pack_meta["version"],
        pack_dir=pack_dir,
        sections=sections,
        questions=questions,
        weights=weights,
        scenarios=scenarios,
        prompts_dir=pack_dir / "prompts",
        age_min=pack_meta.get("age_min"),
        age_max=pack_meta.get("age_max"),
    )


def list_packs(seasons_root: Path) -> list[SeasonPack]:
    if not seasons_root.is_dir():
        return []
    packs: list[SeasonPack] = []
    for child in sorted(seasons_root.iterdir()):
        if (child / "pack.toml").exists():
            packs.append(load_pack(child))
    return packs


def packs_root() -> Path:
    """Default location: src/pathwise/seasons/"""
    import pathwise

    return Path(pathwise.__file__).resolve().parent / "seasons"


def get_pack(season_id: str, root: Path | None = None) -> SeasonPack:
    root = root or packs_root()
    candidate = root / season_id.replace("-", "_")
    if (candidate / "pack.toml").exists():
        return load_pack(candidate)
    # fallback: scan
    for p in list_packs(root):
        if p.id == season_id:
            return p
    raise KeyError(f"Season pack not found: {season_id}")
