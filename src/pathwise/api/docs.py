"""Technical-details viewer.

Surfaces markdown documents from two places:

1. Per-season-pack model essays — any ``*.md`` directly under a season pack's
   root directory (e.g. ``seasons/transition_to_adulthood/build-independence.md``).
   These describe the thinking and math behind that season's planner.
2. A repo-level ``docs/`` directory (optional) — for cross-cutting docs that
   don't belong to any single season.

Slugs are the file's stem; if the same stem appears in both places, the docs/
copy wins. Slug routing rejects path traversal (only alnum + ``-_``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from pathwise.api.deps import CurrentUserId
from pathwise.core.season import list_packs, packs_root

router = APIRouter(prefix="/technical", tags=["technical"])


def _docs_dir() -> Path:
    """Optional repo-level /docs/ for cross-cutting documents."""
    import pathwise

    return Path(pathwise.__file__).resolve().parent.parent.parent / "docs"


def _is_safe_slug(slug: str) -> bool:
    return bool(slug) and all(c.isalnum() or c in "-_" for c in slug)


def _title_from_markdown(text: str, fallback: str) -> str:
    """Pull the first level-1 heading; fall back if none found."""
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("# "):
            return s[2:].strip()
    return fallback


def _all_doc_paths() -> dict[str, Path]:
    """Collect available docs as ``{slug: path}``. docs/ wins on slug clash."""
    paths: dict[str, Path] = {}
    for pack in list_packs(packs_root()):
        for p in sorted(pack.pack_dir.glob("*.md")):
            paths.setdefault(p.stem, p)
    docs_dir = _docs_dir()
    if docs_dir.exists():
        for p in sorted(docs_dir.glob("*.md")):
            paths[p.stem] = p  # docs/ overrides
    return paths


@router.get("")
def list_all(user_id: CurrentUserId) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for slug, path in sorted(_all_doc_paths().items()):
        text = path.read_text()
        out.append({"slug": slug, "title": _title_from_markdown(text, slug)})
    return out


@router.get("/{slug}")
def show(slug: str, user_id: CurrentUserId) -> dict[str, Any]:
    if not _is_safe_slug(slug):
        raise HTTPException(status_code=400, detail="Invalid doc slug.")
    path = _all_doc_paths().get(slug)
    if path is None:
        raise HTTPException(status_code=404, detail="Doc not found.")
    text = path.read_text()
    return {
        "slug": slug,
        "title": _title_from_markdown(text, slug),
        "markdown": text,
    }
