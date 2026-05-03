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
    # Fill every required key with a sensible value
    answers = {
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
    assert meta["life_state"]["cash_flow_monthly"] == 1550
    assert len(meta["scored_scenarios"]) == 7
    # All 7 scenarios from Emma's model are scored and ranked
    ids = [s["id"] for s in meta["scored_scenarios"]]
    assert "low_rent_modest_car_grow_income" in ids


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
    from pathwise.sms.console_sender import ConsoleSmsSender

    sender = ConsoleSmsSender()
    auth = AuthService(store, settings, sender)

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
    code = sender.sent[-1][1].split("code is ")[1].split(".")[0]
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
    # Plan prompt addresses Emma by name and mentions specific scenarios
    assert "Emma" in captured["user"]
    assert "low_rent_modest_car_grow_income" in captured["user"] or \
        "Stay low-rent, modest car" in captured["user"]
