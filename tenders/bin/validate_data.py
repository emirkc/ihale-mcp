#!/usr/bin/env python3
"""Validate tender data files against expected schemas."""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

# ---------------------------------------------------------------------------
# Allowed enum values
# ---------------------------------------------------------------------------

VALID_CLASSIFICATIONS = {"ACTION", "STRONG_CANDIDATE", "WATCH", "SILENT_REJECT"}
VALID_BID_STATUSES = {
    "reviewing", "preparing_bid", "bid_submitted",
    "won", "lost", "cancelled", "no_bid",
}

# ---------------------------------------------------------------------------
# Schema definitions — each is a list of (field, type_check, required, extra)
#   type_check: tuple of types for isinstance OR a callable returning bool
#   required:   True/False
#   extra:      optional dict with "enum", "min", "max" constraints
# ---------------------------------------------------------------------------

SEEN_TENDER_FIELDS: list[tuple[str, Any, bool, dict]] = [
    ("ikn",                    (str, type(None)), True,  {}),
    ("title",                  (str,),            True,  {}),
    ("authority",              (str,),            True,  {}),
    ("latest_classification",  (str,),            True,  {"enum": VALID_CLASSIFICATIONS}),
    ("latest_internal_score",  (int, float),      True,  {"min": 0, "max": 100}),
    ("latest_external_score",  (int, float),      True,  {"min": 1.0, "max": 10.0}),
    ("first_seen_at",          (str,),            True,  {}),
    ("last_seen_at",           (str,),            True,  {}),
]

DECISION_FIELDS: list[tuple[str, Any, bool, dict]] = [
    ("ikn",              (str, type(None)), True,  {}),
    ("title",            (str,),            True,  {}),
    ("classification",   (str,),            True,  {"enum": VALID_CLASSIFICATIONS}),
    ("internal_score",   (int, float),      True,  {"min": 0, "max": 100}),
    ("external_score",   (int, float),      True,  {"min": 1.0, "max": 10.0}),
    ("confidence",       (float, int),      True,  {"min": 0.0, "max": 1.0}),
    ("reasons",          (list,),           True,  {}),
]

RUN_STATE_FIELDS: list[tuple[str, Any, bool, dict]] = [
    ("version",                (str,),            True,  {}),
    ("last_run_type",          (str, type(None)), True,  {}),
    ("last_successful_run_at", (str, type(None)), True,  {}),
]

BID_TRACKING_FIELDS: list[tuple[str, Any, bool, dict]] = [
    ("ikn",    (str,), True, {}),
    ("status", (str,), True, {"enum": VALID_BID_STATUSES}),
]

# Map of short name -> (filename, schema, is_list, root_key)
FILE_SCHEMAS: dict[str, tuple[str, list, bool, str | None]] = {
    "seen":      ("seen_tenders.json",    SEEN_TENDER_FIELDS,  True,  "items"),
    "decisions": ("tender_decisions.json", DECISION_FIELDS,     True,  "items"),
    "run_state": ("run_state.json",       RUN_STATE_FIELDS,    False, None),
    "bid":       ("bid_tracking.json",    BID_TRACKING_FIELDS, True,  "items"),
}

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


class Issue:
    """A single validation issue — either a warning or an error."""

    def __init__(self, level: str, message: str) -> None:
        self.level = level  # "warning" or "error"
        self.message = message

    def __str__(self) -> str:
        prefix = "WARNING" if self.level == "warning" else "ERROR"
        return f"  - [{prefix}] {self.message}"


def _item_label(item: dict[str, Any]) -> str:
    """Human-readable label for a tender item."""
    ikn = item.get("ikn")
    if ikn:
        return f"Item {ikn}"
    title = item.get("title", "???")
    return f"Item '{title[:50]}'"


