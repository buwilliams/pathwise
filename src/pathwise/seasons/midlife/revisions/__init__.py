"""Registry of midlife revisions.

Add a new revision by:
1. Creating ``revisions/v<X>_<Y>_<Z>/`` with ``pack.toml`` (version="X.Y.Z"),
   the data files, and a ``logic.py`` exporting ``make_logic()``.
2. Importing it below and adding it to ``revisions``.

``latest`` is the highest semver among registered revisions.
"""

from __future__ import annotations

from types import ModuleType

from pathwise.seasons.midlife.revisions import v0_1_0


def _semver_key(rev: str) -> tuple[int, ...]:
    return tuple(int(part) for part in rev.split("."))


revisions: dict[str, ModuleType] = {
    "0.1.0": v0_1_0,
}

latest: str = max(revisions, key=_semver_key)

__all__ = ["latest", "revisions"]
