from __future__ import annotations

import pytest

from pathwise.core.store import FileStore


class TestSharding:
    def test_user_dir_layout(self, store: FileStore) -> None:
        uid = "abcdef0123456789abcdef0123456789"
        d = store.user_dir(uid)
        assert d.parts[-3:] == ("ab", "cd", uid)
        assert d.is_relative_to(store.base)

    def test_short_id_rejected(self, store: FileStore) -> None:
        with pytest.raises(ValueError):
            store.user_dir("abc")


class TestJsonRoundtrip:
    def test_write_read(self, store: FileStore) -> None:
        uid = "abcdef0123456789abcdef0123456789"
        path = store.profile_path(uid)
        store.write_json(path, {"first_name": "Emma", "gender": "female"})
        assert store.read_json(path) == {"first_name": "Emma", "gender": "female"}

    def test_write_atomic_no_tmp_left(self, store: FileStore) -> None:
        uid = "abcdef0123456789abcdef0123456789"
        path = store.profile_path(uid)
        store.write_json(path, {"x": 1})
        siblings = list(path.parent.iterdir())
        assert all(not p.name.endswith(".tmp") for p in siblings)

    def test_overwrite(self, store: FileStore) -> None:
        uid = "abcdef0123456789abcdef0123456789"
        path = store.profile_path(uid)
        store.write_json(path, {"v": 1})
        store.write_json(path, {"v": 2})
        assert store.read_json(path) == {"v": 2}

    def test_read_missing_returns_empty(self, store: FileStore) -> None:
        uid = "abcdef0123456789abcdef0123456789"
        assert store.read_json(store.profile_path(uid)) == {}


class TestJsonl:
    def test_append_and_read(self, store: FileStore) -> None:
        uid = "abcdef0123456789abcdef0123456789"
        path = store.events_path(uid)
        store.append_jsonl(path, {"event": "created"})
        store.append_jsonl(path, {"event": "answered", "key": "car_use"})
        records = store.read_jsonl(path)
        assert len(records) == 2
        assert records[0]["event"] == "created"
        assert records[1]["key"] == "car_use"

    def test_read_missing_returns_empty(self, store: FileStore) -> None:
        uid = "abcdef0123456789abcdef0123456789"
        assert store.read_jsonl(store.events_path(uid)) == []


class TestPlanVersions:
    def test_no_plans_yet(self, store: FileStore) -> None:
        uid = "abcdef0123456789abcdef0123456789"
        assert store.list_plan_versions(uid, "tta") == []
        assert store.next_plan_version(uid, "tta") == 1

    def test_versioning_sequence(self, store: FileStore) -> None:
        uid = "abcdef0123456789abcdef0123456789"
        for v in [1, 2, 3]:
            store.write_text(store.plan_path(uid, "tta", v), f"# Plan v{v}\n")
        assert store.list_plan_versions(uid, "tta") == [1, 2, 3]
        assert store.next_plan_version(uid, "tta") == 4

    def test_ignores_non_plan_files(self, store: FileStore) -> None:
        uid = "abcdef0123456789abcdef0123456789"
        store.write_text(store.plan_path(uid, "tta", 1), "# v1\n")
        store.write_text(store.plans_dir(uid, "tta") / "notes.txt", "ignore me")
        assert store.list_plan_versions(uid, "tta") == [1]


class TestUserExists:
    def test_false_when_no_profile(self, store: FileStore) -> None:
        uid = "abcdef0123456789abcdef0123456789"
        assert store.user_exists(uid) is False

    def test_true_after_profile_written(self, store: FileStore) -> None:
        uid = "abcdef0123456789abcdef0123456789"
        store.write_json(store.profile_path(uid), {"first_name": "Emma"})
        assert store.user_exists(uid) is True
