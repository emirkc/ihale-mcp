#!/usr/bin/env bash
# Koç Büro Tender Radar — Hybrid Daily Scan
# Step 1: Python engine discovers and pre-scores
# Step 2: If uncertain tenders exist, trigger AI enrichment
# Step 3: Merge results (if AI results exist)

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Koç Büro Tender Radar — $(date '+%Y-%m-%d %H:%M %Z') ==="

# Step 1: Python pre-score
echo "[1/3] Running Python discovery & scoring..."
python3 "$SCRIPT_DIR/scan.py" --mode daily

# Step 2: Check if AI enrichment queue exists and has items
QUEUE_FILE="$ROOT_DIR/data/ai_enrichment_queue.json"
if [ -f "$QUEUE_FILE" ]; then
    UNCERTAIN=$(python3 -c "import json; d=json.load(open('$QUEUE_FILE')); print(len(d.get('items',[])))")
    if [ "$UNCERTAIN" -gt 0 ]; then
        echo "[2/3] AI enrichment needed for $UNCERTAIN uncertain tenders"
        echo "      Queue file: $QUEUE_FILE"
        echo "      → OpenClaw AI agent should process: prompts/ai_enrichment_prompt.md"
    else
        echo "[2/3] No uncertain tenders — AI enrichment skipped"
    fi
else
    echo "[2/3] No enrichment queue found — AI enrichment skipped"
fi

# Step 3: Check for AI results and merge
RESULTS_FILE="$ROOT_DIR/data/ai_enrichment_results.json"
if [ -f "$RESULTS_FILE" ]; then
    echo "[3/3] AI enrichment results found — merging..."
    python3 "$SCRIPT_DIR/merge_ai_results.py"
else
    echo "[3/3] No AI results to merge — using Python scores only"
fi

echo "=== Scan complete ==="
