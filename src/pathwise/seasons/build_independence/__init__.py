"""Build Independence — life-strategy season for 17–20 year olds.

Revisions live under ``revisions/<rev>/``. The registry in ``revisions/__init__.py``
exposes the available revisions and the latest. Routing is performed by
``pathwise.core.season.get_pack``.
"""

from pathwise.seasons.build_independence.revisions import latest, revisions

__all__ = ["latest", "revisions"]
