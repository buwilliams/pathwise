from __future__ import annotations

from pathlib import Path

from pathwise.seasons._base import BaseLogic


class Logic(BaseLogic):
    REVISION_DIR = Path(__file__).resolve().parent


def make_logic() -> Logic:
    return Logic.make()
