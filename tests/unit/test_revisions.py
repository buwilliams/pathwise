"""Tests for revision-aware season loading.

Stands up a synthetic season package on disk under a tmp dir, makes it
importable, and verifies that ``get_pack`` resolves to the right revision
and that ``latest_revision`` reflects the highest semver.
"""

from __future__ import annotations

import importlib
import sys
import textwrap
from pathlib import Path

import pytest


def _write_pack(rev_dir: Path, pack_id: str, version: str) -> None:
    rev_dir.mkdir(parents=True, exist_ok=True)
    (rev_dir / "pack.toml").write_text(
        textwrap.dedent(
            f"""
            [pack]
            id = "{pack_id}"
            name = "Test Season"
            summary = "synthetic"
            version = "{version}"
            """
        ).strip()
    )
    (rev_dir / "questions.yaml").write_text(
        "sections: []\n"
        "questions:\n"
        "  - key: q1\n"
        "    prompt: 'a question'\n"
        "    type: text\n"
        "    section: s\n"
        "    required: false\n"
    )
    (rev_dir / "weights.yaml").write_text("weights: {c: 1, s: 1}\n")
    (rev_dir / "scenarios.yaml").write_text(
        "scenarios:\n"
        "  - {id: only, label: only, description: x,"
        " car: false, moves_out: false, income_growth: false}\n"
    )
    (rev_dir / "prompts").mkdir(exist_ok=True)
    (rev_dir / "prompts" / "system.md").write_text("voice")
    (rev_dir / "prompts" / "research.md").write_text("research")
    (rev_dir / "prompts" / "plan.md").write_text("plan")


@pytest.fixture
def two_revision_season(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Create a synthetic ``test_season`` package with two revisions and
    register it on sys.path so ``importlib`` can find it from
    ``pathwise.seasons.test_season``.
    """
    season_pkg = tmp_path / "pathwise_test_seasons" / "pathwise" / "seasons" / "test_season"
    revisions_pkg = season_pkg / "revisions"
    rev_a = revisions_pkg / "v0_1_0"
    rev_b = revisions_pkg / "v0_2_0"

    for d in (season_pkg.parent.parent, season_pkg.parent, season_pkg, revisions_pkg):
        d.mkdir(parents=True, exist_ok=True)
        (d / "__init__.py").write_text("")

    _write_pack(rev_a, "test-season", "0.1.0")
    _write_pack(rev_b, "test-season", "0.2.0")

    (rev_a / "__init__.py").write_text(
        "from pathwise.seasons.test_season.revisions.v0_1_0.logic import make_logic\n"
    )
    (rev_b / "__init__.py").write_text(
        "from pathwise.seasons.test_season.revisions.v0_2_0.logic import make_logic\n"
    )

    logic_src = textwrap.dedent(
        """
        from pathlib import Path
        from pathwise.seasons._base import BaseLogic

        class Logic(BaseLogic):
            REVISION_DIR = Path(__file__).resolve().parent

        def make_logic():
            return Logic.make()
        """
    ).strip()
    (rev_a / "logic.py").write_text(logic_src)
    (rev_b / "logic.py").write_text(logic_src)

    (revisions_pkg / "__init__.py").write_text(
        textwrap.dedent(
            """
            from pathwise.seasons.test_season.revisions import v0_1_0, v0_2_0

            revisions = {"0.1.0": v0_1_0, "0.2.0": v0_2_0}
            latest = "0.2.0"
            """
        ).strip()
    )

    # Make pathwise.seasons.test_season importable from this throwaway tree
    # WITHOUT clobbering the installed pathwise package — register the
    # synthetic package as a child module of the real pathwise.seasons.
    seasons_pkg_path = tmp_path / "pathwise_test_seasons" / "pathwise" / "seasons"
    import pathwise.seasons as real_seasons

    real_seasons.__path__.append(str(seasons_pkg_path))

    # Reset import caches that may have already failed to find the module.
    for mod_name in list(sys.modules):
        if mod_name.startswith("pathwise.seasons.test_season"):
            sys.modules.pop(mod_name)
    importlib.invalidate_caches()

    yield "test-season"

    # Cleanup: remove the appended path entry and any imported submodules.
    real_seasons.__path__.remove(str(seasons_pkg_path))
    for mod_name in list(sys.modules):
        if mod_name.startswith("pathwise.seasons.test_season"):
            sys.modules.pop(mod_name)


def test_latest_revision_resolves(two_revision_season: str) -> None:
    from pathwise.core.season import get_pack, latest_revision, list_revisions

    assert list_revisions(two_revision_season) == ["0.1.0", "0.2.0"]
    assert latest_revision(two_revision_season) == "0.2.0"
    assert get_pack(two_revision_season).revision == "0.2.0"


def test_pinned_revision_resolves(two_revision_season: str) -> None:
    from pathwise.core.season import get_pack

    pack = get_pack(two_revision_season, revision="0.1.0")
    assert pack.revision == "0.1.0"
    assert pack.pack_dir.name == "v0_1_0"
