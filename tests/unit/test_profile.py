from __future__ import annotations

import pytest

from pathwise.core.ids import user_id_for_phone
from pathwise.core.profile import ProfileService
from pathwise.core.store import FileStore


@pytest.fixture
def profiles(store: FileStore) -> ProfileService:
    return ProfileService(store)


PHONE = "+12025550100"


def test_create_and_fetch(profiles: ProfileService) -> None:
    p = profiles.create(
        phone_e164=PHONE,
        first_name="  Emma  ",
        gender="female",
        zip_code="30301",
    )
    assert p.first_name == "Emma"
    assert p.gender == "female"
    assert p.zip_code == "30301"
    fetched = profiles.get(user_id_for_phone(PHONE))
    assert fetched == p


def test_create_twice_rejected(profiles: ProfileService) -> None:
    profiles.create(phone_e164=PHONE, first_name="Emma", gender="female")
    with pytest.raises(ValueError):
        profiles.create(phone_e164=PHONE, first_name="Emma", gender="female")


def test_update_changes_only_provided_fields(profiles: ProfileService) -> None:
    p = profiles.create(
        phone_e164=PHONE, first_name="Emma", gender="female", zip_code="30301"
    )
    updated = profiles.update(p.user_id, zip_code="30302")
    assert updated.zip_code == "30302"
    assert updated.first_name == "Emma"
    assert updated.gender == "female"


def test_update_unknown_user(profiles: ProfileService) -> None:
    with pytest.raises(ValueError):
        profiles.update("0" * 32, first_name="X")