def validate_item(item: dict[str, Any], schema: list[tuple[str, Any, bool, dict]], label: str) -> list[Issue]:
    """Validate a single item dict against a schema."""
    issues: list[Issue] = []

    for field_name, type_tuple, required, extra in schema:
        # --- presence check ---
        if field_name not in item:
            if required:
                issues.append(Issue("error", f"{label}: missing required field '{field_name}'"))
            continue

        value = item[field_name]

        # --- None handling ---
        if value is None:
            if type(None) in type_tuple:
                continue  # None is allowed
            issues.append(Issue("error", f"{label}: '{field_name}' is null but null is not allowed"))
            continue

        # --- type check ---
        if not isinstance(value, type_tuple):
            expected = "/".join(t.__name__ for t in type_tuple if t is not type(None))
            issues.append(Issue("error", f"{label}: '{field_name}' expected {expected}, got {type(value).__name__}"))
            continue

        # --- enum check ---
        if "enum" in extra and value not in extra["enum"]:
            issues.append(Issue("warning", f"{label}: '{field_name}' value '{value}' not in {sorted(extra['enum'])}"))

        # --- range check ---
        if "min" in extra and isinstance(value, (int, float)):
            if value < extra["min"]:
                issues.append(Issue("warning", f"{label}: '{field_name}' value {value} below minimum {extra['min']}"))
        if "max" in extra and isinstance(value, (int, float)):
            if value > extra["max"]:
                issues.append(Issue("warning", f"{label}: '{field_name}' value {value} above maximum {extra['max']}"))

    return issues


def check_duplicate_ikns(items: list[dict[str, Any]], file_label: str) -> list[Issue]:
    """Check for duplicate IKN values."""
    issues: list[Issue] = []
    seen_ikns: dict[str, int] = {}
    for idx, item in enumerate(items):
        ikn = item.get("ikn")
        if ikn is None:
            continue
        if ikn in seen_ikns:
            issues.append(Issue("warning", f"Duplicate IKN found: {ikn} (indices {seen_ikns[ikn]} and {idx})"))
        else:
            seen_ikns[ikn] = idx
    return issues


# ---------------------------------------------------------------------------
# Per-file validation
# ---------------------------------------------------------------------------


def validate_file(short_name: str) -> tuple[list[Issue], int]:
    """
    Validate a single data file.

    Returns (issues, item_count).
    item_count is -1 if file could not be loaded.
    """
    filename, schema, is_list, root_key = FILE_SCHEMAS[short_name]
    path = DATA / filename
    issues: list[Issue] = []

    # --- file existence ---
    if not path.exists():
        issues.append(Issue("error", f"File not found: {path}"))
        return issues, -1

    # --- valid JSON ---
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        issues.append(Issue("error", f"File is empty: {path}"))
        return issues, -1

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        issues.append(Issue("error", f"Invalid JSON in {filename}: {exc}"))
        return issues, -1

    # --- root structure ---
    if not isinstance(data, dict):
        issues.append(Issue("error", f"{filename}: root must be a JSON object, got {type(data).__name__}"))
        return issues, -1

    if "version" not in data and short_name != "run_state":
        issues.append(Issue("warning", f"{filename}: missing 'version' at root level"))

    if is_list:
        if root_key and root_key not in data:
            # Try alternate key "events" for history-like files
            issues.append(Issue("error", f"{filename}: missing root key '{root_key}'"))
            return issues, -1
        items = data.get(root_key, [])
        if not isinstance(items, list):
            issues.append(Issue("error", f"{filename}: '{root_key}' must be a list, got {type(items).__name__}"))
            return issues, -1

        for idx, item in enumerate(items):
            label = _item_label(item) if isinstance(item, dict) else f"Item[{idx}]"
            if not isinstance(item, dict):
                issues.append(Issue("error", f"{filename}: {label} must be a dict, got {type(item).__name__}"))
                continue
            issues.extend(validate_item(item, schema, label))

        # duplicate IKN check
        if short_name in ("seen", "decisions"):
            issues.extend(check_duplicate_ikns(items, filename))

        return issues, len(items)
    else:
        # Single object file (run_state)
        issues.extend(validate_item(data, schema, filename))
        return issues, 0


