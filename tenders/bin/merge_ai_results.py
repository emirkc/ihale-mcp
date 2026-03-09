#!/usr/bin/env python3
"""Merge AI enrichment results into tender decisions."""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Europe/Istanbul")
except Exception:
    TZ = None

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

def main() -> int:
    results_path = DATA / "ai_enrichment_results.json"
    decisions_path = DATA / "tender_decisions.json"

    if not results_path.exists():
        print("No AI enrichment results found.")
        return 0

    results = json.loads(results_path.read_text(encoding="utf-8"))
    decisions = json.loads(decisions_path.read_text(encoding="utf-8"))

    ai_items = {item["ikn"]: item for item in results.get("results", [])}
    if not ai_items:
        print("AI results file is empty.")
        return 0

    updated = 0
    for decision in decisions.get("items", []):
        ikn = decision.get("ikn")
        if ikn not in ai_items:
            continue

        ai = ai_items[ikn]
        old_cls = decision.get("classification")
        old_score = decision.get("internal_score", 0)

        # Apply AI adjustment
        adjustment = ai.get("ai_score_adjustment", 0)
        new_score = max(0, min(100, old_score + adjustment))
        new_cls = ai.get("ai_classification", old_cls)

        decision["internal_score"] = new_score
        decision["external_score"] = round(max(1.0, min(10.0, new_score / 10.0)), 1)
        decision["classification"] = new_cls
        decision["confidence"] = ai.get("ai_confidence", decision.get("confidence", 0.5))
        decision["ai_enriched"] = True
        decision["ai_reasoning"] = ai.get("ai_reasoning", "")
        decision["ai_product_relevance"] = ai.get("ai_product_relevance", "")

        # Track the change
        if old_cls != new_cls or abs(old_score - new_score) >= 5:
            decision["status_tag"] = "AI_UPDATED"

        updated += 1

    # Re-sort by score
    decisions["items"] = sorted(
        decisions.get("items", []),
        key=lambda x: (x.get("external_score", 0), x.get("ikn", "")),
        reverse=True
    )

    now = datetime.now(TZ) if TZ else datetime.now()
    decisions["updated_at"] = now.isoformat()
    decisions["last_ai_merge_at"] = now.isoformat()

    decisions_path.write_text(
        json.dumps(decisions, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )

    # Archive the processed results
    archive_name = f"ai_results_{now.strftime('%Y%m%d_%H%M')}.json"
    archive_dir = DATA / "archive"
    archive_dir.mkdir(exist_ok=True)
    (archive_dir / archive_name).write_text(
        results_path.read_text(encoding="utf-8"),
        encoding="utf-8"
    )

    # Clear the queue and results
    results_path.unlink()
    queue_path = DATA / "ai_enrichment_queue.json"
    if queue_path.exists():
        queue_path.unlink()

    print(f"AI merge complete: {updated} tenders updated, results archived to {archive_name}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
