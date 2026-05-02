from __future__ import annotations

from pathlib import Path

import pytest

from pathwise.core.store import FileStore


@pytest.fixture
def store(tmp_path: Path) -> FileStore:
    return FileStore(tmp_path / "users")