# ---------------------------------------------------------------------------
# Fix mode — repair common issues in-place
# ---------------------------------------------------------------------------


def fix_file(short_name: str) -> list[str]:
    """Attempt to fix common issues. Returns list of fix descriptions."""
    filename, schema, is_list, root_key = FILE_SCHEMAS[short_name]
    path = DATA / filename
    fixes: list[str] = []

    if not path.exists():
        return fixes

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return fixes

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return fixes

    if not isinstance(data, dict):
        return fixes

    modified = False

    if is_list and root_key:
        items = data.get(root_key, [])
        if not isinstance(items, list):
            return fixes

        # --- Remove duplicate IKNs (keep last occurrence) ---
        if short_name in ("seen", "decisions"):
            seen_ikns: dict[str, int] = {}
            duplicates: set[int] = set()
            for idx, item in enumerate(items):
                ikn = item.get("ikn")
                if ikn is None:
                    continue
                if ikn in seen_ikns:
                    duplicates.add(seen_ikns[ikn])  # remove earlier occurrence
                    fixes.append(f"Removed duplicate IKN {ikn} (kept later entry)")
                seen_ikns[ikn] = idx
            if duplicates:
                items = [item for idx, item in enumerate(items) if idx not in duplicates]
                data[root_key] = items
                modified = True

        # --- Clamp scores ---
        for item in items:
            if not isinstance(item, dict):
                continue
            for field_name, type_tuple, required, extra in schema:
                if field_name not in item:
                    continue
                value = item[field_name]
                if value is None:
                    continue
                if not isinstance(value, (int, float)):
                    continue
                clamped = value
                if "min" in extra:
                    clamped = max(extra["min"], clamped)
                if "max" in extra:
                    clamped = min(extra["max"], clamped)
                if clamped != value:
                    label = _item_label(item)
                    fixes.append(f"{label}: clamped '{field_name}' from {value} to {clamped}")
                    item[field_name] = clamped
                    modified = True

    if modified:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return fixes


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate tender data files against expected schemas.")
    parser.add_argument(
        "--file",
        choices=list(FILE_SCHEMAS.keys()),
        help="Validate only a specific file (seen, decisions, run_state, bid)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Fix common issues: remove duplicate IKNs, clamp out-of-range scores",
    )
    args = parser.parse_args()

    targets = [args.file] if args.file else list(FILE_SCHEMAS.keys())

    if args.fix:
        print("Running in --fix mode\n")
        any_fixes = False
        for short_name in targets:
            filename = FILE_SCHEMAS[short_name][0]
            fixes = fix_file(short_name)
            if fixes:
                any_fixes = True
                print(f"Fixed {filename}:")
                for f in fixes:
                    print(f"  - {f}")
            else:
                print(f"No fixes needed for {filename}")
        print()
        # Fall through to validation after fixes

    worst_level = 0  # 0=ok, 1=warnings, 2=errors

    for short_name in targets:
        filename = FILE_SCHEMAS[short_name][0]
        issues, item_count = validate_file(short_name)

        errors = [i for i in issues if i.level == "error"]
        warnings = [i for i in issues if i.level == "warning"]

        if errors:
            worst_level = max(worst_level, 2)
            print(f"Validating {filename}... {len(errors)} error(s), {len(warnings)} warning(s)")
        elif warnings:
            worst_level = max(worst_level, 1)
            print(f"Validating {filename}... {len(warnings)} warning(s)")
        else:
            count_str = f" ({item_count} items)" if item_count >= 0 else ""
            print(f"Validating {filename}... OK{count_str}")

        for issue in issues:
            print(str(issue))

    return worst_level


if __name__ == "__main__":
    raise SystemExit(main())
