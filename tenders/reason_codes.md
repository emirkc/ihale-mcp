# Reason Codes

Standardized identifiers for score breakdown in `tender_decisions.json`. Every scoring decision logs one or more reason codes with points awarded.

## Product Relevance (PR)

| Code | Description | Points |
|---|---|---|
| `PR_CORE_EXACT` | Title/description explicitly names a core product (masa, dolap, keson, koltuk, sandalye, yönetici takımı) | +30 to +35 |
| `PR_COMPLEMENT` | Complementary product match (kitaplık, panel bölme, banko, bekleme grubu) | +20 to +29 |
| `PR_MIXED` | Mixed procurement containing some furniture items among unrelated items | +10 to +19 |
| `PR_GENERIC` | Generic "mobilya" mention without specific product names | +15 to +20 |
| `PR_OKAS_ONLY` | No keyword match but OKAS code suggests relevance | +8 to +12 |
| `PR_NONE` | No product relevance detected | 0 |

## OKAS Code Match (OK)

| Code | Description | Points |
|---|---|---|
| `OK_CORE` | Core-relevance OKAS code match (39121000, 39130000, etc.) | +16 to +20 |
| `OK_HIGH` | High-relevance OKAS code match | +10 to +15 |
| `OK_MEDIUM` | Medium-relevance OKAS code match | +5 to +9 |
| `OK_SECONDARY` | Secondary code match only | +4 to +8 |
| `OK_KEYWORD_ONLY` | No OKAS match but keyword match exists | 0 |
| `OK_NEGATIVE` | Negative OKAS code detected | -10 |

## Authority Quality (AQ)

| Code | Description | Points |
|---|---|---|
| `AQ_TIER1` | Tier 1 authority (bakanlık, TBMM, Cumhurbaşkanlığı) | +12 to +15 |
| `AQ_TIER2` | Tier 2 authority (büyükşehir, üniversite, hastane) | +7 to +11 |
| `AQ_TIER3` | Tier 3 authority (ilçe belediyesi, köylere hizmet) | +2 to +6 |
| `AQ_UNKNOWN` | Authority not in any tier | +3 |
| `AQ_BLACKLIST` | Blacklisted authority → triggers SILENT_REJECT | -15 |

## Tender Size & Value (TV)

| Code | Description | Points |
|---|---|---|
| `TV_LARGE` | Estimated value > 1M TL or large item count | +8 to +10 |
| `TV_MEDIUM` | Estimated value 250K-1M TL | +5 to +7 |
| `TV_SMALL` | Estimated value 50K-250K TL | +2 to +4 |
| `TV_MICRO` | Estimated value < 50K TL or unknown | +1 to +2 |
| `TV_UNKNOWN` | Value cannot be determined | +3 |

## Deadline Feasibility (DF)

| Code | Description | Points |
|---|---|---|
| `DF_COMFORTABLE` | Submission deadline > 15 days away | +8 to +10 |
| `DF_ADEQUATE` | Submission deadline 7-15 days away | +5 to +7 |
| `DF_TIGHT` | Submission deadline 3-7 days away | +2 to +4 |
| `DF_CRITICAL` | Submission deadline < 3 days away | +0 to +1 |
| `DF_EXPIRED` | Deadline has passed → auto-reject | 0 |

## Positive Signals (PS)

| Code | Description | Points |
|---|---|---|
| `PS_STRONG` | 3+ positive signals from positive_signals.txt | +8 to +10 |
| `PS_MODERATE` | 2 positive signals | +5 to +7 |
| `PS_WEAK` | 1 positive signal | +2 to +4 |
| `PS_NONE` | No positive signals | 0 |

## Hard Reject (HR)

| Code | Description | Effect |
|---|---|---|
| `HR_KEYWORD` | Hard reject keyword found in title/description | Score = 0, SILENT_REJECT |
| `HR_BLACKLIST` | Authority is blacklisted | Score = 0, SILENT_REJECT |
| `HR_NEGATIVE_OKAS` | Primary OKAS code is hard_reject negative | Score = 0, SILENT_REJECT |
| `HR_EXPIRED` | Tender deadline has passed | Score = 0, SILENT_REJECT |
| `HR_DUPLICATE` | IKN already in seen_tenders.json with final decision | Skip entirely |

## Soft Reject (SR)

| Code | Description | Points |
|---|---|---|
| `SR_KEYWORD` | Soft reject keyword found (-5 per keyword, max -15) | -5 to -15 |
| `SR_MIXED_DOMINANT` | Furniture < 20% of total items | -10 |
| `SR_SHORT_DEADLINE` | < 3 days deadline additional penalty | -5 |
| `SR_LOW_VALUE` | Estimated value < 20K TL | -5 |

## Risk Flags (RF)

| Code | Description | Effect |
|---|---|---|
| `RF_TIGHT_DEADLINE` | Submission deadline < 5 days | Appended to assessment |
| `RF_MIXED_PROCUREMENT` | Furniture is minority of total items | Appended to assessment |
| `RF_UNKNOWN_AUTHORITY` | Authority not found in any tier | Appended to assessment |
| `RF_LOW_CONFIDENCE` | Confidence score < 0.6 | Appended to assessment |
| `RF_FIRST_TIME_AUTHORITY` | Authority has no prior tenders in history | Appended to assessment |
| `RF_HIGH_COMPETITION` | Açık İhale + low estimated value | Appended to assessment |

## Usage

Each tender decision in `tender_decisions.json` includes a `reasons` array:

```json
{
  "reasons": [
    {"code": "PR_CORE_EXACT", "points": 32, "detail": "çalışma masası, dosya dolabı"},
    {"code": "OK_CORE", "points": 20, "detail": "39121000"},
    {"code": "AQ_TIER1", "points": 14, "detail": "Sağlık Bakanlığı"},
    {"code": "TV_MEDIUM", "points": 6, "detail": "~500K TL estimated"},
    {"code": "DF_COMFORTABLE", "points": 9, "detail": "22 days remaining"},
    {"code": "PS_MODERATE", "points": 6, "detail": "büro mobilya alımı, mal alımı"}
  ],
  "risk_flags": ["RF_FIRST_TIME_AUTHORITY"]
}
```
