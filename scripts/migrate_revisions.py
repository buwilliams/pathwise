"""One-shot migration to the revisioned season layout.

For each user under ``data/users/``:

1. Rename ``seasons/transition-to-adulthood/`` → ``seasons/build-independence/``
   if the old name still exists and the new one doesn't.
2. Stamp ``pack_version`` on every record under that season that lacks one.
   Default value when missing: ``"0.3.0"`` (the only revision that exists
   pre-migration).
3. Rewrite the ``season_id`` field stored *inside* records from
   ``"transition-to-adulthood"`` to ``"build-independence"``.

Idempotent: re-runs are no-ops once a record already has the new slug or a
``pack_version`` field.

Usage:
    uv run python scripts/migrate_revisions.py --users-dir ./data/users
    uv run python scripts/migrate_revisions.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

OLD_SLUG = "transition-to-adulthood"
NEW_SLUG = "build-independence"
DEFAULT_PACK_VERSION = "0.3.0"

logger = logging.getLogger("migrate_revisions")


def _user_dirs(users_dir: Path) -> list[Path]:
    """Two-level shard: ``{base}/{aa}/{bb}/{user_id}/``."""
    out: list[Path] = []
    for a in sorted(users_dir.iterdir()) if users_dir.is_dir() else []:
        if not a.is_dir():
            continue
        for b in sorted(a.iterdir()):
            if not b.is_dir():
                continue
            for u in sorted(b.iterdir()):
                if u.is_dir() and (u / "profile.json").exists():
                    out.append(u)
    return out


def _rewrite_season_id(record: dict[str, Any]) -> bool:
    """Replace any nested ``season_id`` referencing the old slug. Returns True
    if the record was modified."""
    changed = False
    if record.get("season_id") == OLD_SLUG:
        record["season_id"] = NEW_SLUG
        changed = True
    return changed


def _stamp_pack_version(record: dict[str, Any]) -> bool:
    if "pack_version" in record:
        return False
    record["pack_version"] = DEFAULT_PACK_VERSION
    return True


def _migrate_json(path: Path, *, dry_run: bool) -> bool:
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        logger.warning("skip (unreadable JSON): %s", path)
        return False
    if not isinstance(data, dict):
        return False
    changed = _rewrite_season_id(data) | _stamp_pack_version(data)
    if changed and not dry_run:
        path.write_text(json.dumps(data, indent=2, sort_keys=True))
    return changed


def _migrate_jsonl(path: Path, *, dry_run: bool) -> bool:
    try:
        lines = path.read_text().splitlines()
    except OSError:
        logger.warning("skip (unreadable JSONL): %s", path)
        return False
    out: list[str] = []
    changed = False
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            logger.warning("skip line (not JSON) in %s", path)
            out.append(line)
            continue
        if not isinstance(rec, dict):
            out.append(line)
            continue
        rec_changed = _rewrite_season_id(rec) | _stamp_pack_version(rec)
        if rec_changed:
            changed = True
        out.append(json.dumps(rec))
    if changed and not dry_run:
        path.write_text("\n".join(out) + ("\n" if out else ""))
    return changed


def _migrate_answers_json(answers_path: Path, *, dry_run: bool) -> bool:
    """``answers.json`` is a flat ``{question_key: value}`` map. We must NOT
    pollute it with a top-level ``pack_version``; that field belongs in the
    sibling ``answers.meta.json``. Strip it from the answers file if a prior
    migration put it there, and write the meta sibling.
    """
    try:
        data = json.loads(answers_path.read_text())
    except (json.JSONDecodeError, OSError):
        logger.warning("skip (unreadable JSON): %s", answers_path)
        return False
    if not isinstance(data, dict):
        return False
    pack_version = data.pop("pack_version", DEFAULT_PACK_VERSION)
    meta_path = answers_path.with_name("answers.meta.json")
    needs_meta = not meta_path.exists()
    if not dry_run:
        answers_path.write_text(json.dumps(data, indent=2, sort_keys=True))
        if needs_meta:
            meta_path.write_text(
                json.dumps(
                    {"pack_version": pack_version, "updated_at": 0},
                    indent=2,
                    sort_keys=True,
                )
            )
    return True


def _migrate_user(user_dir: Path, *, dry_run: bool) -> dict[str, int]:
    counters = {"renamed": 0, "json": 0, "jsonl": 0, "skipped": 0}

    seasons_dir = user_dir / "seasons"
    if not seasons_dir.is_dir():
        return counters

    old_dir = seasons_dir / OLD_SLUG
    new_dir = seasons_dir / NEW_SLUG
    if old_dir.is_dir() and not new_dir.exists():
        if dry_run:
            logger.info("would rename %s → %s", old_dir, new_dir)
        else:
            old_dir.rename(new_dir)
        counters["renamed"] += 1
    elif old_dir.is_dir() and new_dir.exists():
        logger.warning(
            "both %s and %s exist; manual merge needed for user %s",
            OLD_SLUG, NEW_SLUG, user_dir.name,
        )
        counters["skipped"] += 1

    season_dir = seasons_dir / NEW_SLUG
    if not season_dir.is_dir():
        return counters

    # events.jsonl lives at the user root, not under a season dir
    events_path = user_dir / "events.jsonl"
    if events_path.exists() and _migrate_jsonl(events_path, dry_run=dry_run):
        counters["jsonl"] += 1

    answers_path = season_dir / "answers.json"
    if answers_path.exists() and _migrate_answers_json(answers_path, dry_run=dry_run):
        counters["json"] += 1

    for path in season_dir.rglob("*"):
        if path.is_dir() or path == answers_path:
            continue
        if path.name == "answers.meta.json":
            continue
        if path.suffix == ".json":
            if _migrate_json(path, dry_run=dry_run):
                counters["json"] += 1
        elif path.suffix == ".jsonl":
            if _migrate_jsonl(path, dry_run=dry_run):
                counters["jsonl"] += 1

    return counters


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--users-dir",
        default="data/users",
        help="Path to the users data directory (default: data/users)",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    users_dir = Path(args.users_dir).resolve()
    if not users_dir.is_dir():
        logger.error("users dir not found: %s", users_dir)
        return 1

    totals = {"users": 0, "renamed": 0, "json": 0, "jsonl": 0, "skipped": 0}
    for user_dir in _user_dirs(users_dir):
        totals["users"] += 1
        counters = _migrate_user(user_dir, dry_run=args.dry_run)
        for k, v in counters.items():
            totals[k] += v

    logger.info(
        "%s: users=%d renamed=%d json=%d jsonl=%d skipped=%d",
        "DRY RUN" if args.dry_run else "DONE",
        totals["users"], totals["renamed"], totals["json"],
        totals["jsonl"], totals["skipped"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
