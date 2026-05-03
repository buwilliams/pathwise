"""Tests for the async plan-generation job machinery (start_plan_job +
plan_job_status). Real threading; LLM calls are mocked."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

import pytest

from pathwise.config import Settings
from pathwise.core.plan import (
    PlanJobAlreadyRunning,
    plan_job_status,
    start_plan_job,
)
from pathwise.core.profile import ProfileService
from pathwise.core.questionnaire import QuestionnaireService
from pathwise.core.season import get_pack
from pathwise.core.store import FileStore
from pathwise.llm.client import LlmCallResult
from pathwise.llm.research import ResearchBundle


def _empty_bundle() -> ResearchBundle:
    return ResearchBundle(data={}, sources=[], raw_text="", usage={})


PHONE = "+12025550100"
SEASON = "build-independence"


@pytest.fixture
def setup(tmp_path: Path):
    settings = Settings(pathwise_data_dir=tmp_path, anthropic_api_key="dummy")
    settings.users_dir.mkdir(parents=True, exist_ok=True)
    store = FileStore(settings.users_dir)
    profile = ProfileService(store).create(
        phone_e164=PHONE, first_name="Emma", gender="female", zip_code="30301",
    )
    pack = get_pack(SEASON)
    qs = QuestionnaireService(store)
    qs.set_answers(profile.user_id, pack, {
        "current_savings": "10000",
        "current_monthly_take_home": "1800",
        "current_monthly_bills": "250",
        "lives_with_parents": "yes",
        "has_car": "no",
        "emergency_fund_floor": "3000",
        "monthly_pressure_comfort": "mild",
        "current_job_feeling": "ok",
        "hours_preference": "more",
        "interested_in_training": "yes",
        "move_out_urgency": "4",
        "move_out_horizon": "1yr",
        "productive_hours_per_week": "18",
        "quality_of_time_now": "4",
        "top_value": "independence",
    })
    return settings, store, profile


def _wait_until_done(store, user_id, season_id, timeout=10.0):
    """Spin until the lock file is gone, indicating the worker thread finished."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not store.plan_job_lock_path(user_id, season_id).exists():
            return
        time.sleep(0.05)
    raise AssertionError(f"plan job did not finish within {timeout}s")


def test_start_plan_job_returns_immediately_and_completes(setup) -> None:
    settings, store, profile = setup

    with patch("pathwise.core.plan.call_plain") as mock_call:
        mock_call.return_value = LlmCallResult(
            text="# v1\n", sources=[], usage={"input_tokens": 1, "output_tokens": 1}
        )
        # Skip the LLM research call too
        with patch("pathwise.core.plan.run_research", return_value=_empty_bundle()):
            t = time.time()
            res = start_plan_job(
                user_id=profile.user_id, season_id=SEASON, store=store,
                settings=Settings(pathwise_data_dir=settings.pathwise_data_dir,
                                  anthropic_api_key="dummy"),
            )
            assert time.time() - t < 1.0  # returns immediately
            assert res["started_at"] > 0
            assert res["from_chat"] is False
            # Lock should exist while running (race-tight, but the lock is
            # written synchronously before the thread starts).
            _wait_until_done(store, profile.user_id, SEASON)

    # Plan v1 written; lock removed; success record in jobs log.
    assert store.list_plan_versions(profile.user_id, SEASON) == [1]
    assert not store.plan_job_lock_path(profile.user_id, SEASON).exists()
    history = store.read_jsonl(store.plan_jobs_log_path(profile.user_id, SEASON))
    assert len(history) == 1
    assert history[0]["status"] == "succeeded"
    assert history[0]["version"] == 1


def test_concurrent_start_raises_already_running(setup) -> None:
    settings, store, profile = setup

    # Slow down the LLM call so we can observe the lock window
    def slow_call(**_):
        time.sleep(0.5)
        return LlmCallResult(text="# slow\n", sources=[], usage={})

    with patch("pathwise.core.plan.call_plain", side_effect=slow_call), \
         patch("pathwise.core.plan.run_research", return_value=_empty_bundle()):
        start_plan_job(user_id=profile.user_id, season_id=SEASON, store=store,
                       settings=settings)
        with pytest.raises(PlanJobAlreadyRunning):
            start_plan_job(user_id=profile.user_id, season_id=SEASON, store=store,
                           settings=settings)
        _wait_until_done(store, profile.user_id, SEASON)


