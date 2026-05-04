"""Midlife — life-strategy season for adults roughly 35–45.

Concerns differ from build-independence: existing momentum, accumulated
responsibilities, debts, caregiving load, divorce or partnership change,
loss of community, and the felt need to make real changes rather than
endure. Same formal model ``L = {V, T, A, K, W}`` as build-independence;
the questionnaire, scenarios, and prompts are reworked for the season.

Revisions live under ``revisions/<rev>/``. The registry in
``revisions/__init__.py`` exposes the available revisions and the latest.
Routing is performed by ``pathwise.core.season.get_pack``.
"""

from pathwise.seasons.midlife.revisions import latest, revisions

__all__ = ["latest", "revisions"]
