from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from pathwise.config import Settings
from pathwise.core.plan import PlanError, generate_plan, list_plans, read_plan
from pathwise.core.profile import ProfileService
from pathwise.core.questionnaire import QuestionnaireService
from pathwise.core.season import get_pack
from pathwise.core.store import FileStore
from pathwise.llm.client import LlmCallResult


PHONE = "+12025550100"


@pytest.fixture
def setup(tmp_path: Path):
    settings = Settings(pathwise_data_dir=tmp_path, anthropic_api_key="dummy")
    settings.users_dir.mkdir(parents=True, exist_ok=True)
    store = FileStore(settings.users_dir)
    profile = ProfileService(store).create(
        phone_e164=PHONE,
        first_name="Emma",
        gender="female",
        zip_code="30301",
    )
    pack = get_pack("build-independence")
    qs = QuestionnaireService(store)
    # Fill every required key with a sensible value (v0_5_0 schema).
    answers = {
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
    qs.set_answers(profile.user_id, pack, answers)
    return settings, store, profile


def test_generate_plan_with_mocked_llm(setup) -> None:
    settings, store, profile = setup
    fake_plan_text = "# Your plan, Emma\n\nHere is the plan.\n"

    with patch("pathwise.core.plan.call_plain") as mock_call:
        mock_call.return_value = LlmCallResult(
            text=fake_plan_text,
            sources=[],
            usage={"input_tokens": 100, "output_tokens": 50},
        )
        result = generate_plan(
            user_id=profile.user_id,
            season_id="build-independence",
            store=store,
            settings=settings,
            skip_research=True,
        )

    assert result.version == 1
    assert "Emma" in result.markdown
    assert Path(result.plan_path).exists()
    assert Path(result.meta_path).exists()

    # Versioning works
    with patch("pathwise.core.plan.call_plain") as mock_call:
        mock_call.return_value = LlmCallResult(
            text="# v2\n", sources=[], usage={"input_tokens": 10, "output_tokens": 5}
        )
        r2 = generate_plan(
            user_id=profile.user_id,
            season_id="build-independence",
            store=store,
            settings=settings,
            skip_research=True,
        )
    assert r2.version == 2
    assert list_plans(profile.user_id, "build-independence", store) == [1, 2]


def test_meta_records_scenarios_and_life_state(setup) -> None:
    settings, store, profile = setup
    with patch("pathwise.core.plan.call_plain") as mock_call:
        mock_call.return_value = LlmCallResult(
            text="# plan\n", sources=[], usage={"input_tokens": 1, "output_tokens": 1}
        )
        generate_plan(
            user_id=profile.user_id,
            season_id="build-independence",
            store=store,
            settings=settings,
            skip_research=True,
        )
    text, meta = read_plan(profile.user_id, "build-independence", 1, store)
    assert text == "# plan\n"
    assert meta["model_plan"] == "claude-opus-4-7"
    # v0_5_0 life-state is grouped by L's five top-level dimensions.
    assert meta["life_state"]["A"]["c"] == 1550
    # Each scored item is a path-of-stages.
    assert meta["scored_scenarios"]
    first = meta["scored_scenarios"][0]
    assert "stages" in first and len(first["stages"]) >= 1
    ids = [r["id"] for r in meta["scored_scenarios"]]
    assert "trade_school_direct" in ids


def test_incomplete_questionnaire_rejected(setup) -> None:
    settings, store, profile = setup
    # Wipe required answers
    store.write_json(store.answers_path(profile.user_id, "build-independence"), {})

    with pytest.raises(PlanError) as exc_info:
        generate_plan(
            user_id=profile.user_id,
            season_id="build-independence",
            store=store,
            settings=settings,
            skip_research=True,
        )
    assert "incomplete" in str(exc_info.value).lower()


def test_plans_index_endpoint_returns_enriched_versions(setup, tmp_path) -> None:
    """The /seasons/{id}/plans endpoint should return version + generated_at +
    model_plan for each version, not just the bare version numbers."""
    settings, store, profile = setup
    from fastapi.testclient import TestClient

    from pathwise.api import deps
    from pathwise.api.app import create_app
    from pathwise.core.auth import AuthService
    from pathwise.core.profile import ProfileService
    from pathwise.verify.console_verifier import ConsoleVerifier

    verifier = ConsoleVerifier(
        store=store,
        otp_dir=settings.otp_dir,
        ttl_seconds=settings.pathwise_otp_ttl_seconds,
        max_attempts=settings.pathwise_otp_max_verify_attempts,
    )
    auth = AuthService(store, settings, verifier)

    # Generate two plan versions
    for _ in range(2):
        with patch("pathwise.core.plan.call_plain") as mock_call:
            mock_call.return_value = LlmCallResult(
                text="# plan\n", sources=[], usage={}
            )
            generate_plan(
                user_id=profile.user_id,
                season_id="build-independence",
                store=store,
                settings=settings,
                skip_research=True,
            )

    app = create_app()
    app.dependency_overrides[deps.get_settings] = lambda: settings
    app.dependency_overrides[deps.get_store] = lambda: store
    app.dependency_overrides[deps.get_auth_service] = lambda: auth
    app.dependency_overrides[deps.get_profile_service] = lambda: ProfileService(store)
    client = TestClient(app)

    # Sign in as the profile holder
    client.post("/auth/start", json={"phone": PHONE})
    code = verifier.sent[-1][1]
    token = client.post("/auth/verify", json={"phone": PHONE, "code": code}).json()[
        "session_token"
    ]

    r = client.get(
        "/seasons/build-independence/plans",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    versions = r.json()["versions"]
    assert len(versions) == 2
    assert versions[0]["version"] == 1
    assert versions[1]["version"] == 2
    assert versions[0]["generated_at"]  # populated
    assert versions[0]["model_plan"] == "claude-opus-4-7"


def test_plan_prompt_renders_with_full_context(setup) -> None:
    """Smoke test: the plan template renders without missing-context errors."""
    settings, store, profile = setup
    captured: dict = {}

    def fake_call(*, system_prompt, user_prompt, model, max_tokens=16000):
        captured["system"] = system_prompt
        captured["user"] = user_prompt
        return LlmCallResult(
            text="# ok\n", sources=[], usage={"input_tokens": 0, "output_tokens": 0}
        )

    with patch("pathwise.core.plan.call_plain", side_effect=fake_call):
        generate_plan(
            user_id=profile.user_id,
            season_id="build-independence",
            store=store,
            settings=settings,
            skip_research=True,
        )

    # System prompt is the season pack's system.md
    assert "wise older friend" in captured["system"]
    # Plan prompt addresses the user by name and mentions one of v0_5_0's paths.
    assert "Emma" in captured["user"]
    assert "trade_school_direct" in captured["user"] or \
        "Trade school" in captured["user"]
