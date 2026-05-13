from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from pathwise.api import deps
from pathwise.api.app import create_app
from pathwise.config import Settings
from pathwise.core.auth import AuthService
from pathwise.core.ids import user_id_for_phone
from pathwise.core.profile import ProfileService
from pathwise.core.questionnaire import QuestionnaireService
from pathwise.core.season import get_pack
from pathwise.core.store import FileStore
from pathwise.verify.console_verifier import ConsoleVerifier

PHONE = "+12025550100"
SEASON = "build-independence"


def _full_answers() -> dict[str, object]:
    """Same fixture the plan-pipeline integration test uses."""
    return {
        "wants_mobility": ["car"],
        "wants_housing": ["move_out"],
        "wants_education": ["trade_school"],
        "wants_work": ["full_time_job"],
        "wants_relationships": ["deepen_friendships"],
        "wants_place": ["stay_where_i_am"],
        "wants_health": ["fitness_practice"],
        "wants_money_goals": ["emergency_fund"],
        "wants_lifestyle": [],
        "current_savings": "10000",
        "current_monthly_take_home": "1800",
        "current_monthly_bills": "250",
        "current_debt": "0",
        "lives_with_parents": "yes",
        "has_car": "no",
        "emergency_fund_floor": "3000",
        "monthly_pressure_comfort": "mild",
        "productive_hours_per_week": "18",
        "buffer_hours_per_week": "10",
        "quality_of_time_now": "4",
        "physical_health_self": "4",
        "mental_health_self": "4",
        "fitness_practice_freq": "weekly",
        "emotional_state_now": "neutral",
        "relational_quality_now": "okay",
        "current_job_feeling": "ok",
        "hours_preference": "more",
        "move_out_urgency": "3",
        "move_out_horizon": "1yr",
        "top_value": "independence",
        "stability_now": "3",
        "social_satisfaction": "3",
    }


@pytest.fixture
def client(tmp_path: Path):
    settings = Settings(pathwise_data_dir=tmp_path)
    settings.users_dir.mkdir(parents=True, exist_ok=True)
    settings.otp_dir.mkdir(parents=True, exist_ok=True)
    settings.sessions_dir.mkdir(parents=True, exist_ok=True)
    store = FileStore(settings.users_dir)
    verifier = ConsoleVerifier(
        store=store,
        otp_dir=settings.otp_dir,
        ttl_seconds=settings.pathwise_otp_ttl_seconds,
        max_attempts=settings.pathwise_otp_max_verify_attempts,
    )
    auth = AuthService(store, settings, verifier)
    profiles = ProfileService(store)
    app = create_app()
    app.dependency_overrides[deps.get_settings] = lambda: settings
    app.dependency_overrides[deps.get_store] = lambda: store
    app.dependency_overrides[deps.get_auth_service] = lambda: auth
    app.dependency_overrides[deps.get_profile_service] = lambda: profiles
    return TestClient(app), verifier, store