def test_status_reflects_running_then_done(setup) -> None:
    settings, store, profile = setup

    def slow_call(**_):
        time.sleep(0.3)
        return LlmCallResult(text="# done\n", sources=[], usage={})

    with patch("pathwise.core.plan.call_plain", side_effect=slow_call), \
         patch("pathwise.core.plan.run_research", return_value=_empty_bundle()):
        start_plan_job(user_id=profile.user_id, season_id=SEASON, store=store,
                       settings=settings)
        # While running
        s1 = plan_job_status(profile.user_id, SEASON, store)
        assert s1["generating"] is True
        assert s1["started_at"] > 0
        assert s1["last_error"] is None
        _wait_until_done(store, profile.user_id, SEASON)

    s2 = plan_job_status(profile.user_id, SEASON, store)
    assert s2["generating"] is False
    assert s2["latest_version"] == 1
    assert s2["last_error"] is None


def test_failure_records_error_and_clears_lock(setup) -> None:
    settings, store, profile = setup

    with patch("pathwise.core.plan.call_plain", side_effect=RuntimeError("boom")), \
         patch("pathwise.core.plan.run_research", return_value=_empty_bundle()):
        start_plan_job(user_id=profile.user_id, season_id=SEASON, store=store,
                       settings=settings)
        _wait_until_done(store, profile.user_id, SEASON)

    assert not store.plan_job_lock_path(profile.user_id, SEASON).exists()
    s = plan_job_status(profile.user_id, SEASON, store)
    assert s["generating"] is False
    assert s["last_error"] == "boom"
    assert store.list_plan_versions(profile.user_id, SEASON) == []  # nothing written


def test_stale_lock_is_cleaned_up_on_status_check(setup) -> None:
    """A lock file older than STALE_LOCK_AGE_SECONDS must be treated as a
    crashed job — cleared on read so a fresh job can start."""
    settings, store, profile = setup
    lock_path = store.plan_job_lock_path(profile.user_id, SEASON)
    # Write a stale lock by hand (started ages ago)
    store.write_json(lock_path, {"started_at": time.time() - 9999, "season_id": SEASON})

    s = plan_job_status(profile.user_id, SEASON, store)
    assert s["generating"] is False
    assert s["last_error"] is not None and "stale" in s["last_error"].lower()
    assert not lock_path.exists()  # cleaned up

    # And a new job can now start
    with patch("pathwise.core.plan.call_plain") as mock_call:
        mock_call.return_value = LlmCallResult(text="# fresh\n", sources=[], usage={})
        with patch("pathwise.core.plan.run_research", return_value=_empty_bundle()):
            start_plan_job(user_id=profile.user_id, season_id=SEASON, store=store,
                           settings=settings)
            _wait_until_done(store, profile.user_id, SEASON)
    assert store.list_plan_versions(profile.user_id, SEASON) == [1]


def test_chat_context_recorded_in_job(setup) -> None:
    settings, store, profile = setup
    with patch("pathwise.core.plan.call_plain") as mock_call:
        mock_call.return_value = LlmCallResult(text="# from chat\n", sources=[], usage={})
        with patch("pathwise.core.plan.run_research", return_value=_empty_bundle()):
            res = start_plan_job(
                user_id=profile.user_id, season_id=SEASON, store=store,
                settings=settings, chat_context="**Buddy:** can we move out sooner?",
            )
            assert res["from_chat"] is True
            _wait_until_done(store, profile.user_id, SEASON)

    history = store.read_jsonl(store.plan_jobs_log_path(profile.user_id, SEASON))
    assert history[-1]["status"] == "succeeded"
    assert history[-1]["from_chat"] is True
