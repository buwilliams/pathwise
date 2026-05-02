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
from pathwise.sms.console_sender import ConsoleSmsSender


@pytest.fixture
def client(tmp_path: Path):
    settings = Settings(pathwise_data_dir=tmp_path)
    settings.users_dir.mkdir(parents=True, exist_ok=True)
    settings.otp_dir.mkdir(parents=True, exist_ok=True)
    settings.sessions_dir.mkdir(parents=True, exist_ok=True)
    store = FileStore(settings.users_dir)
    sender = ConsoleSmsSender()
    auth = AuthService(store, settings, sender)
    profiles = ProfileService(store)

    app = create_app()
    app.dependency_overrides[deps.get_settings] = lambda: settings
    app.dependency_overrides[deps.get_store] = lambda: store
    app.dependency_overrides[deps.get_auth_service] = lambda: auth
    app.dependency_overrides[deps.get_profile_service] = lambda: profiles
    return TestClient(app), sender


PHONE = "+12025550100"


def _last_code(sender: ConsoleSmsSender) -> str:
    return sender.sent[-1][1].split("code is ")[1].split(".")[0]


def test_full_auth_then_onboard_flow(client) -> None:
    api, sender = client
    r = api.post("/auth/start", json={"phone": PHONE})
    assert r.status_code == 200, r.text
    assert r.json() == {"sent": True}

    code = _last_code(sender)
    r = api.post("/auth/verify", json={"phone": PHONE, "code": code})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["needs_onboarding"] is True
    token = body["session_token"]

    r = api.post(
        "/me/onboard",
        json={
            "phone": PHONE,
            "first_name": "Emma",
            "gender": "female",
            "zip_code": "30301",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["first_name"] == "Emma"

    r = api.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["zip_code"] == "30301"


def test_invalid_phone_rejected(client) -> None:
    api, _ = client
    r = api.post("/auth/start", json={"phone": "not-a-number"})
    assert r.status_code == 400


def test_no_token_rejected(client) -> None:
    api, _ = client
    r = api.get("/me")
    assert r.status_code == 401


def test_bad_token_rejected(client) -> None:
    api, _ = client
    r = api.get("/me", headers={"Authorization": "Bearer nonsense"})
    assert r.status_code == 401
