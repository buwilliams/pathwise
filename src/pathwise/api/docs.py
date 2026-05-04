"""Technical-details viewer.

Surfaces per-season-pack model essays — any ``*.md`` directly under the
*latest* revision of a season pack (e.g.
``seasons/build_independence/revisions/v0_3_0/model.md``). These describe
the thinking and math behind that season's planner.

Slugs are ``{pack_id}-{stem}`` so two packs' ``model.md`` files don't
collide. Slug routing rejects path traversal (only alnum + ``-_``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from pathwise.api.deps import CurrentUserId
from pathwise.core.season import list_packs

router = APIRouter(prefix="/technical", tags=["technical"])


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
    """Collect available docs as ``{slug: path}``, namespaced by pack id."""
    paths: dict[str, Path] = {}
    for pack in list_packs():
        for p in sorted(pack.pack_dir.glob("*.md")):
            paths[f"{pack.id}-{p.stem}"] = p
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
