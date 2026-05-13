from __future__ import annotations

import pytest

from pathwise.core.checkin import (
    Checkin,
    CheckinError,
    CheckinService,
    compute_drift,
)
from pathwise.core.store import FileStore

USER = "0" * 32
SEASON = "build-independence"


@pytest.fixture
def svc(store: FileStore) -> CheckinService:
    return CheckinService(store)


def test_record_persists_observations(svc: CheckinService) -> None:
    c = svc.record(
        user_id=USER,
        season_id=SEASON,
        observations={"b": 12.0, "eta": 1.0},
        note="good week",
        at=1000.0,
    )
    assert c.observations == {"b": 12.0, "eta": 1.0}
    assert c.note == "good week"

    listed = svc.list(USER, SEASON)
    assert len(listed) == 1
    assert listed[0].at == 1000.0
    assert listed[0].observations == {"b": 12.0, "eta": 1.0}


def test_record_rejects_empty_observations(svc: CheckinService) -> None:
    with pytest.raises(CheckinError):
        svc.record(user_id=USER, season_id=SEASON, observations={})


def test_record_rejects_unknown_component(svc: CheckinService) -> None:
    with pytest.raises(CheckinError):
        svc.record(
            user_id=USER, season_id=SEASON, observations={"banana": 1.0}
        )


def test_record_rejects_out_of_range_value(svc: CheckinService) -> None:
    with pytest.raises(CheckinError):
        svc.record(user_id=USER, season_id=SEASON, observations={"eta": 9.0})
    with pytest.raises(CheckinError):
        svc.record(user_id=USER, season_id=SEASON, observations={"zeta": 0.0})


def test_list_is_sorted_chronologically(svc: CheckinService) -> None:
    svc.record(user_id=USER, season_id=SEASON, observations={"q": 4}, at=300.0)
    svc.record(user_id=USER, season_id=SEASON, observations={"q": 3}, at=100.0)
    svc.record(user_id=USER, season_id=SEASON, observations={"q": 2}, at=200.0)

    listed = svc.list(USER, SEASON)
    assert [c.at for c in listed] == [100.0, 200.0, 300.0]


def _checkins(*pairs: tuple[float, dict[str, float]]) -> list[Checkin]:
    return [
        Checkin(user_id=USER, season_id=SEASON, at=t, observations=dict(o))
        for t, o in pairs
    ]


def test_drift_empty() -> None:
    report = compute_drift([], user_id=USER, season_id=SEASON)
    assert report.sample_count == 0
    assert report.components == {}
    assert report.falling_alerts == []


def test_drift_single_sample_direction_unknown() -> None:
    checkins = _checkins((1.0, {"zeta": 4}))
    report = compute_drift(checkins, user_id=USER, season_id=SEASON)
    zeta = report.components["zeta"]
    assert zeta.direction == "unknown"
    assert zeta.falling_streak == 0
    assert zeta.rising_streak == 0
    assert zeta.samples == 1
    assert zeta.delta_from_first == 0.0


def test_drift_falling_streak_triggers_alert() -> None:
    # ζ falls four weeks running — exactly the roadmap.md scenario
    checkins = _checkins(
        (1.0, {"zeta": 5}),
        (2.0, {"zeta": 4}),
        (3.0, {"zeta": 3}),
        (4.0, {"zeta": 2}),
    )
    report = compute_drift(checkins, user_id=USER, season_id=SEASON)
    zeta = report.components["zeta"]
    assert zeta.direction == "falling"
    assert zeta.falling_streak == 3
    assert zeta.delta_from_first == -3.0
    assert "zeta" in report.falling_alerts


def test_drift_rebound_breaks_streak() -> None:
    # falls, falls, then rises — streak resets
    checkins = _checkins(
        (1.0, {"q": 4}),
        (2.0, {"q": 3}),
        (3.0, {"q": 2}),
        (4.0, {"q": 4}),
    )
    report = compute_drift(checkins, user_id=USER, season_id=SEASON)
    q = report.components["q"]
    assert q.direction == "rising"
    assert q.falling_streak == 0
    assert q.rising_streak == 1
    assert "q" not in report.falling_alerts


def test_drift_threshold_respected() -> None:
    checkins = _checkins(
        (1.0, {"b": 15}),
        (2.0, {"b": 12}),
        (3.0, {"b": 10}),
    )
    # Two consecutive drops — streak == 2.
    report_default = compute_drift(checkins, user_id=USER, season_id=SEASON)
    assert "b" not in report_default.falling_alerts  # default streak == 3

    report_two = compute_drift(
        checkins, user_id=USER, season_id=SEASON, falling_streak=2
    )
    assert "b" in report_two.falling_alerts


def test_drift_component_independence() -> None:
    # ζ falling, η rising, b stable across the same sequence
    checkins = _checkins(
        (1.0, {"zeta": 5, "eta": -1, "b": 10}),
        (2.0, {"zeta": 4, "eta": 0, "b": 10}),
        (3.0, {"zeta": 3, "eta": 1, "b": 10}),
        (4.0, {"zeta": 2, "eta": 2, "b": 10}),
    )
    report = compute_drift(checkins, user_id=USER, season_id=SEASON)
    assert report.components["zeta"].direction == "falling"
    assert report.components["eta"].direction == "rising"
    assert report.components["b"].direction == "stable"
    assert report.falling_alerts == ["zeta"]


def test_drift_sparse_observations() -> None:
    # Each check-in only reports some components — series should still
    # be built per-component and only count samples that actually exist.
    checkins = _checkins(
        (1.0, {"zeta": 4}),
        (2.0, {"eta": 1}),
        (3.0, {"zeta": 3}),
        (4.0, {"zeta": 2}),
    )
    report = compute_drift(checkins, user_id=USER, season_id=SEASON)
    zeta = report.components["zeta"]
    assert zeta.samples == 3
    assert zeta.direction == "falling"
    assert zeta.falling_streak == 2
    eta = report.components["eta"]
    assert eta.samples == 1
    assert eta.direction == "unknown"


def test_service_drift_round_trip(svc: CheckinService) -> None:
    for at, val in [(1.0, 5), (2.0, 4), (3.0, 3), (4.0, 2)]:
        svc.record(user_id=USER, season_id=SEASON, observations={"zeta": val}, at=at)
    report = svc.drift(USER, SEASON)
    assert report.sample_count == 4
    assert "zeta" in report.falling_alerts
