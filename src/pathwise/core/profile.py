from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Literal

from pathwise.core.ids import user_id_for_phone
from pathwise.core.store import FileStore

Gender = Literal["male", "female", "non-binary"]


@dataclass
class Profile:
    user_id: str
    first_name: str
    gender: Gender
    phone_e164: str
    zip_code: str | None
    created_at: float
    updated_at: float


class ProfileService:
    def __init__(self, store: FileStore) -> None:
        self.store = store

    def create(
        self,
        *,
        phone_e164: str,
        first_name: str,
        gender: Gender,
        zip_code: str | None = None,
        now: float | None = None,
    ) -> Profile:
        now = now if now is not None else time.time()
        user_id = user_id_for_phone(phone_e164)
        if self.store.user_exists(user_id):
            raise ValueError(f"Profile already exists for this phone.")
        profile = Profile(
            user_id=user_id,
            first_name=first_name.strip(),
            gender=gender,
            phone_e164=phone_e164,
            zip_code=zip_code.strip() if zip_code else None,
            created_at=now,
            updated_at=now,
        )
        self.store.write_json(self.store.profile_path(user_id), asdict(profile))
        self.store.append_jsonl(
            self.store.events_path(user_id),
            {"event": "profile.created", "at": now},
        )
        return profile

    def get(self, user_id: str) -> Profile | None:
        data = self.store.read_json(self.store.profile_path(user_id))
        if not data:
            return None
        return Profile(**data)

    def update(
        self,
        user_id: str,
        *,
        first_name: str | None = None,
        gender: Gender | None = None,
        zip_code: str | None = None,
        now: float | None = None,
    ) -> Profile:
        now = now if now is not None else time.time()
        existing = self.get(user_id)
        if existing is None:
            raise ValueError(f"No profile for user_id={user_id}")
        if first_name is not None:
            existing.first_name = first_name.strip()
        if gender is not None:
            existing.gender = gender
        if zip_code is not None:
            existing.zip_code = zip_code.strip() or None
        existing.updated_at = now
        self.store.write_json(self.store.profile_path(user_id), asdict(existing))
        self.store.append_jsonl(
            self.store.events_path(user_id),
            {"event": "profile.updated", "at": now},
        )
        return existing

    def delete(self, user_id: str) -> None:
        self.store.delete_user(user_id)
