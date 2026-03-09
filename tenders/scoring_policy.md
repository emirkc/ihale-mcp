# Tender Scoring Policy

## Overview

Every tender is scored on a 100-point internal scale, then mapped to a 10-point external score for reporting. The score determines the tender's classification and whether it surfaces to the operator.

## Internal Score (0-100) to External Score (1-10) Mapping

| Internal Score | External Score | Classification | Action |
|---|---|---|---|
| 85-100 | 9-10 | ACTION | Immediately notify operator. High-confidence match. |
| 65-84 | 7-8 | STRONG_CANDIDATE | Include in daily report with recommendation to review. |
| 40-64 | 4-6 | WATCH | Include in daily report, lower section. Monitor for updates. |
| 0-39 | 1-3 | SILENT_REJECT | Log to tender_decisions.json. Do not include in reports unless specifically requested. |

## Scoring Components

### 1. Product Relevance (0-35 points)

How closely the tender's items match the company's product portfolio.

| Condition | Points |
|---|---|
| Tender title/description explicitly names core product (masa, dolap, keson, koltuk, sandalye, yönetici takımı) | 30-35 |
| Tender mentions complementary products (kitaplık, panel bölme, banko, bekleme grubu) | 20-29 |
| Tender is a mixed procurement with some furniture items among unrelated items | 10-19 |
| Tender mentions "mobilya" generically without specific product names | 15-20 |
| No clear product match but OKAS code suggests relevance | 8-12 |
| No product relevance detected | 0 |

### 2. OKAS Code Match (0-20 points)

Based on `okas_signal_map.json` score_boost values, normalized to this range.

| Condition | Points |
|---|---|
| Core relevance OKAS code match (39121000, 39130000, etc.) | 16-20 |
| High relevance OKAS code match | 10-15 |
| Medium relevance OKAS code match | 5-9 |
| Secondary code match only | 4-8 |
| No OKAS match but keyword match exists | 0 |
| Negative OKAS code detected | -10 (penalty) |

### 3. Authority Quality (0-15 points)

Based on `authority_preferences.json` tier mapping.

| Condition | Points |
|---|---|
| Tier 1 authority | 12-15 |
| Tier 2 authority | 7-11 |
| Tier 3 authority | 2-6 |
| Unknown authority (not in any tier) | 3 |
| Blacklisted authority | -15 (penalty, triggers SILENT_REJECT) |

### 4. Tender Size & Value (0-10 points)

| Condition | Points |
|---|---|
| Estimated value > 1M TL or large item count | 8-10 |
| Estimated value 250K-1M TL | 5-7 |
| Estimated value 50K-250K TL | 2-4 |
| Estimated value < 50K TL or unknown | 1-2 |
| Value cannot be determined | 3 (neutral) |

### 5. Deadline Feasibility (0-10 points)

| Condition | Points |
|---|---|
| Submission deadline > 15 days away | 8-10 |
| Submission deadline 7-15 days away | 5-7 |
| Submission deadline 3-7 days away | 2-4 |
| Submission deadline < 3 days away | 0-1 |
| Deadline passed | 0 (auto-reject) |

### 6. Positive Signals (0-10 points)

Additive points for signals listed in `positive_signals.txt`.

| Condition | Points |
|---|---|
| 3+ positive signals detected | 8-10 |
| 2 positive signals | 5-7 |
| 1 positive signal | 2-4 |
| No positive signals | 0 |

## Hard Reject Rules

A tender is immediately classified as SILENT_REJECT (score = 0) if ANY of these conditions are true:

1. **Hard reject keyword match:** Title or description contains any keyword from `search_config.json` → `hard_reject_keywords`
2. **Blacklisted authority:** Procuring authority is in `authority_preferences.json` → `blacklist`
3. **Negative OKAS code:** Primary OKAS code is in `okas_signal_map.json` → `negative_codes` with `action: "hard_reject"`
4. **Expired deadline:** Tender submission deadline has passed
5. **Expired/superseded duplicate state:** If a tender is already tracked and unchanged, suppress re-reporting instead of treating it as a fresh opportunity

## Soft Reject Rules

These reduce score but do not trigger automatic rejection:

1. **Soft reject keyword presence:** -5 points per keyword from `soft_reject_keywords` found (max -15)
2. **Mixed procurement dominance:** If furniture items represent < 20% of total tender items, -10 points
3. **Very short deadline:** < 3 days, -5 additional points
4. **Low-value threshold:** Estimated value < 20K TL, -5 points

## Risk Flags

Risk flags do not affect scoring but are appended to the tender assessment for operator awareness:

| Flag | Trigger |
|---|---|
| `RISK:TIGHT_DEADLINE` | Submission deadline < 5 days |
| `RISK:MIXED_PROCUREMENT` | Furniture is minority of total items |
| `RISK:UNKNOWN_AUTHORITY` | Authority not found in any tier |
| `RISK:LOW_CONFIDENCE` | Confidence score < 0.6 |
| `RISK:FIRST_TIME_AUTHORITY` | Authority has no prior tenders in history |
| `RISK:HIGH_COMPETITION` | Tender type is "Açık İhale" with low estimated value |

## Confidence Score (0.0 - 1.0)

Confidence reflects how certain the system is about the classification:

| Confidence | Meaning |
|---|---|
| 0.9 - 1.0 | Title explicitly mentions core products + OKAS match + known authority |
| 0.7 - 0.89 | Strong keyword match + either OKAS or authority match |
| 0.5 - 0.69 | Keyword match only, or OKAS match only, ambiguous context |
| 0.3 - 0.49 | Weak signals, possibly relevant, high uncertainty |
| 0.0 - 0.29 | Minimal relevance signals, likely false positive |

## Urgency Levels

| Urgency | Condition |
|---|---|
| CRITICAL | Deadline < 3 days AND score >= 65 |
| HIGH | Deadline < 7 days AND score >= 65 |
| NORMAL | Deadline >= 7 days OR score 40-64 |
| LOW | Score < 40 or WATCH classification |

## Score Adjustment Log

Every score must be accompanied by a reason breakdown showing points awarded per component. This enables tuning and operator override. See `reason_codes.md` for standardized reason identifiers.
