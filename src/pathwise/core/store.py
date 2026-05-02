from __future__ import annotations

import fcntl
import json
import os
import shutil
from pathlib import Path
from typing import Any


class FileStore:
    """Single gateway for all flat-file persistence.

    Users are sharded git-style under a base directory:
        {base}/{user_id[0:2]}/{user_id[2:4]}/{user_id}/

    All writes are atomic (write-temp-then-rename) and locked with fcntl
    so concurrent processes (web + CLI + cron) cannot corrupt files.
    """

    def __init__(self, base: Path) -> None:
        self.base = base

    def user_dir(self, user_id: str) -> Path:
        if len(user_id) < 4:
            raise ValueError(f"user_id must be at least 4 characters, got: {user_id!r}")
        return self.base / user_id[0:2] / user_id[2:4] / user_id

    def user_exists(self, user_id: str) -> bool:
        return (self.user_dir(user_id) / "profile.json").exists()

    def append_jsonl(self, path: Path, record: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                f.write(json.dumps(record) + "\n")
                f.flush()
                os.fsync(f.fileno())
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    def write_json(self, path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                json.dump(data, f, indent=2, sort_keys=True)
                f.flush()
                os.fsync(f.fileno())
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
        tmp.replace(path)

    def read_json(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        with open(path) as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            try:
                return json.load(f)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    def read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        records: list[dict[str, Any]] = []
        with open(path) as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            try:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
        return records

    def write_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                f.write(text)
                f.flush()
                os.fsync(f.fileno())
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
        tmp.replace(path)

    def read_text(self, path: Path) -> str:
        if not path.exists():
            return ""
        with open(path) as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            try:
                return f.read()
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    def delete_user(self, user_id: str) -> None:
        d = self.user_dir(user_id)
        if d.exists():
            shutil.rmtree(d)

    # ------------------------------------------------------------------
    # Path builders
    # ------------------------------------------------------------------

    def profile_path(self, user_id: str) -> Path:
        return self.user_dir(user_id) / "profile.json"

    def events_path(self, user_id: str) -> Path:
        return self.user_dir(user_id) / "events.jsonl"

    def season_dir(self, user_id: str, season_id: str) -> Path:
        return self.user_dir(user_id) / "seasons" / season_id

    def answers_path(self, user_id: str, season_id: str) -> Path:
        return self.season_dir(user_id, season_id) / "answers.json"

    def answers_history_path(self, user_id: str, season_id: str) -> Path:
        return self.season_dir(user_id, season_id) / "answers.history.jsonl"

    def research_dir(self, user_id: str, season_id: str) -> Path:
        return self.season_dir(user_id, season_id) / "research"

    def plans_dir(self, user_id: str, season_id: str) -> Path:
        return self.season_dir(user_id, season_id) / "plans"

    def plan_path(self, user_id: str, season_id: str, version: int) -> Path:
        return self.plans_dir(user_id, season_id) / f"plan_v{version}.md"

    def plan_meta_path(self, user_id: str, season_id: str, version: int) -> Path:
        return self.plans_dir(user_id, season_id) / f"plan_v{version}.meta.json"

    def chat_history_path(self, user_id: str, season_id: str, version: int) -> Path:
        return self.plans_dir(user_id, season_id) / f"plan_v{version}.chat.jsonl"

    def plan_job_lock_path(self, user_id: str, season_id: str) -> Path:
        """Lock file written when a plan-generation job is in flight.

        Removed on completion (success or failure). Stale locks (older than
        STALE_LOCK_AGE_SECONDS) are treated as crashed jobs and cleaned up.
        """
        return self.season_dir(user_id, season_id) / ".plan_job.json"

    def plan_jobs_log_path(self, user_id: str, season_id: str) -> Path:
        """Append-only log of plan-generation job outcomes (success + failure)."""
        return self.season_dir(user_id, season_id) / "plan_jobs.jsonl"

    def list_plan_versions(self, user_id: str, season_id: str) -> list[int]:
        d = self.plans_dir(user_id, season_id)
        if not d.exists():
            return []
        versions: list[int] = []
        for p in d.iterdir():
            if p.suffix == ".md" and p.stem.startswith("plan_v"):
                try:
                    versions.append(int(p.stem.removeprefix("plan_v")))
                except ValueError:
                    continue
        return sorted(versions)

    def next_plan_version(self, user_id: str, season_id: str) -> int:
        existing = self.list_plan_versions(user_id, season_id)
        return (existing[-1] + 1) if existing else 1


__all__ = ["FileStore"]
