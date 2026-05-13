"""Longitudinal check-ins on the life-state.

The model (`model.md` §2.4) is explicit that the artifact is a *policy*,
not a plan: re-optimize at each new observation. Roadmap.md #1 calls this
out as the one-bet feature — re-run the policy weekly off light-touch
check-ins, detect drift on each component of `L`, and surface trajectory
instead of a frozen artifact.

This module is the data layer for that loop. It defines:

- ``Checkin``: a sparse, time-stamped observation of a few fast-moving
  ``L`` components (buffer hours, emotional impact, fitness practice,
  time quality). The set is intentionally small — these are the things a
  user can credibly self-report in a single SMS reply.
- ``CheckinService``: append-only persistence under
  ``seasons/{season_id}/checkins.jsonl``.
- ``compute_drift``: per-component direction + consecutive-fall streak
  detection. A streak of N consecutive drops on the same component is
  the signal worth pinging the user about ("ζ has fallen for three
  weeks" — roadmap.md #1).

Scheduling and SMS round-tripping are intentionally separate concerns;
this layer is what records and analyzes observations regardless of how
they arrive (API, CLI, SMS webhook later).
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from pathwise.core.store import FileStore

# Components we accept observations for. Each maps to a sub-component of
# ``L`` in the model. Keeping the set small keeps the per-checkin survey
# under ~5 numbers — credible for SMS.
#
# Conventions (all numeric so trends are well-defined):
#   b     — buffer hours per week           (0..168, raw count)
#   eta   — net emotional impact            (-2..+2, signed Likert)
#   zeta  — fitness practice                ( 1..5,  Likert)
#   q     — quality of time / energy        ( 1..5,  Likert)
KNOWN_COMPONENTS: tuple[str, ...] = ("b", "eta", "zeta", "q")

_RANGES: dict[str, tuple[float, float]] = {
    "b": (0.0, 168.0),
    "eta": (-2.0, 2.0),
    "zeta": (1.0, 5.0),
    "q": (1.0, 5.0),
}

# Default falling-streak threshold. Roadmap.md cites three weeks ("when ζ
# has fallen for three weeks, that's a notification").
DEFAULT_FALLING_STREAK = 3


class CheckinError(ValueError):
    """Raised on invalid observation input."""


@dataclass
class Checkin:
    user_id: str
    season_id: str
    at: float
    observations: dict[str, float]
    note: str | None = None


@dataclass
class ComponentDrift:
    component: str
    latest: float
    direction: Literal["rising", "falling", "stable", "unknown"]
    falling_streak: int
    rising_streak: int
    samples: int
    delta_from_first: float


@dataclass
class DriftReport:
    season_id: str
    user_id: str
    sample_count: int
    components: dict[str, ComponentDrift] = field(default_factory=dict)
    falling_alerts: list[str] = field(default_factory=list)

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "season_id": self.season_id,
            "user_id": self.user_id,
            "sample_count": self.sample_count,
            "components": {k: asdict(v) for k, v in self.components.items()},
            "falling_alerts": list(self.falling_alerts),
        }


def _validate_observations(observations: dict[str, float]) -> dict[str, float]:
    if not observations:
        raise CheckinError("a check-in must report at least one observation")
    cleaned: dict[str, float] = {}
    for key, raw in observations.items():
        if key not in KNOWN_COMPONENTS:
            raise CheckinError(
                f"unknown component {key!r}; expected one of {KNOWN_COMPONENTS}"
            )
        try:
            value = float(raw)
        except (TypeError, ValueError) as exc:
            raise CheckinError(f"component {key!r} must be numeric") from exc
        lo, hi = _RANGES[key]
        if not (lo <= value <= hi):
            raise CheckinError(
                f"component {key!r}={value} outside expected range [{lo}, {hi}]"
            )
        cleaned[key] = value
    return cleaned


class CheckinService:
    """Append-only persistence + drift analysis for check-ins."""

    def __init__(self, store: FileStore) -> None:
        self.store = store

    def _path(self, user_id: str, season_id: str):
        return self.store.season_dir(user_id, season_id) / "checkins.jsonl"

    def record(
        self,
        *,
        user_id: str,
        season_id: str,
        observations: dict[str, float],
        note: str | None = None,
        at: float | None = None,
    ) -> Checkin:
        cleaned = _validate_observations(observations)
        ts = at if at is not None else time.time()
        checkin = Checkin(
            user_id=user_id,
            season_id=season_id,
            at=ts,
            observations=cleaned,
            note=(note.strip() or None) if note else None,
        )
        self.store.append_jsonl(
            self._path(user_id, season_id),
            {
                "at": checkin.at,
                "observations": checkin.observations,
                "note": checkin.note,
            },
        )
        return checkin

    def list(self, user_id: str, season_id: str) -> list[Checkin]:
        records = self.store.read_jsonl(self._path(user_id, season_id))
        out: list[Checkin] = []
        for rec in records:
            try:
                obs = {k: float(v) for k, v in (rec.get("observations") or {}).items()}
            except (TypeError, ValueError):
                continue
            out.append(
                Checkin(
                    user_id=user_id,
                    season_id=season_id,
                    at=float(rec.get("at", 0.0)),
                    observations=obs,
                    note=rec.get("note"),
                )
            )
        out.sort(key=lambda c: c.at)
        return out

    def drift(
        self,
        user_id: str,
        season_id: str,
        *,
        falling_streak: int = DEFAULT_FALLING_STREAK,
    ) -> DriftReport:
        return compute_drift(
            self.list(user_id, season_id),
            user_id=user_id,
            season_id=season_id,
            falling_streak=falling_streak,
        )


def compute_drift(
    checkins: list[Checkin],
    *,
    user_id: str,
    season_id: str,
    falling_streak: int = DEFAULT_FALLING_STREAK,
) -> DriftReport:
    """Per-component direction + consecutive-drop streak.

    A component "falls" between two adjacent samples when its later value
    is strictly less than its earlier value. ``falling_streak`` is the
    number of consecutive falls (== ``falling_streak + 1`` consecutive
    decreasing samples) needed to fire an alert.

    Direction is reported from the last two samples — most useful for a
    one-glance "where is this heading right now?" view. ``delta_from_first``
    captures the longer-arc movement.
    """
    report = DriftReport(
        season_id=season_id, user_id=user_id, sample_count=len(checkins)
    )
    if not checkins:
        return report

    # Bucket samples by component, preserving chronological order.
    series: dict[str, list[float]] = {k: [] for k in KNOWN_COMPONENTS}
    for c in checkins:
        for k, v in c.observations.items():
            if k in series:
                series[k].append(v)

    for component, values in series.items():
        if not values:
            continue

        latest = values[-1]
        delta_from_first = latest - values[0]

        if len(values) < 2:
            direction: Literal["rising", "falling", "stable", "unknown"] = "unknown"
        else:
            last, prev = values[-1], values[-2]
            if last < prev:
                direction = "falling"
            elif last > prev:
                direction = "rising"
            else:
                direction = "stable"

        falling = _trailing_streak(values, predicate=lambda a, b: b < a)
        rising = _trailing_streak(values, predicate=lambda a, b: b > a)

        report.components[component] = ComponentDrift(
            component=component,
            latest=latest,
            direction=direction,
            falling_streak=falling,
            rising_streak=rising,
            samples=len(values),
            delta_from_first=delta_from_first,
        )

        if falling >= falling_streak:
            report.falling_alerts.append(component)

    return report


def _trailing_streak(values: list[float], *, predicate) -> int:
    """Count consecutive adjacent transitions from the end that satisfy
    ``predicate(earlier, later)``. Returns 0 if fewer than 2 samples.
    """
    streak = 0
    for i in range(len(values) - 1, 0, -1):
        if predicate(values[i - 1], values[i]):
            streak += 1
        else:
            break
    return streak


__all__ = [
    "Checkin",
    "CheckinError",
    "CheckinService",
    "ComponentDrift",
    "DriftReport",
    "DEFAULT_FALLING_STREAK",
    "KNOWN_COMPONENTS",
    "compute_drift",
]
