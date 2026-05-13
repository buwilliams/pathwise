from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pathwise.api import deps
from pathwise.api.app import create_app
from pathwise.config import Settings
from pathwise.core.auth import AuthService
from pathwise.core.profile import ProfileService
from pathwise.core.store import FileStore
from pathwise.verify.console_verifier import ConsoleVerifier

PHONE = "+12025550100"
SEASON = "build-independence"


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
    return TestClient(app), verifier


def _sign_in(api, verifier) -> str:
    api.post("/auth/start", json={"phone": PHONE})
    code = verifier.sent[-1][1]
    body = api.post("/auth/verify", json={"phone": PHONE, "code": code}).json()
    return body["session_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_record_list_and_drift_round_trip(client) -> None:
    api, verifier = client
    token = _sign_in(api, verifier)

    # Empty list to start
    r = api.get(f"/seasons/{SEASON}/checkins", headers=_auth(token))
    assert r.status_code == 200
    assert r.json() == {"checkins": [], "total": 0}

    # Record a check-in
    r = api.post(
        f"/seasons/{SEASON}/checkins",
        json={"b": 12, "eta": 1, "note": "ok week"},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["observations"] == {"b": 12.0, "eta": 1.0}
    assert body["note"] == "ok week"

    # Drift report (only one sample → direction unknown)
    r = api.get(f"/seasons/{SEASON}/checkins/drift", headers=_auth(token))
    assert r.status_code == 200
    drift = r.json()
    assert drift["sample_count"] == 1
    assert drift["components"]["b"]["direction"] == "unknown"
    assert drift["falling_alerts"] == []


def test_record_rejects_empty_payload(client) -> None:
    api, verifier = client
    token = _sign_in(api, verifier)
    r = api.post(f"/seasons/{SEASON}/checkins", json={}, headers=_auth(token))
    assert r.status_code == 400


def test_drift_flags_falling_streak(client) -> None:
    api, verifier = client
    token = _sign_in(api, verifier)
    for v in (5, 4, 3, 2):
        r = api.post(
            f"/seasons/{SEASON}/checkins",
            json={"zeta": v},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text

    r = api.get(f"/seasons/{SEASON}/checkins/drift", headers=_auth(token))
    body = r.json()
    assert body["sample_count"] == 4
    assert "zeta" in body["falling_alerts"]
    assert body["components"]["zeta"]["direction"] == "falling"
    assert body["components"]["zeta"]["falling_streak"] == 3


def test_checkins_require_auth(client) -> None:
    api, _ = client
    assert api.get(f"/seasons/{SEASON}/checkins").status_code == 401
    assert (
        api.post(f"/seasons/{SEASON}/checkins", json={"q": 4}).status_code == 401
    )
    assert (
        api.get(f"/seasons/{SEASON}/checkins/drift").status_code == 401
    )


def test_out_of_range_rejected(client) -> None:
    api, verifier = client
    token = _sign_in(api, verifier)
    r = api.post(
        f"/seasons/{SEASON}/checkins", json={"eta": 9}, headers=_auth(token)
    )
    assert r.status_code == 422  # pydantic-level range check
