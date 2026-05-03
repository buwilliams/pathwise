from __future__ import annotations

import importlib
import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any, Literal

import yaml

from pathwise.core.questionnaire_schema import Questionnaire


@dataclass
class Scenario:
    id: str
    label: str
    description: str
    car: bool
    moves_out: bool
    income_growth: bool
    # Per-decision recoverability — how easily a teen can reverse / repair / step
    # back from the choice. Distinct from life-state fragility (which describes
    # exposure to shocks). See model.md §Recoverability.
    recoverability: Literal["high", "medium", "low"] = "medium"
    # Which named path this scenario belongs to in the user-facing plan output.
    bucket: Literal["fast_freedom", "compounding_freedom", "skill_leverage"] = "skill_leverage"


@dataclass
class SeasonPack:
    id: str
    name: str
    summary: str
    version: str
    pack_dir: Path
    questionnaire: Questionnaire
    weights: dict[str, float]
    scenarios: list[Scenario]
    prompts_dir: Path
    age_min: int | None = None
    age_max: int | None = None

    @property
    def revision(self) -> str:
        return self.version

    def prompt_path(self, name: str) -> Path:
        return self.prompts_dir / f"{name}.md"


def _load_yaml(path: Path) -> Any:
    with open(path) as f:
        return yaml.safe_load(f)


def _load_questionnaire(path: Path) -> Questionnaire:
    with open(path) as f:
        raw = json.load(f)
    return Questionnaire.model_validate(raw)


def load_pack(pack_dir: Path) -> SeasonPack:
    pack_dir = pack_dir.resolve()
    if not pack_dir.is_dir():
        raise FileNotFoundError(pack_dir)

    with open(pack_dir / "pack.toml", "rb") as f:
        meta = tomllib.load(f)

    pack_meta = meta["pack"]

    questionnaire = _load_questionnaire(pack_dir / "questionnaire.json")
    weights = _load_yaml(pack_dir / "weights.yaml")["weights"]
    scenarios = [Scenario(**s) for s in _load_yaml(pack_dir / "scenarios.yaml")["scenarios"]]

    return SeasonPack(
        id=pack_meta["id"],
        name=pack_meta["name"],
        summary=pack_meta["summary"],
        version=pack_meta["version"],
        pack_dir=pack_dir,
        questionnaire=questionnaire,
        weights=weights,
        scenarios=scenarios,
        prompts_dir=pack_dir / "prompts",
        age_min=pack_meta.get("age_min"),
        age_max=pack_meta.get("age_max"),
    )


# ---------------------------------------------------------------------------
# Revision-aware resolution
# ---------------------------------------------------------------------------


def _season_module_name(season_id: str) -> str:
    return season_id.replace("-", "_")


def _revisions_module(season_id: str) -> ModuleType:
    """Import ``pathwise.seasons.<id_snake>.revisions`` and return it.

    Raises KeyError if the season package or its revisions registry is missing.
    """
    module_path = f"pathwise.seasons.{_season_module_name(season_id)}.revisions"
    try:
        return importlib.import_module(module_path)
    except ImportError as exc:
        raise KeyError(f"Season pack not found: {season_id}") from exc


def list_revisions(season_id: str) -> list[str]:
    """All revisions registered for a season, sorted by semver ascending."""
    mod = _revisions_module(season_id)
    revs: dict[str, Any] = mod.revisions
    return sorted(revs, key=lambda r: tuple(int(p) for p in r.split(".")))


def latest_revision(season_id: str) -> str:
    return _revisions_module(season_id).latest


def get_pack(season_id: str, revision: str | None = None) -> SeasonPack:
    """Load the season pack for a specific revision.

    ``revision=None`` means latest. The returned ``SeasonPack`` has its
    ``pack_dir`` pointing at the revision's directory, so prompts/yaml all
    resolve to that revision's snapshot.
    """
    mod = _revisions_module(season_id)
    rev = revision or mod.latest
    revs: dict[str, ModuleType] = mod.revisions
    if rev not in revs:
        raise KeyError(f"Revision {rev!r} not found for season {season_id!r}")
    return revs[rev].make_logic().pack


# ---------------------------------------------------------------------------
# Listing — used by /seasons and `pathwise season list`
# ---------------------------------------------------------------------------


@dataclass
class SeasonSummary:
    id: str
    name: str
    summary: str
    version: str
    revision: str
    available_revisions: list[str]
    age_min: int | None
    age_max: int | None


def packs_root() -> Path:
    """Default location: src/pathwise/seasons/"""
    import pathwise

    return Path(pathwise.__file__).resolve().parent / "seasons"


def _discover_season_ids(seasons_root: Path | None = None) -> list[str]:
    """Find season packages on disk: any seasons/<dir>/revisions/."""
    root = seasons_root or packs_root()
    if not root.is_dir():
        return []
    ids: list[str] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name.startswith("_") or child.name.startswith("."):
            continue
        if (child / "revisions").is_dir():
            # Module name uses underscores; pack id uses dashes — convert.
            ids.append(child.name.replace("_", "-"))
    return ids


def list_packs(seasons_root: Path | None = None) -> list[SeasonPack]:
    """Latest pack per season. Used wherever the listing should reflect what's
    current — the home page, /seasons, `pathwise season list`."""
    return [get_pack(sid) for sid in _discover_season_ids(seasons_root)]


def list_seasons(seasons_root: Path | None = None) -> list[SeasonSummary]:
    """Same as list_packs but pre-bundles revision history for the API."""
    out: list[SeasonSummary] = []
    for sid in _discover_season_ids(seasons_root):
        revs = list_revisions(sid)
        pack = get_pack(sid)  # latest
        out.append(
            SeasonSummary(
                id=pack.id,
                name=pack.name,
                summary=pack.summary,
                version=pack.version,
                revision=pack.version,
                available_revisions=revs,
                age_min=pack.age_min,
                age_max=pack.age_max,
            )
        )
    return out