def _sign_in_and_onboard(client, verifier, store):
    client.post("/auth/start", json={"phone": PHONE})
    code = verifier.sent[-1][1]
    body = client.post("/auth/verify", json={"phone": PHONE, "code": code}).json()
    token = body["session_token"]
    # Onboard via API to create a profile
    client.post(
        "/me/onboard",
        json={"phone": PHONE, "first_name": "Emma", "gender": "female", "zip_code": "30301"},
        headers={"Authorization": f"Bearer {token}"},
    )
    # Fill in questionnaire
    user_id = user_id_for_phone(PHONE)
    pack = get_pack(SEASON)
    QuestionnaireService(store).set_answers(user_id, pack, _full_answers())
    return token


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_sandbox_get_returns_baseline_and_first_simulation(client) -> None:
    api, verifier, store = client
    token = _sign_in_and_onboard(api, verifier, store)

    r = api.get(f"/seasons/{SEASON}/sandbox", headers=_auth(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["season_id"] == SEASON
    assert body["horizon_months"] > 0
    assert "baseline" in body
    assert "paths_meta" in body and len(body["paths_meta"]) > 0
    assert "config" in body
    assert "result" in body
    result = body["result"]
    assert len(result["paths"]) == len(body["paths_meta"])
    # Every path view carries the keys the UI binds to.
    for view in result["paths"]:
        assert "path_momentum" in view
        assert "min_recoverability" in view
        assert "viable" in view
        assert "stages" in view
        assert "on_pareto_frontier" in view


def test_sandbox_simulate_applies_overrides(client) -> None:
    api, verifier, store = client
    token = _sign_in_and_onboard(api, verifier, store)

    # Baseline
    base = api.get(f"/seasons/{SEASON}/sandbox", headers=_auth(token)).json()
    base_paths = {p["id"]: p for p in base["result"]["paths"]}

    # Override rent to a stress-test value; expect at least one move-out path
    # to flip viability vs baseline.
    override = {
        "paths": base["config"]["paths"],
        "globals": {**base["config"]["globals"], "rent_monthly": 4000},
        "monte_carlo": {"samples": 0},
    }
    r = api.post(
        f"/seasons/{SEASON}/sandbox/simulate",
        json={"config": override},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    sim_paths = {p["id"]: p for p in r.json()["result"]["paths"]}
    flipped = [
        pid for pid, view in sim_paths.items()
        if base_paths[pid]["viable"] and not view["viable"]
    ]
    assert flipped, "expensive rent should flip at least one path"


def test_sandbox_simulate_runs_monte_carlo(client) -> None:
    api, verifier, store = client
    token = _sign_in_and_onboard(api, verifier, store)
    base = api.get(f"/seasons/{SEASON}/sandbox", headers=_auth(token)).json()

    config = {
        **base["config"],
        "monte_carlo": {
            "samples": 32,
            "rho_jitter": 0.2,
            "delta_jitter": 0.05,
            "rent_jitter": 0.2,
            "car_jitter": 0.1,
            "seed": 1,
        },
    }
    r = api.post(
        f"/seasons/{SEASON}/sandbox/simulate",
        json={"config": config},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    paths = r.json()["result"]["paths"]
    enabled = [p for p in paths if p["enabled"]]
    assert enabled
    for p in enabled:
        assert p["monte_carlo"] is not None
        mc = p["monte_carlo"]
        assert mc["samples"] == 32
        assert mc["momentum_p10"] <= mc["momentum_p50"] <= mc["momentum_p90"]
        assert 0.0 <= mc["viable_prob"] <= 1.0


def test_sandbox_narrate_calls_llm_with_grounded_result(client) -> None:
    api, verifier, store = client
    token = _sign_in_and_onboard(api, verifier, store)
    base = api.get(f"/seasons/{SEASON}/sandbox", headers=_auth(token)).json()

    from pathwise.llm.client import LlmCallResult

    captured: dict[str, object] = {}

    def fake_call(*, system_prompt, messages, model, max_tokens):
        captured["system_prompt"] = system_prompt
        captured["user_prompt"] = messages[-1]["content"]
        return LlmCallResult(
            text="You just stress-tested the rent. The move_out_with_car path went red on cash flow.",
            sources=[],
            usage={"input_tokens": 1, "output_tokens": 1},
        )

    with patch("pathwise.llm.narrate.call_chat", side_effect=fake_call):
        r = api.post(
            f"/seasons/{SEASON}/sandbox/narrate",
            json={
                "config": {
                    **base["config"],
                    "globals": {**base["config"]["globals"], "rent_monthly": 3500},
                },
                "focus": "what happened when I cranked up rent?",
            },
            headers=_auth(token),
        )
    assert r.status_code == 200, r.text
    assert "went red" in r.json()["narration"]
    # The narrator must have been handed the simulation result (the math),
    # not asked to invent. Verify the user_prompt contains the path JSON.
    assert "paths" in captured["user_prompt"]
    assert "Sandbox mode" in captured["system_prompt"]


def test_sandbox_requires_completed_questionnaire(client) -> None:
    api, verifier, store = client
    # Sign in but skip the questionnaire
    api.post("/auth/start", json={"phone": PHONE})
    code = verifier.sent[-1][1]
    body = api.post("/auth/verify", json={"phone": PHONE, "code": code}).json()
    token = body["session_token"]
    api.post(
        "/me/onboard",
        json={"phone": PHONE, "first_name": "Emma", "gender": "female", "zip_code": "30301"},
        headers=_auth(token),
    )
    r = api.get(f"/seasons/{SEASON}/sandbox", headers=_auth(token))
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert detail["code"] == "questionnaire_incomplete"
