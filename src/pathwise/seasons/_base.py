"""Per-revision logic surface.

Each season revision lives in its own directory under
``seasons/<season>/revisions/<rev>/`` and ships a ``logic.py`` exporting
``make_logic() -> SeasonLogic``. ``SeasonLogic`` binds the loaded ``SeasonPack``
to whatever per-revision behavior that revision needs. ``BaseLogic`` is the
default — it delegates to the generic implementations in ``core/`` so a new
revision that doesn't change behavior is a one-line subclass.

Routing happens in ``core/season.py``: ``get_pack(season_id, revision=None)``
imports ``pathwise.seasons.<id_snake>.revisions.<rev>.logic``, calls
``make_logic()``, and returns ``logic.pack``. Callers that need behavior call
``get_logic(season_id, revision=None)`` and use the returned object directly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from pathwise.core.season import SeasonPack, load_pack


class SeasonLogic(Protocol):
    pack: SeasonPack

    def compute_life_state(self, answers: dict[str, Any]) -> Any: ...

    def score_all(self, life: Any, research_data: dict[str, Any]) -> list[Any]: ...


class BaseLogic:
    """Default per-revision logic. Delegates everything to ``core``.

    Revisions that don't need to change behavior subclass this with no
    overrides and just override ``REVISION_DIR``.
    """

    REVISION_DIR: Path

    def __init__(self, pack: SeasonPack) -> None:
        self.pack = pack

    @classmethod
    def make(cls) -> "BaseLogic":
        pack = load_pack(cls.REVISION_DIR)
        return cls(pack)

    def compute_life_state(self, answers: dict[str, Any]) -> Any:
        from pathwise.core.life_state import compute_life_state

        return compute_life_state(answers)

    def score_all(self, life: Any, research_data: dict[str, Any]) -> list[Any]:
        from pathwise.core.momentum import score_all

        return score_all(self.pack.scenarios, life, self.pack.weights, research_data)
