# Delta Scan Prompt — Koç Büro Tender Radar

You are running a mid-cycle delta scan for Koç Büro Mobilyaları.

## Goal
Detect only meaningful changes since the last successful run and avoid noise.

## Load first
Read the same core files as the daily scan, especially:
- `tenders/search_config.json`
- `tenders/scoring_policy.md`
- `tenders/data/seen_tenders.json`
- `tenders/data/tender_decisions.json`
- `tenders/data/tender_history.json`
- `tenders/data/run_state.json`

## Search strategy
- Use the highest-value keyword clusters first.
- Use `tender_types: [1]` and `tender_date_filter: "from_today"`.
- Focus on changes that could matter operationally today.

## What counts as alert-worthy
Only alert when at least one is true:
- a NEW ACTION tender appears
- a STRONG_CANDIDATE becomes ACTION
- a known tender becomes LAST_CALL
- a new high-confidence STRONG_CANDIDATE appears
- detail enrichment reveals a decisive new signal

## What should stay silent
Do not notify if:
- only low-value WATCH tenders appear
- previously seen tenders remain unchanged
- score changes are minor and do not affect priority

## State handling
Update state files like the daily scan, but mark:
- `last_run_type = "delta"`
- event_type values such as `delta_discovered`, `delta_reported`, `delta_suppressed`

## Output
- Write an internal markdown note only if there are meaningful changes.
- Send a compact Telegram summary only if there is something actionable.
- If nothing meaningful changed, return a brief no-op summary for logs and do not spam Telegram.
