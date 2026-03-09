# Koç Büro Mobilyaları — Tender Intelligence Scaffold

## Purpose

Stateful tender discovery, scoring, and classification system for Koç Büro Mobilyaları. Scans Turkish public procurement (EKAP) for office furniture opportunities, scores them on a 100-point internal scale (mapped to 10-point external), and classifies into ACTION / STRONG_CANDIDATE / WATCH / SILENT_REJECT.

## Architecture

```
search_config.json          ← keyword clusters + OKAS boost codes + reject filters
       │
       ▼
  ┌─────────────────────────────────────────┐
  │  Tender Discovery Engine                │
  │  (daily full scan + 12h delta scan)     │
  └──────────┬──────────────────────────────┘
             │ raw candidates
             ▼
  ┌─────────────────────────────────────────┐
  │  Scoring Pipeline                       │
  │  scoring_policy.md (rules)              │
  │  okas_signal_map.json (OKAS boost)      │
  │  authority_preferences.json (tier boost) │
  │  positive_signals.txt (+points)         │
  │  negative_signals.txt (-points/reject)  │
  │  reason_codes.md (audit trail)          │
  └──────────┬──────────────────────────────┘
             │ scored + classified
             ▼
  ┌─────────────────────────────────────────┐
  │  State Layer                            │
  │  data/seen_tenders.json (dedup)         │
  │  data/score_history.jsonl (audit)       │
  │  reports/ (daily + weekly)              │
  └─────────────────────────────────────────┘
```

## Files

| File | Role |
|---|---|
| `company_profile.md` | Company identity, product portfolio, participation criteria |
| `search_config.json` | Keyword clusters, OKAS boost list, reject keywords, schedule |
| `scoring_policy.md` | 100-point scoring rubric, classification thresholds, hard/soft reject rules |
| `okas_signal_map.json` | OKAS/CPV code → relevance mapping with score boosts |
| `authority_preferences.json` | Tier 1/2/3 authorities + blacklist |
| `positive_signals.txt` | Phrases that add scoring points |
| `negative_signals.txt` | Phrases that penalize or auto-reject |
| `reason_codes.md` | Standardized reason identifiers for score breakdowns |

## State Management

The system is **stateful**: every tender encountered is logged to `data/seen_tenders.json` with its IKN, score, classification, and timestamp. Re-encounters are deduplicated. Score changes trigger re-classification and are appended to `data/score_history.jsonl`.

## Classification Thresholds

| Internal (0-100) | External (1-10) | Class | Behavior |
|---|---|---|---|
| 85-100 | 9-10 | **ACTION** | Immediate operator notification |
| 65-84 | 7-8 | **STRONG_CANDIDATE** | Daily report, review recommended |
| 40-64 | 4-6 | **WATCH** | Daily report lower section, monitor |
| 0-39 | 1-3 | **SILENT_REJECT** | Logged only, excluded from reports |

## Operators

- **Daily full scan** at 08:00 TR time across all keyword clusters
- **Delta scan** every 12 hours for new/updated tenders
- **Weekly summary** on Mondays at 09:00 TR time
- Manual re-score via `prompts/` templates

## Hybrid Workflow

The system supports a hybrid workflow where a deterministic Python engine handles discovery and pre-scoring, while an AI agent enriches uncertain tenders that fall near classification boundaries.

1. **Step 1 — Python discovery & scoring**: `bin/run_hybrid.sh` invokes `bin/scan.py --mode daily`, which searches EKAP, deduplicates, and scores all candidates using the deterministic 100-point rubric. Tenders with ambiguous scores (near classification thresholds or low confidence) are written to `data/ai_enrichment_queue.json`.

2. **Step 2 — AI enrichment**: If the queue is non-empty, the OpenClaw AI agent processes the uncertain tenders using `prompts/ai_enrichment_prompt.md`. The agent pulls additional tender details, evaluates product-line relevance, and writes its adjustments to `data/ai_enrichment_results.json`.

3. **Step 3 — Merge**: `bin/merge_ai_results.py` reads the AI results, applies score adjustments and reclassifications back into `data/tender_decisions.json`, archives the processed results under `data/archive/`, and cleans up the queue.

OpenClaw cron runs `bin/run_hybrid.sh` daily at **08:00 TR time** (Europe/Istanbul).

## Conventions

- All Turkish text uses Turkish locale for case-insensitive matching (İ/i, I/ı)
- OKAS codes follow CPV (Common Procurement Vocabulary) numbering
- Monetary values in TL unless stated otherwise
- Dates in ISO 8601 (YYYY-MM-DD)
