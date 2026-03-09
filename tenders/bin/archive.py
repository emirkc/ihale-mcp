#!/usr/bin/env python3
"""Archive old tender data to keep active files lean.

Moves old events, scores, seen tenders, and decisions into monthly JSONL
archive files under data/archive/.  Safe to run multiple times (idempotent)
because it only appends to archive files and rewrites active files with the
remaining (non-archived) data.

Usage:
    python bin/archive.py            # run for real
    python bin/archive.py --dry-run  # only show what would be archived
"""
from __future__ import annotations

import argparse
import json
import shutil
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ARCHIVE = DATA / "archive"
TZ = ZoneInfo("Europe/Istanbul") if ZoneInfo else None
NOW = datetime.now(TZ) if TZ else datetime.now()


# ---------------------------------------------------------------------------
# Helpers (mirrors scan.py conventions)
# ---------------------------------------------------------------------------

def load_json(path: Path, default: Any = None) -> Any:
    from copy import deepcopy
    if not path.exists():
        return deepcopy(default)
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return deepcopy(default)
    return json.loads(text)


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_iso(value: str | None) -> datetime | None:
    """Parse an ISO-8601 timestamp (with or without timezone)."""
    if not value:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    return None


def parse_tender_dt(value: str | None) -> datetime | None:
    """Parse a tender deadline string like '10.03.2026 10:00'."""
    if not value:
        return None
    for fmt in ("%d.%m.%Y %H:%M", "%d.%m.%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.replace(tzinfo=TZ) if TZ else parsed
        except ValueError:
            pass
    return None


def month_key(dt: datetime) -> str:
    """Return YYYY-MM for the given datetime."""
    return dt.strftime("%Y-%m")


def append_jsonl(path: Path, objects: list[dict]) -> None:
    """Append JSON objects to a JSONL file (one per line)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for obj in objects:
            fh.write(json.dumps(obj, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# 1. Archive old tender_history events
# ---------------------------------------------------------------------------

def archive_history(dry_run: bool) -> int:
    path = DATA / "tender_history.json"
    history = load_json(path, {"version": "1.0.0", "events": [], "updated_at": None})
    events = history.get("events", [])
    if not events:
        return 0

    cutoff = NOW - timedelta(days=30)
    keep: list[dict] = []
    to_archive: dict[str, list[dict]] = defaultdict(list)

    for event in events:
        ts = parse_iso(event.get("timestamp"))
        if ts and ts < cutoff:
            mk = month_key(ts)
            to_archive[mk].append(event)
        else:
            keep.append(event)

    archived = sum(len(v) for v in to_archive.values())
    if archived == 0:
        return 0

    if dry_run:
        return archived

    for mk, items in sorted(to_archive.items()):
        append_jsonl(ARCHIVE / f"history-{mk}.jsonl", items)

    history["events"] = keep
    history["updated_at"] = NOW.isoformat()
    save_json(path, history)
    return archived


# ---------------------------------------------------------------------------
# 2. Archive old score_history entries
# ---------------------------------------------------------------------------

def archive_scores(dry_run: bool) -> int:
    path = DATA / "score_history.jsonl"
    if not path.exists():
        return 0

    cutoff = NOW - timedelta(days=30)
    keep_lines: list[str] = []
    to_archive: dict[str, list[dict]] = defaultdict(list)

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # skip non-JSON lines (e.g. "init")
        if not line.startswith("{"):
            keep_lines.append(line)
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            keep_lines.append(line)
            continue

        ts = parse_iso(obj.get("timestamp"))
        if ts and ts < cutoff:
            mk = month_key(ts)
            to_archive[mk].append(obj)
        else:
            keep_lines.append(json.dumps(obj, ensure_ascii=False))

    archived = sum(len(v) for v in to_archive.values())
    if archived == 0:
        return 0

    if dry_run:
        return archived

    for mk, items in sorted(to_archive.items()):
        append_jsonl(ARCHIVE / f"scores-{mk}.jsonl", items)

    path.write_text("\n".join(keep_lines) + ("\n" if keep_lines else ""), encoding="utf-8")
    return archived


# ---------------------------------------------------------------------------
# 3. Archive expired/rejected seen tenders
# ---------------------------------------------------------------------------

def archive_seen(dry_run: bool) -> int:
    path = DATA / "seen_tenders.json"
    seen = load_json(path, {"version": "1.0.0", "items": [], "updated_at": None})
    items = seen.get("items", [])
    if not items:
        return 0

    cutoff = NOW - timedelta(days=60)
    keep: list[dict] = []
    to_archive: dict[str, list[dict]] = defaultdict(list)

    for item in items:
        cls = item.get("latest_classification")
        last_seen = parse_iso(item.get("last_seen_at"))
        if cls == "SILENT_REJECT" and last_seen and last_seen < cutoff:
            mk = month_key(last_seen)
            to_archive[mk].append(item)
        else:
            keep.append(item)

    archived = sum(len(v) for v in to_archive.values())
    if archived == 0:
        return 0

    if dry_run:
        return archived

    for mk, items_batch in sorted(to_archive.items()):
        append_jsonl(ARCHIVE / f"seen-{mk}.jsonl", items_batch)

    seen["items"] = keep
    seen["updated_at"] = NOW.isoformat()
    save_json(path, seen)
    return archived


# ---------------------------------------------------------------------------
# 4. Archive old decisions
# ---------------------------------------------------------------------------

def archive_decisions(dry_run: bool) -> int:
    path = DATA / "tender_decisions.json"
    decisions = load_json(path, {"version": "1.0.0", "items": [], "updated_at": None})
    items = decisions.get("items", [])
    if not items:
        return 0

    cutoff = NOW - timedelta(days=60)
    keep: list[dict] = []
    to_archive: dict[str, list[dict]] = defaultdict(list)

    for item in items:
        cls = item.get("classification")
        has_label = item.get("operator_label")
        deadline_dt = parse_tender_dt(item.get("deadline"))
        if cls == "SILENT_REJECT" and not has_label and deadline_dt and deadline_dt < cutoff:
            mk = month_key(deadline_dt)
            to_archive[mk].append(item)
        else:
            keep.append(item)

    archived = sum(len(v) for v in to_archive.values())
    if archived == 0:
        return 0

    if dry_run:
        return archived

    for mk, items_batch in sorted(to_archive.items()):
        append_jsonl(ARCHIVE / f"decisions-{mk}.jsonl", items_batch)

    decisions["items"] = keep
    decisions["updated_at"] = NOW.isoformat()
    save_json(path, decisions)
    return archived


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Archive old tender data to keep active files lean."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print what would be archived; do not write anything.",
    )
    args = parser.parse_args()

    if not args.dry_run:
        ARCHIVE.mkdir(parents=True, exist_ok=True)

    prefix = "[DRY RUN] " if args.dry_run else ""

    history_count = archive_history(args.dry_run)
    score_count = archive_scores(args.dry_run)
    seen_count = archive_seen(args.dry_run)
    decision_count = archive_decisions(args.dry_run)

    print(
        f"{prefix}Archived: {history_count} history events, "
        f"{score_count} score entries, "
        f"{seen_count} seen tenders, "
        f"{decision_count} decisions"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
