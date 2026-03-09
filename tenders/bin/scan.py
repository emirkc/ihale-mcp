#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import unicodedata
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REPORTS_DAILY = ROOT / "reports" / "daily"
REPORTS_WEEKLY = ROOT / "reports" / "weekly"
TZ = ZoneInfo("Europe/Istanbul") if ZoneInfo else None
NOW = datetime.now(TZ) if TZ else datetime.now()


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return deepcopy(default)
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return deepcopy(default)
    return json.loads(text)


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def backup_file(path: Path) -> None:
    """Copy *path* to data/.backup/FILENAME.bak before overwriting."""
    if not path.exists():
        return
    backup_dir = DATA / ".backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup_dir / (path.name + ".bak"))


def load_lines(path: Path) -> list[str]:
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(line.split("|")[0].strip())
    return lines


def normalize(text: str | None) -> str:
    text = (text or "").lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    repl = str.maketrans({
        "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u",
        "Ç": "c", "Ğ": "g", "İ": "i", "Ö": "o", "Ş": "s", "Ü": "u",
    })
    text = text.translate(repl)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def slug_date(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def parse_tender_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%d.%m.%Y %H:%M", "%d.%m.%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.replace(tzinfo=TZ) if TZ else parsed
        except ValueError:
            pass
    return None


def days_until(value: str | None) -> int | None:
    dt = parse_tender_dt(value)
    if not dt:
        return None
    delta = dt.date() - NOW.date()
    return delta.days


def mcporter_call(tool: str, args: dict[str, Any]) -> dict[str, Any]:
    cmd = [
        "mcporter",
        "call",
        f"ihale-mcp.{tool}",
        "--args",
        json.dumps(args, ensure_ascii=False),
        "--output",
        "json",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT.parent))
    if proc.returncode != 0:
        raise RuntimeError(f"mcporter {tool} failed: {proc.stderr or proc.stdout}")
    return json.loads(proc.stdout)


def unique_preserve(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def read_core_config() -> dict[str, Any]:
    return {
        "config": load_json(ROOT / "search_config.json", {}),
        "authority": load_json(ROOT / "authority_preferences.json", {}),
        "okas": load_json(ROOT / "okas_signal_map.json", {}),
        "positive": load_lines(ROOT / "positive_signals.txt"),
        "negative": load_lines(ROOT / "negative_signals.txt"),
        "seen": load_json(DATA / "seen_tenders.json", {"version": "1.0.0", "items": [], "updated_at": None}),
        "decisions": load_json(DATA / "tender_decisions.json", {"version": "1.0.0", "items": [], "updated_at": None}),
        "history": load_json(DATA / "tender_history.json", {"version": "1.0.0", "events": [], "updated_at": None}),
        "run_state": load_json(DATA / "run_state.json", {}),
    }


def select_discovery_queries(config: dict[str, Any]) -> list[dict[str, str]]:
    queries = []
    if config.get("search_strategy", {}).get("include_recent_pool"):
        queries.append({"cluster_id": "RECENT", "cluster_name": "Recent Goods Pool", "keyword": "__recent__"})
    for cluster in config.get("keyword_clusters", []):
        kws = cluster.get("keywords", [])
        if not kws:
            continue
        priority = cluster.get("priority", 3)
        # Agresif keşif: priority 1 → tüm keyword, priority 2 → 3-4, priority 3 → 2
        if priority == 1:
            take = len(kws)
        elif priority == 2:
            take = min(len(kws), 4)
        else:
            take = min(len(kws), 2)
        for kw in kws[:take]:
            queries.append({
                "cluster_id": cluster.get("id", "UNK"),
                "cluster_name": cluster.get("name", "Unnamed"),
                "keyword": kw,
            })
    return queries


def authority_points(authority_name: str, authority_cfg: dict[str, Any]) -> tuple[int, str, str | None]:
    n = normalize(authority_name)
    for entry in authority_cfg.get("blacklist", {}).get("authorities", []):
        if normalize(entry.get("name", "")) in n:
            return -15, "BLACKLIST", entry.get("name")
    tiers = authority_cfg.get("tiers", {})
    for tier_name in ("tier_1", "tier_2", "tier_3"):
        tier = tiers.get(tier_name, {})
        for entry in tier.get("authorities", []):
            name = normalize(entry.get("name", ""))
            pattern = entry.get("pattern")
            if name and name in n:
                return int(tier.get("boost_points", 0)), tier_name.upper(), entry.get("name")
            if pattern and re.search(pattern, n):
                return int(tier.get("boost_points", 0)), tier_name.upper(), entry.get("name")
    return 3, "UNKNOWN", None


def hard_reject(title: str, authority: str, config: dict[str, Any], authority_cfg: dict[str, Any]) -> tuple[bool, str | None]:
    text = normalize(title)
    for kw in config.get("hard_reject_keywords", []):
        if normalize(kw) in text:
            return True, f"hard keyword: {kw}"
    hard_stems = [
        "kent mobilya", "kent donati", "park mobilya", "bahce mobilya", "piknik",
        "kamelya", "oyun ekipman", "oyun parki", "cocuk oyun", "cop kovasi",
        "dis mekan", "outdoor", "park bank", "peyzaj",
    ]
    for stem in hard_stems:
        if stem in text:
            return True, f"hard stem: {stem}"
    auth_points, tier, matched = authority_points(authority, authority_cfg)
    if auth_points < 0:
        return True, f"authority blacklist: {matched or tier}"
    return False, None


def region_boost(province: str | None, config: dict[str, Any]) -> tuple[int, str]:
    """Bölge boost — eleme yok, sadece sıralama puanı."""
    if not province:
        return 0, "bilinmiyor"
    region_cfg = config.get("region_boost", {}).get("tiers", {})
    p = province.upper().strip()
    for region_name, region_data in region_cfg.items():
        if region_name == "diger":
            continue
        provinces = [prov.upper() for prov in region_data.get("provinces", [])]
        if p in provinces:
            return int(region_data.get("boost", 0)), region_name
    diger = region_cfg.get("diger", {})
    return int(diger.get("boost", 0)), "diger"


def signal_hits(text: str, signals: list[str]) -> list[str]:
    n = normalize(text)
    hits = [s for s in signals if normalize(s) in n]
    return unique_preserve(hits)


def quantity_score(text: str) -> tuple[int, str | None]:
    n = normalize(text)
    kalem = re.search(r"(\d{1,3})\s+kalem", n)
    adet = re.search(r"(\d{1,4})\s+adet", n)
    k = int(kalem.group(1)) if kalem else 0
    a = int(adet.group(1)) if adet else 0
    if k >= 20 or a >= 100:
        return 10, f"{k} kalem / {a} adet"
    if k >= 10 or a >= 20:
        return 7, f"{k} kalem / {a} adet"
    if k >= 5 or a >= 10:
        return 4, f"{k} kalem / {a} adet"
    return 3, None


def deadline_score(deadline_text: str | None) -> tuple[int, int | None]:
    d = days_until(deadline_text)
    if d is None:
        return 3, None
    if d < 0:
        return 0, d
    if d > 15:
        return 10, d
    if d >= 7:
        return 7, d
    if d >= 3:
        return 4, d
    return 1, d


def product_score(text: str) -> tuple[int, str]:
    n = normalize(text)
    core_terms = [
        "ofis mobilyasi", "ofis mobilyalari", "buro mobilyasi", "buro mobilyalari",
        "calisma masasi", "toplanti masasi", "yonetici masasi", "personel masasi",
        "dosya dolabi", "evrak dolabi", "arsiv dolabi", "keson", "ofis sandalyesi",
        "yonetici koltugu", "bekleme koltugu", "banko", "danisma bankosu", "panel bolme",
        "makam takimi", "ofis takimi", "mobilyalari",
    ]
    complement_terms = ["kitaplik", "raf sistemi", "seperator", "paravan", "oturma grubu", "resepsiyon"]
    core_hits = [t for t in core_terms if t in n]
    comp_hits = [t for t in complement_terms if t in n]
    if any(k in n for k in ["ofis mobilyasi", "buro mobilyasi"]) or len(core_hits) >= 2:
        return 34, ", ".join(core_hits[:4]) or "direct office furniture"
    if core_hits:
        return 28, ", ".join(core_hits[:4])
    if comp_hits:
        return 20, ", ".join(comp_hits[:4])
    if any(k in n for k in ["mobilya", "tefrisat", "mefrusat"]):
        return 15, "generic furniture/tefrişat"
    return 0, "no product fit"


def okas_score(detail: dict[str, Any], okas_cfg: dict[str, Any]) -> tuple[int, list[str]]:
    codes = [c.get("code") for c in detail.get("okas_codes", []) if c.get("code")]
    if not codes:
        return 0, []
    primary = okas_cfg.get("primary_codes", {})
    secondary = okas_cfg.get("secondary_codes", {})
    negative = okas_cfg.get("negative_codes", {})
    matched = []
    best = 0
    for code in codes:
        if code in negative and negative[code].get("action") == "hard_reject":
            return -10, [code]
        if code in primary:
            best = max(best, int(primary[code].get("score_boost", 0)))
            matched.append(code)
        elif code in secondary:
            best = max(best, math.floor(int(secondary[code].get("score_boost", 0)) * 0.75))
            matched.append(code)
    return min(best, 20), matched[:5]


def accessibility_score(detail: dict[str, Any], md: str) -> tuple[int, list[str]]:
    points = 0
    notes = []
    basic = detail.get("basic_info", {})
    rules = detail.get("process_rules", {})
    if basic.get("is_electronic") or rules.get("is_electronic"):
        points += 5
        notes.append("e-ihale")
    if basic.get("is_partial"):
        points += 3
        notes.append("kısmi teklif")
    if rules.get("can_submit_bid"):
        points += 1
        notes.append("katılıma açık")
    if rules.get("has_non_price_factors") is False:
        points += 2
        notes.append("fiyat dışı unsur yok")
    n = normalize(md)
    if "yerli istekli lehine fiyat avantaji" in n:
        points += 2
        notes.append("yerli avantajı")
    return min(points, 10), notes


def confidence_score(product: int, positive_hits: int, okas: int, detail_loaded: bool) -> float:
    score = 0.35
    score += min(product / 50.0, 0.35)
    score += min(positive_hits * 0.05, 0.15)
    score += min(okas / 50.0, 0.1)
    if detail_loaded:
        score += 0.1
    return round(min(score, 0.99), 2)


def classification(internal_score: int) -> str:
    if internal_score >= 85:
        return "ACTION"
    if internal_score >= 65:
        return "STRONG_CANDIDATE"
    if internal_score >= 40:
        return "WATCH"
    return "SILENT_REJECT"


def external_score(internal_score: int) -> float:
    return round(max(1.0, min(10.0, internal_score / 10.0)), 1)


def urgency_label(days_remaining: int | None, cls: str) -> str:
    if days_remaining is None:
        return "NORMAL"
    if days_remaining < 3 and cls in {"ACTION", "STRONG_CANDIDATE"}:
        return "CRITICAL"
    if days_remaining < 7 and cls in {"ACTION", "STRONG_CANDIDATE"}:
        return "HIGH"
    return "NORMAL" if cls != "SILENT_REJECT" else "LOW"


def tender_text_blob(tender: dict[str, Any], detail: dict[str, Any] | None, announcements: dict[str, Any] | None) -> str:
    parts = [
        tender.get("name", ""),
        tender.get("authority", ""),
        tender.get("province", ""),
    ]
    if detail:
        parts.append(json.dumps(detail.get("basic_info", {}), ensure_ascii=False))
        for item in detail.get("okas_codes", []):
            parts.append(item.get("full_description", ""))
    if announcements:
        for ann in announcements.get("announcements", []):
            parts.append(ann.get("markdown_content", ""))
    return "\n".join(parts)


def discover_candidates(cfg: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, int]], dict[str, list[str]]]:
    config = cfg["config"]
    queries = select_discovery_queries(config)
    cluster_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"searched": 0, "hits": 0})
    pool: dict[str, dict[str, Any]] = {}

    # OKAS validation / enrichment for core terms
    validated_okas = []
    for term in ["ofis mobilyası", "büro masası", "dosya dolabı"]:
        try:
            res = mcporter_call("search_okas_codes", {"search_term": term, "kalem_turu": 1, "limit": 5})
            validated_okas.extend([str(item.get("code")) for item in res.get("codes", []) if item.get("code")])
        except Exception:
            pass

    dynamic_okas = unique_preserve(config.get("okas_boost_codes", []) + validated_okas)

    # OKAS kod tabanlı keşif — keyword'e takılmayan ihaleleri yakalar
    okas_discovery = config.get("okas_discovery", {})
    if okas_discovery.get("enabled"):
        core_codes = okas_discovery.get("core_codes", [])
        for code in core_codes:
            cluster_stats["OKAS"]["searched"] += 1
            try:
                result = mcporter_call("search_tenders", {
                    "search_text": code,
                    "tender_types": [1],
                    "tender_date_filter": "from_today",
                    "order_by": "ihaleTarihi",
                    "sort_order": "asc",
                    "limit": config.get("search_strategy", {}).get("default_limit", 30),
                })
                okas_tenders = result.get("tenders", [])
                cluster_stats["OKAS"]["hits"] += len(okas_tenders)
                for tender in okas_tenders:
                    ikn = tender.get("ikn") or f"{normalize(tender.get('name'))}|{normalize(tender.get('authority'))}|{tender.get('tender_datetime','')}"
                    entry = pool.setdefault(ikn, {
                        "ikn": tender.get("ikn"),
                        "tender_id": tender.get("id"),
                        "title": tender.get("name"),
                        "authority": tender.get("authority"),
                        "province": tender.get("province"),
                        "deadline": tender.get("tender_datetime"),
                        "status": (tender.get("status") or {}).get("description"),
                        "document_count": tender.get("document_count"),
                        "matched_keywords": [],
                        "matched_clusters": [],
                        "raw": tender,
                    })
                    entry["matched_clusters"].append("OKAS")
                    entry["matched_keywords"].append(f"OKAS:{code}")
                    if not entry.get("tender_id") and tender.get("id"):
                        entry["tender_id"] = tender.get("id")
            except Exception:
                pass

    for q in queries:
        cid = q["cluster_id"]
        cluster_stats[cid]["searched"] += 1
        if q["keyword"] == "__recent__":
            result = mcporter_call("get_recent_tenders", {"days": 5, "tender_types": [1], "limit": 100})
            tenders = result.get("tenders", [])
        else:
            result = mcporter_call("search_tenders", {
                "search_text": q["keyword"],
                "tender_types": [1],
                "tender_date_filter": "from_today",
                "order_by": "ihaleTarihi",
                "sort_order": "asc",
                "limit": config.get("search_strategy", {}).get("default_limit", 30),
            })
            tenders = result.get("tenders", [])
        cluster_stats[cid]["hits"] += len(tenders)
        for tender in tenders:
            ikn = tender.get("ikn") or f"{normalize(tender.get('name'))}|{normalize(tender.get('authority'))}|{tender.get('tender_datetime','')}"
            entry = pool.setdefault(ikn, {
                "ikn": tender.get("ikn"),
                "tender_id": tender.get("id"),
                "title": tender.get("name"),
                "authority": tender.get("authority"),
                "province": tender.get("province"),
                "deadline": tender.get("tender_datetime"),
                "status": (tender.get("status") or {}).get("description"),
                "document_count": tender.get("document_count"),
                "matched_keywords": [],
                "matched_clusters": [],
                "raw": tender,
            })
            if q["keyword"] != "__recent__":
                entry["matched_keywords"].append(q["keyword"])
                entry["matched_clusters"].append(cid)
            if not entry.get("tender_id") and tender.get("id"):
                entry["tender_id"] = tender.get("id")
    return pool, cluster_stats, {"validated_okas": dynamic_okas}


def build_assessment(entry: dict[str, Any], cfg: dict[str, Any], okas_runtime: list[str], previous: dict[str, Any] | None) -> dict[str, Any]:
    config, authority_cfg, okas_cfg = cfg["config"], cfg["authority"], cfg["okas"]
    search_strategy = config.get("search_strategy", {})
    deadline_window_days = int(search_strategy.get("deadline_window_days", 21))
    title, authority = entry["title"], entry["authority"]

    reject, reason = hard_reject(title, authority, config, authority_cfg)
    if reject:
        return {
            "ikn": entry["ikn"], "title": title, "classification": "SILENT_REJECT", "internal_score": 0,
            "external_score": 1.0, "confidence": 0.95, "urgency": "LOW", "status_tag": "REJECTED",
            "reasons": [{"code": "HR_KEYWORD", "points": 0, "detail": reason}], "risk_flags": [],
            "matched_keywords": unique_preserve(entry.get("matched_keywords", [])), "matched_clusters": unique_preserve(entry.get("matched_clusters", [])),
            "province": entry.get("province"), "authority": authority, "deadline": entry.get("deadline"), "tender_id": entry.get("tender_id"),
            "detail_loaded": False,
        }

    base_text = title
    prod_points, prod_detail = product_score(base_text)
    pos_hits = signal_hits(base_text, cfg["positive"])
    pos_points = min(10, 2 + (len(pos_hits) - 1) * 2) if pos_hits else 0
    auth_points, auth_tier, auth_match = authority_points(authority, authority_cfg)
    dl_points, dleft = deadline_score(entry.get("deadline"))
    if dleft is not None and (dleft < 0 or dleft > deadline_window_days):
        return {
            "ikn": entry["ikn"], "title": title, "classification": "SILENT_REJECT", "internal_score": 0,
            "external_score": 1.0, "confidence": 0.9, "urgency": "LOW", "status_tag": "OUT_OF_WINDOW",
            "reasons": [{"code": "HR_WINDOW", "points": 0, "detail": f"days={dleft}, window={deadline_window_days}"}], "risk_flags": [],
            "matched_keywords": unique_preserve(entry.get("matched_keywords", [])), "matched_clusters": unique_preserve(entry.get("matched_clusters", [])),
            "province": entry.get("province"), "authority": authority, "deadline": entry.get("deadline"), "tender_id": entry.get("tender_id"),
            "detail_loaded": False,
        }
    soft_hits = signal_hits(base_text, config.get("soft_reject_keywords", []))
    soft_penalty = min(15, len(soft_hits) * 5)

    detail = None
    anns = None
    # Tüm non-reject ihaleler için detay çek — hiçbir fırsat kaçmasın
    should_enrich = not reject
    if should_enrich and entry.get("tender_id"):
        try:
            detail = mcporter_call("get_tender_details", {"tender_id": entry["tender_id"]}).get("tender_details", {})
        except Exception:
            detail = None
        try:
            anns = mcporter_call("get_tender_announcements", {"tender_id": entry["tender_id"]})
        except Exception:
            anns = None

    blob = tender_text_blob(entry, detail, anns)
    reject_after_detail, reject_reason_after_detail = hard_reject(blob, authority, config, authority_cfg)
    if reject_after_detail:
        return {
            "ikn": entry["ikn"], "title": title, "classification": "SILENT_REJECT", "internal_score": 0,
            "external_score": 1.0, "confidence": 0.98, "urgency": "LOW", "status_tag": "REJECTED",
            "reasons": [{"code": "HR_KEYWORD", "points": 0, "detail": reject_reason_after_detail}], "risk_flags": [],
            "matched_keywords": unique_preserve(entry.get("matched_keywords", [])), "matched_clusters": unique_preserve(entry.get("matched_clusters", [])),
            "province": entry.get("province"), "authority": authority, "deadline": entry.get("deadline"), "tender_id": entry.get("tender_id"),
            "detail_loaded": detail is not None,
        }
    prod_points, prod_detail = product_score(blob)
    pos_hits = signal_hits(blob, cfg["positive"])
    pos_points = min(10, 2 + (len(pos_hits) - 1) * 2) if pos_hits else 0
    soft_hits = signal_hits(blob, config.get("soft_reject_keywords", []))
    soft_penalty = min(15, len(soft_hits) * 5)
    qty_points, qty_detail = quantity_score(blob)
    ok_points, ok_codes = okas_score(detail or {}, okas_cfg)
    access_points, access_notes = accessibility_score(detail or {}, blob)
    reg_points, reg_name = region_boost(entry.get("province"), config)

    reasons = [
        {"code": "PR", "points": prod_points, "detail": prod_detail},
        {"code": "AQ", "points": max(auth_points, 0), "detail": auth_match or auth_tier},
        {"code": "DF", "points": dl_points, "detail": f"days={dleft}" if dleft is not None else "unknown"},
        {"code": "PS", "points": pos_points, "detail": ", ".join(pos_hits[:5]) if pos_hits else "none"},
        {"code": "TV", "points": qty_points, "detail": qty_detail or "unknown"},
        {"code": "OK", "points": ok_points, "detail": ", ".join(ok_codes[:5]) if ok_codes else "none"},
        {"code": "AC", "points": access_points, "detail": ", ".join(access_notes) if access_notes else "none"},
        {"code": "RG", "points": reg_points, "detail": f"{entry.get('province', '?')} ({reg_name})"},
    ]
    if soft_penalty:
        reasons.append({"code": "SR_KEYWORD", "points": -soft_penalty, "detail": ", ".join(soft_hits[:5])})

    internal = max(0, min(100, prod_points + max(auth_points, 0) + dl_points + pos_points + qty_points + ok_points + access_points + reg_points - soft_penalty))
    cls = classification(internal)
    ext = external_score(internal)
    conf = confidence_score(prod_points, len(pos_hits), max(ok_points, 0), detail is not None)
    urgency = urgency_label(dleft, cls)

    risk_flags = []
    if dleft is not None and dleft < 5:
        risk_flags.append("RF_TIGHT_DEADLINE")
    if conf < 0.6:
        risk_flags.append("RF_LOW_CONFIDENCE")
    if soft_hits:
        risk_flags.append("RF_MIXED_PROCUREMENT")
    if auth_tier == "UNKNOWN":
        risk_flags.append("RF_UNKNOWN_AUTHORITY")
    if ok_points < 0:
        cls = "SILENT_REJECT"
        internal = 0
        ext = 1.0
        risk_flags.append("RF_NEGATIVE_OKAS")

    status_tag = "NEW" if previous is None else "SEEN"
    if previous:
        prev_score = float(previous.get("latest_external_score", previous.get("external_score", 0)) or 0)
        prev_cls = previous.get("latest_classification", previous.get("classification"))
        if abs(ext - prev_score) >= 1.0 or prev_cls != cls:
            status_tag = "UPDATED"
        if dleft is not None and dleft <= 2:
            status_tag = "LAST_CALL"
    elif dleft is not None and dleft <= 2:
        status_tag = "LAST_CALL"

    return {
        "ikn": entry["ikn"], "title": title, "classification": cls, "internal_score": internal,
        "external_score": ext, "confidence": conf, "urgency": urgency, "status_tag": status_tag,
        "reasons": reasons, "risk_flags": risk_flags,
        "matched_keywords": unique_preserve(entry.get("matched_keywords", [])), "matched_clusters": unique_preserve(entry.get("matched_clusters", [])),
        "province": entry.get("province"), "authority": authority, "deadline": entry.get("deadline"), "tender_id": entry.get("tender_id"),
        "detail_loaded": detail is not None,
        "okas_codes": ok_codes,
        "access_notes": access_notes,
    }


def categorize_for_ai(results: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Categorize scored results into 3 tiers for the hybrid AI workflow."""
    tiers: dict[str, list[dict[str, Any]]] = {
        "certain_reject": [],
        "certain_good": [],
        "uncertain": [],
    }
    for item in results:
        cls = item.get("classification", "")
        score = item.get("internal_score", 0)
        conf = item.get("confidence", 0.0)

        if cls == "SILENT_REJECT" and score == 0:
            tiers["certain_reject"].append(item)
        elif score >= 75 and conf >= 0.8:
            tiers["certain_good"].append(item)
        else:
            tiers["uncertain"].append(item)
    return tiers


def _ai_review_reason(item: dict[str, Any]) -> str:
    """Determine why an item needs AI review."""
    conf = item.get("confidence", 0.0)
    score = item.get("internal_score", 0)
    cls = item.get("classification", "")

    if conf < 0.6:
        return "low confidence"
    if 1 <= score <= 50:
        return "borderline score"
    if cls in ("WATCH", "STRONG_CANDIDATE") and conf < 0.8:
        return "ambiguous product match"
    return "borderline score"


def suppress_repeat(assessment: dict[str, Any], previous: dict[str, Any] | None) -> bool:
    if not previous:
        return False
    if assessment["status_tag"] in {"UPDATED", "LAST_CALL"}:
        return False
    prev_cls = previous.get("latest_classification", previous.get("classification"))
    prev_score = float(previous.get("latest_external_score", previous.get("external_score", 0)) or 0)
    if prev_cls == assessment["classification"] and abs(prev_score - assessment["external_score"]) < 1.0:
        return True
    return False


def write_daily_report(results: list[dict[str, Any]], counts: dict[str, int], cluster_stats: dict[str, dict[str, int]]) -> Path:
    day = slug_date(NOW)
    path = REPORTS_DAILY / f"{day}.md"
    actionable_tags = {"NEW", "UPDATED", "LAST_CALL"}
    action = [r for r in results if r["classification"] == "ACTION" and r.get("status_tag") in actionable_tags]
    strong = [r for r in results if r["classification"] == "STRONG_CANDIDATE" and r.get("status_tag") in actionable_tags]
    watch = [r for r in results if r["classification"] == "WATCH" and r.get("status_tag") in actionable_tags]
    lines = [
        f"# Koç Büro Tender Radar — {day}",
        "",
        f"- Scan time: {NOW.strftime('%Y-%m-%d %H:%M %Z')}",
        f"- Scanned raw: {counts['scanned']}",
        f"- Unique: {counts['unique']}",
        f"- Hard rejected: {counts['hard_rejected']}",
        f"- Suppressed: {counts['suppressed']}",
        f"- ACTION: {counts['action']} | STRONG: {counts['strong_candidate']} | WATCH: {counts['watch']}",
        "",
        "## ACTION",
    ]
    if not action:
        lines += ["- No ACTION tenders today.", ""]
    for i, item in enumerate(action, 1):
        lines += [
            f"### {i}. [{item['external_score']}/10] {item['province']} — {item['authority']}",
            f"- **{item['title']}**",
            f"- IKN: `{item['ikn']}` | Deadline: {item['deadline']} | Tag: {item['status_tag']}",
            f"- Reasons: " + "; ".join([f"{r['code']}={r['points']} ({r['detail']})" for r in item['reasons'][:6]]),
            f"- Risks: {', '.join(item['risk_flags']) if item['risk_flags'] else 'None'}",
            "",
        ]
    lines += ["## STRONG_CANDIDATE", ""]
    if not strong:
        lines += ["- No STRONG_CANDIDATE tenders today.", ""]
    for item in strong:
        lines.append(f"- [{item['external_score']}/10] `{item['ikn']}` — {item['title']} — {item['authority']} — {item['deadline']} — {item['status_tag']}")
    lines += ["", "## WATCH", ""]
    if not watch:
        lines += ["- No WATCH tenders worth logging today.", ""]
    for item in watch[:15]:
        lines.append(f"- [{item['external_score']}/10] `{item['ikn']}` — {item['title']} — {item['authority']} — {item['deadline']}")
    lines += ["", "## Cluster Stats", ""]
    for cid, stats in sorted(cluster_stats.items()):
        lines.append(f"- {cid}: searched={stats.get('searched',0)} hits={stats.get('hits',0)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def telegram_summary(results: list[dict[str, Any]], counts: dict[str, int]) -> str:
    actionable_tags = {"NEW", "UPDATED", "LAST_CALL"}
    action = [r for r in results if r["classification"] == "ACTION" and r.get("status_tag") in actionable_tags]
    strong = [r for r in results if r["classification"] == "STRONG_CANDIDATE" and r.get("status_tag") in actionable_tags]
    watch = [r for r in results if r["classification"] == "WATCH" and r.get("status_tag") in actionable_tags]
    lines = [
        f"📋 KOÇ BÜRO — GÜNLÜK İHALE RAPORU",
        f"📅 Tarih: {slug_date(NOW)}",
        f"🔍 Taranan: {counts['scanned']} | Unique: {counts['unique']} | Öncelikli: {len(action) + len(strong)} | Baskılanan: {counts['suppressed']}",
        "",
        "━━━ AKSİYON / GÜÇLÜ ADAY ━━━",
    ]
    shown = action[:5] + strong[:5]
    if not shown:
        lines.append("Bugün yeni güçlü ihale yok.")
    for i, item in enumerate(shown, 1):
        why = ", ".join([r["detail"] for r in item["reasons"] if r["code"] in {"PR", "OK", "AC"} and r.get("detail") and r["detail"] != "none"][:2])
        risk = item["risk_flags"][0] if item["risk_flags"] else "düşük risk"
        lines += [
            f"{i}. [⭐{item['external_score']}/10] {item['province']} — {item['authority']}",
            f"   “{item['title']}”",
            f"   İKN: {item['ikn']} | Son teklif: {item['deadline']} | {item['status_tag']}",
            f"   Neden önemli: {why or 'ürün uyumu yüksek'}",
            f"   Risk: {risk}",
        ]
    if watch:
        lines += ["", "━━━ TAKİP ET ━━━"]
        for item in watch[:5]:
            lines.append(f"- [{item['external_score']}/10] {item['title']} — {item['authority']}")
    return "\n".join(lines)


def update_state(cfg: dict[str, Any], results: list[dict[str, Any]], counts: dict[str, int], report_path: Path) -> None:
    seen = cfg["seen"]
    decisions = cfg["decisions"]
    history = cfg["history"]
    run_state = cfg["run_state"]
    seen_map = {item.get("ikn") or item.get("title"): item for item in seen.get("items", [])}
    decision_map = {item.get("ikn") or item.get("title"): item for item in decisions.get("items", [])}
    now_iso = NOW.isoformat()

    for item in results:
        key = item.get("ikn") or item.get("title")
        prev = seen_map.get(key)
        record = {
            "ikn": item.get("ikn"),
            "title": item.get("title"),
            "authority": item.get("authority"),
            "province": item.get("province"),
            "first_seen_at": prev.get("first_seen_at") if prev else now_iso,
            "last_seen_at": now_iso,
            "latest_status": item.get("status_tag"),
            "latest_internal_score": item.get("internal_score"),
            "latest_external_score": item.get("external_score"),
            "latest_classification": item.get("classification"),
            "last_reported_at": now_iso if item.get("classification") != "SILENT_REJECT" else prev.get("last_reported_at") if prev else None,
            "matched_clusters": item.get("matched_clusters", []),
            "suppression_count": (prev.get("suppression_count", 0) if prev else 0) + (1 if item.get("suppressed") else 0),
        }
        seen_map[key] = record
        decision_map[key] = {
            "ikn": item.get("ikn"),
            "title": item.get("title"),
            "classification": item.get("classification"),
            "internal_score": item.get("internal_score"),
            "external_score": item.get("external_score"),
            "confidence": item.get("confidence"),
            "urgency": item.get("urgency"),
            "reasons": item.get("reasons", []),
            "risk_flags": item.get("risk_flags", []),
            "status_tag": item.get("status_tag"),
            "reported_today": item.get("classification") != "SILENT_REJECT" and not item.get("suppressed"),
            "matched_keywords": item.get("matched_keywords", []),
            "matched_clusters": item.get("matched_clusters", []),
            "deadline": item.get("deadline"),
            "province": item.get("province"),
            "authority": item.get("authority"),
            "notes": "auto-generated by tender runner",
        }
        history.setdefault("events", []).append({
            "timestamp": now_iso,
            "ikn": item.get("ikn"),
            "event_type": "reported" if not item.get("suppressed") else "suppressed",
            "summary": f"{item.get('classification')} {item.get('title')}",
        })

    seen["items"] = sorted(seen_map.values(), key=lambda x: (x.get("last_seen_at") or "", x.get("ikn") or ""), reverse=True)
    seen["updated_at"] = now_iso
    decisions["items"] = sorted(decision_map.values(), key=lambda x: (x.get("external_score", 0), x.get("ikn") or ""), reverse=True)
    decisions["updated_at"] = now_iso
    history["updated_at"] = now_iso
    run_state.update({
        "version": run_state.get("version", "1.0.0"),
        "description": run_state.get("description", "Run metadata for daily, delta, and weekly tender scans."),
        "last_daily_scan_at": now_iso,
        "last_successful_run_at": now_iso,
        "last_run_type": "daily",
        "last_report_path": str(report_path),
        "last_counts": counts,
        "updated_at": now_iso,
    })

    backup_file(DATA / "seen_tenders.json")
    backup_file(DATA / "tender_decisions.json")
    backup_file(DATA / "tender_history.json")
    backup_file(DATA / "run_state.json")
    backup_file(DATA / "score_history.jsonl")

    save_json(DATA / "seen_tenders.json", seen)
    save_json(DATA / "tender_decisions.json", decisions)
    save_json(DATA / "tender_history.json", history)
    save_json(DATA / "run_state.json", run_state)
    with (DATA / "score_history.jsonl").open("a", encoding="utf-8") as fh:
        for item in results:
            fh.write(json.dumps({
                "timestamp": now_iso,
                "ikn": item.get("ikn"),
                "classification": item.get("classification"),
                "internal_score": item.get("internal_score"),
                "external_score": item.get("external_score"),
                "suppressed": item.get("suppressed", False),
            }, ensure_ascii=False) + "\n")


def run_daily() -> str:
    cfg = read_core_config()
    previous_seen = {item.get("ikn") or item.get("title"): item for item in cfg["seen"].get("items", [])}
    pool, cluster_stats, meta = discover_candidates(cfg)
    results = []
    hard_rejected = 0
    suppressed = 0

    for item in pool.values():
        prev = previous_seen.get(item.get("ikn") or item.get("title"))
        assessment = build_assessment(item, cfg, meta.get("validated_okas", []), prev)
        assessment["title"] = item.get("title")
        if assessment["classification"] == "SILENT_REJECT" and assessment["internal_score"] == 0:
            hard_rejected += 1
        assessment["suppressed"] = suppress_repeat(assessment, prev)
        if assessment["suppressed"]:
            suppressed += 1
        results.append(assessment)

    # --- Hybrid AI triage layer ---
    ai_tiers = categorize_for_ai(results)
    for item in results:
        cls = item.get("classification", "")
        score = item.get("internal_score", 0)
        conf = item.get("confidence", 0.0)
        if cls == "SILENT_REJECT" and score == 0:
            item["ai_tier"] = "certain_reject"
        elif score >= 75 and conf >= 0.8:
            item["ai_tier"] = "certain_good"
        else:
            item["ai_tier"] = "uncertain"

    now_iso = NOW.isoformat()
    ai_queue_items = []
    for item in ai_tiers["uncertain"]:
        ai_queue_items.append({
            "ikn": item.get("ikn"),
            "title": item.get("title"),
            "authority": item.get("authority"),
            "province": item.get("province"),
            "deadline": item.get("deadline"),
            "tender_id": item.get("tender_id"),
            "current_score": item.get("internal_score", 0),
            "current_classification": item.get("classification", ""),
            "confidence": item.get("confidence", 0.0),
            "reasons": item.get("reasons", []),
            "risk_flags": item.get("risk_flags", []),
            "matched_keywords": item.get("matched_keywords", []),
            "detail_loaded": item.get("detail_loaded", False),
            "needs_ai_review": True,
            "ai_review_reason": _ai_review_reason(item),
        })
    ai_queue_payload = {
        "version": "1.0.0",
        "generated_at": now_iso,
        "run_type": "daily",
        "items": ai_queue_items,
        "stats": {
            "total": len(results),
            "certain_reject": len(ai_tiers["certain_reject"]),
            "certain_good": len(ai_tiers["certain_good"]),
            "uncertain": len(ai_tiers["uncertain"]),
        },
    }
    save_json(DATA / "ai_enrichment_queue.json", ai_queue_payload)
    print(f"AI Triage: {len(ai_tiers['certain_good'])} certain_good, {len(ai_tiers['uncertain'])} uncertain (queued for AI), {len(ai_tiers['certain_reject'])} certain_reject")

    unsuppressed = [r for r in results if not r["suppressed"] and r["classification"] != "SILENT_REJECT"]
    ranked = sorted(unsuppressed, key=lambda r: (r["internal_score"], r["confidence"]), reverse=True)
    counts = {
        "scanned": sum(stats.get("hits", 0) for stats in cluster_stats.values()),
        "unique": len(pool),
        "hard_rejected": hard_rejected,
        "action": sum(1 for r in ranked if r["classification"] == "ACTION"),
        "strong_candidate": sum(1 for r in ranked if r["classification"] == "STRONG_CANDIDATE"),
        "watch": sum(1 for r in ranked if r["classification"] == "WATCH"),
        "silent_reject": sum(1 for r in results if r["classification"] == "SILENT_REJECT"),
        "suppressed": suppressed,
    }
    report_path = write_daily_report(ranked, counts, cluster_stats)
    update_state(cfg, results, counts, report_path)
    return telegram_summary(ranked, counts)


def _load_score_history_week(days: int = 7) -> list[dict[str, Any]]:
    """Parse score_history.jsonl and return entries from the last *days* days."""
    path = DATA / "score_history.jsonl"
    if not path.exists():
        return []
    cutoff = NOW - timedelta(days=days)
    entries: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line == "init":
            continue
        try:
            rec = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        ts_str = rec.get("timestamp")
        if not ts_str:
            continue
        try:
            ts = datetime.fromisoformat(ts_str)
        except (ValueError, TypeError):
            continue
        if ts >= cutoff:
            entries.append(rec)
    return entries


def _load_score_history_prev_week() -> list[dict[str, Any]]:
    """Return score_history entries from 8-14 days ago (previous week)."""
    path = DATA / "score_history.jsonl"
    if not path.exists():
        return []
    cutoff_start = NOW - timedelta(days=14)
    cutoff_end = NOW - timedelta(days=7)
    entries: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line == "init":
            continue
        try:
            rec = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        ts_str = rec.get("timestamp")
        if not ts_str:
            continue
        try:
            ts = datetime.fromisoformat(ts_str)
        except (ValueError, TypeError):
            continue
        if cutoff_start <= ts < cutoff_end:
            entries.append(rec)
    return entries


def _week_classification_counts(entries: list[dict[str, Any]]) -> dict[str, int]:
    """Deduplicate by ikn (keep latest) and count by classification."""
    latest: dict[str, dict[str, Any]] = {}
    for e in entries:
        ikn = e.get("ikn")
        if not ikn:
            continue
        prev = latest.get(ikn)
        if prev is None or e.get("timestamp", "") >= prev.get("timestamp", ""):
            latest[ikn] = e
    counts: dict[str, int] = defaultdict(int)
    for rec in latest.values():
        counts[rec.get("classification", "UNKNOWN")] += 1
    return dict(counts)


def _delta_str(current: int, previous: int) -> str:
    diff = current - previous
    if diff > 0:
        return f"+{diff}"
    if diff < 0:
        return str(diff)
    return "0"


def run_weekly() -> str:
    cfg = read_core_config()
    config = cfg["config"]
    authority_cfg = cfg["authority"]
    okas_cfg = cfg["okas"]
    seen_items = cfg["seen"].get("items", [])
    decision_items = cfg["decisions"].get("items", [])
    history_events = cfg["history"].get("events", [])
    run_state = cfg["run_state"]

    week_number = NOW.strftime("%Y-[W]%V")
    week_end = NOW
    week_start = NOW - timedelta(days=7)
    week_start_str = slug_date(week_start)
    week_end_str = slug_date(week_end)

    # ── 1. Load score history for this week and previous week ──────────
    score_this_week = _load_score_history_week(7)
    score_prev_week = _load_score_history_prev_week()

    # Deduplicate by ikn — keep latest entry per ikn for this week
    this_week_latest: dict[str, dict[str, Any]] = {}
    for e in score_this_week:
        ikn = e.get("ikn")
        if not ikn:
            continue
        prev = this_week_latest.get(ikn)
        if prev is None or e.get("timestamp", "") >= prev.get("timestamp", ""):
            this_week_latest[ikn] = e

    total_scanned = len(score_this_week)
    new_unique = len(this_week_latest)
    cls_counts = _week_classification_counts(score_this_week)
    action_count = cls_counts.get("ACTION", 0)
    strong_count = cls_counts.get("STRONG_CANDIDATE", 0)
    watch_count = cls_counts.get("WATCH", 0)
    silent_count = cls_counts.get("SILENT_REJECT", 0)
    hard_rejected = sum(1 for e in this_week_latest.values() if e.get("internal_score", 0) == 0 and e.get("classification") == "SILENT_REJECT")
    suppressed_count = sum(1 for e in score_this_week if e.get("suppressed"))

    # Previous week counts for comparison
    prev_cls = _week_classification_counts(score_prev_week)
    prev_total = len(score_prev_week)
    prev_unique_map: dict[str, dict[str, Any]] = {}
    for e in score_prev_week:
        ikn = e.get("ikn")
        if ikn:
            prev_unique_map[ikn] = e
    prev_unique = len(prev_unique_map)
    prev_action = prev_cls.get("ACTION", 0)
    prev_strong = prev_cls.get("STRONG_CANDIDATE", 0)
    prev_watch = prev_cls.get("WATCH", 0)
    prev_silent = prev_cls.get("SILENT_REJECT", 0)
    prev_hard = sum(1 for e in prev_unique_map.values() if e.get("internal_score", 0) == 0 and e.get("classification") == "SILENT_REJECT")
    prev_suppressed = sum(1 for e in score_prev_week if e.get("suppressed"))
    has_prev = prev_total > 0

    # ── 2. Top Opportunities — ACTION + STRONG still active ───────────
    top_opportunities = []
    for item in decision_items:
        cls = item.get("classification")
        if cls not in {"ACTION", "STRONG_CANDIDATE"}:
            continue
        dl = days_until(item.get("deadline"))
        if dl is not None and dl < 0:
            continue  # deadline passed
        top_opportunities.append(item)

    # Sort by external_score descending
    top_opportunities.sort(key=lambda x: (x.get("external_score", 0), x.get("internal_score", 0)), reverse=True)
    top_opportunities = top_opportunities[:10]

    # ── 3. Cluster Effectiveness Analysis ─────────────────────────────
    # Build decision lookup by ikn
    decision_map: dict[str, dict[str, Any]] = {}
    for item in decision_items:
        ikn = item.get("ikn")
        if ikn:
            decision_map[ikn] = item

    # Also build seen lookup
    seen_map: dict[str, dict[str, Any]] = {}
    for item in seen_items:
        ikn = item.get("ikn")
        if ikn:
            seen_map[ikn] = item

    # Determine which ikns were seen this week
    this_week_ikns = set(this_week_latest.keys())

    # Cluster names from config
    cluster_name_map: dict[str, str] = {}
    for cluster in config.get("keyword_clusters", []):
        cid = cluster.get("id", "UNK")
        cluster_name_map[cid] = cluster.get("name", cid)
    cluster_name_map["OKAS"] = "OKAS Kod Keşfi"
    cluster_name_map["RECENT"] = "Son Eklenenler"

    # Map each ikn to its matched clusters
    ikn_clusters: dict[str, list[str]] = {}
    for ikn in this_week_ikns:
        seen_entry = seen_map.get(ikn)
        dec_entry = decision_map.get(ikn)
        clusters = []
        if dec_entry and dec_entry.get("matched_clusters"):
            clusters = dec_entry["matched_clusters"]
        elif seen_entry and seen_entry.get("matched_clusters"):
            clusters = seen_entry["matched_clusters"]
        ikn_clusters[ikn] = clusters

    # Compute cluster stats
    all_cluster_ids = sorted(set(cluster_name_map.keys()))
    cluster_effectiveness: list[dict[str, Any]] = []

    for cid in all_cluster_ids:
        # IKNs hit by this cluster this week
        cluster_ikns = {ikn for ikn, cl_list in ikn_clusters.items() if cid in cl_list}
        raw_hits = len(cluster_ikns)

        action_hits = 0
        strong_hits = 0
        for ikn in cluster_ikns:
            best_cls = this_week_latest.get(ikn, {}).get("classification", "")
            if best_cls == "ACTION":
                action_hits += 1
            elif best_cls == "STRONG_CANDIDATE":
                strong_hits += 1

        useful = action_hits + strong_hits
        hit_rate = round(useful / raw_hits * 100, 1) if raw_hits > 0 else 0.0

        # Unique contribution — found ONLY by this cluster
        unique_contribution = 0
        for ikn in cluster_ikns:
            clusters_for_ikn = ikn_clusters.get(ikn, [])
            if len(clusters_for_ikn) == 1 and clusters_for_ikn[0] == cid:
                unique_contribution += 1

        cluster_effectiveness.append({
            "cluster_id": cid,
            "name": cluster_name_map.get(cid, cid),
            "raw_hits": raw_hits,
            "action": action_hits,
            "strong": strong_hits,
            "hit_rate": hit_rate,
            "unique_contribution": unique_contribution,
        })

    # Sort by hit_rate descending, then by useful count
    cluster_effectiveness.sort(key=lambda x: (x["action"] + x["strong"], x["hit_rate"]), reverse=True)

    # Flag clusters with 0 useful results
    dormant_clusters: list[str] = []
    for ce in cluster_effectiveness:
        if ce["raw_hits"] == 0 or (ce["action"] + ce["strong"]) == 0:
            dormant_clusters.append(ce["cluster_id"])

    # ── 4. Authority Distribution ─────────────────────────────────────
    authority_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"count": 0, "total_score": 0.0, "tier": "UNKNOWN"})
    for ikn in this_week_ikns:
        dec = decision_map.get(ikn)
        if not dec:
            continue
        auth = dec.get("authority", "Bilinmiyor")
        score = float(dec.get("external_score", 0) or 0)
        # Determine tier
        auth_pts, tier, _matched = authority_points(auth, authority_cfg)
        authority_stats[auth]["count"] += 1
        authority_stats[auth]["total_score"] += score
        authority_stats[auth]["tier"] = tier

    # Compute averages and sort
    auth_summary: list[dict[str, Any]] = []
    for auth_name, stats in authority_stats.items():
        cnt = stats["count"]
        avg = round(stats["total_score"] / cnt, 1) if cnt > 0 else 0.0
        auth_summary.append({
            "authority": auth_name,
            "count": cnt,
            "avg_score": avg,
            "tier": stats["tier"],
        })
    auth_summary.sort(key=lambda x: x["avg_score"], reverse=True)

    # Authority tier aggregation
    tier_agg: dict[str, dict[str, Any]] = defaultdict(lambda: {"count": 0, "total_score": 0.0})
    for a in auth_summary:
        t = a["tier"]
        tier_agg[t]["count"] += a["count"]
        tier_agg[t]["total_score"] += a["avg_score"] * a["count"]

    tier_avg_lines: list[str] = []
    for t in ["TIER_1", "TIER_2", "TIER_3", "UNKNOWN"]:
        if t in tier_agg and tier_agg[t]["count"] > 0:
            avg = round(tier_agg[t]["total_score"] / tier_agg[t]["count"], 1)
            tier_avg_lines.append(f"| {t} | {tier_agg[t]['count']} | {avg}/10 |")

    # ── 5. OKAS Code Effectiveness ────────────────────────────────────
    okas_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"count": 0, "total_score": 0.0, "unique": 0})
    for ikn in this_week_ikns:
        dec = decision_map.get(ikn)
        if not dec:
            continue
        # Check reasons for OK (okas) points
        okas_codes_found: list[str] = []
        for reason in dec.get("reasons", []):
            if reason.get("code") == "OK" and reason.get("detail") and reason["detail"] != "none":
                okas_codes_found = [c.strip() for c in reason["detail"].split(",") if c.strip()]
                break
        if not okas_codes_found:
            continue
        score = float(dec.get("external_score", 0) or 0)
        clusters = ikn_clusters.get(ikn, [])
        is_okas_unique = "OKAS" in clusters and len(clusters) == 1
        for code in okas_codes_found:
            okas_stats[code]["count"] += 1
            okas_stats[code]["total_score"] += score
            if is_okas_unique:
                okas_stats[code]["unique"] += 1

    okas_summary: list[dict[str, Any]] = []
    okas_primary = okas_cfg.get("primary_codes", {})
    okas_secondary = okas_cfg.get("secondary_codes", {})
    for code, stats in okas_stats.items():
        desc = ""
        if code in okas_primary:
            desc = okas_primary[code].get("description_tr", "")
        elif code in okas_secondary:
            desc = okas_secondary[code].get("description_tr", "")
        avg = round(stats["total_score"] / stats["count"], 1) if stats["count"] > 0 else 0.0
        okas_summary.append({
            "code": code,
            "description": desc,
            "count": stats["count"],
            "avg_score": avg,
            "unique": stats["unique"],
        })
    okas_summary.sort(key=lambda x: x["avg_score"], reverse=True)

    # ── 6. Missed Opportunities Detection ─────────────────────────────
    missed: list[dict[str, Any]] = []
    for ikn in this_week_ikns:
        dec = decision_map.get(ikn)
        if not dec:
            continue
        cls = dec.get("classification", "")
        if cls not in {"WATCH", "SILENT_REJECT"}:
            continue
        internal = dec.get("internal_score", 0)
        if internal == 0:
            continue  # hard reject — skip

        miss_reason = None
        suggestion = None

        # Check: WATCH with generic title but positive OKAS codes
        if cls == "WATCH":
            okas_points = 0
            for reason in dec.get("reasons", []):
                if reason.get("code") == "OK":
                    okas_points = reason.get("points", 0)
                    break
            if okas_points >= 10:
                miss_reason = "WATCH ihale, OKAS kodu güçlü eşleşme gösteriyor"
                suggestion = "Detay incelenmeli — ürün uyumu OKAS'a göre yüksek"

        # Check: SILENT_REJECT where only reject reason was soft keywords
        if cls == "SILENT_REJECT" and internal > 0:
            has_hard = False
            has_soft = False
            for reason in dec.get("reasons", []):
                if reason.get("code") == "HR_KEYWORD":
                    has_hard = True
                if reason.get("code") == "SR_KEYWORD":
                    has_soft = True
            if has_soft and not has_hard:
                miss_reason = "Sadece soft keyword nedeniyle düşürülmüş — hard reject yok"
                suggestion = "Başlık detaylı incelenmeli, ürün uyumu olabilir"

        # Check: Tier 1 authorities that scored low
        if not miss_reason:
            auth = dec.get("authority", "")
            auth_pts, tier, _matched = authority_points(auth, authority_cfg)
            if tier == "TIER_1" and internal < 40:
                miss_reason = f"Tier 1 kurum ({auth[:40]}) ama düşük skor ({internal})"
                suggestion = "Kurumsal alım olabilir — başlık jenerik olsa bile incelenmeli"

        if miss_reason:
            missed.append({
                "ikn": ikn,
                "title": dec.get("title", ""),
                "authority": dec.get("authority", ""),
                "province": dec.get("province", ""),
                "external_score": dec.get("external_score", 0),
                "internal_score": internal,
                "classification": cls,
                "miss_reason": miss_reason,
                "suggestion": suggestion,
            })

    # Sort by internal_score descending, take top 5
    missed.sort(key=lambda x: x["internal_score"], reverse=True)
    missed = missed[:5]

    # ── 7. Upcoming Deadlines (Next 14 Days) ──────────────────────────
    upcoming: list[dict[str, Any]] = []
    for item in seen_items:
        cls = item.get("latest_classification", "")
        if cls == "SILENT_REJECT" and item.get("latest_internal_score", 0) == 0:
            continue
        dl = days_until(item.get("deadline") if "deadline" in item else None)
        # Try from decision_map
        ikn = item.get("ikn")
        dec = decision_map.get(ikn) if ikn else None
        deadline_str = None
        if dec and dec.get("deadline"):
            deadline_str = dec["deadline"]
            dl = days_until(deadline_str)
        if dl is None:
            continue
        if dl < 0 or dl > 14:
            continue
        urgency = "NORMAL"
        if dl <= 2:
            urgency = "KRITIK"
        elif dl <= 5:
            urgency = "YUKSEK"
        elif dl <= 7:
            urgency = "ORTA"

        upcoming.append({
            "ikn": ikn or "?",
            "title": item.get("title", ""),
            "deadline": deadline_str or "?",
            "days_remaining": dl,
            "external_score": item.get("latest_external_score", 0),
            "classification": cls,
            "urgency": urgency,
        })

    upcoming.sort(key=lambda x: x["days_remaining"])

    # ── 8. Auto Tuning Recommendations ────────────────────────────────
    tuning: list[str] = []

    # Dormant clusters
    for cid in dormant_clusters:
        cname = cluster_name_map.get(cid, cid)
        tuning.append(f"- {cid} ({cname}) bu hafta 0 ACTION/STRONG uretmis — etkisini degerlendirin")

    # Check specific clusters with 0 raw hits
    for ce in cluster_effectiveness:
        if ce["raw_hits"] == 0 and ce["cluster_id"] not in {"OKAS", "RECENT"}:
            cname = ce["name"]
            tuning.append(f"- {ce['cluster_id']} ({cname}) hic sonuc uretmedi — keyword'ler guncellenmeli")

    # Too many or too few ACTION tenders
    if action_count == 0 and strong_count == 0:
        tuning.append("- Bu hafta hic ACTION veya STRONG_CANDIDATE ihale bulunamadi — scoring esikleri dusurulebilir veya keyword'ler genisletilebilir")
    elif action_count > 10:
        tuning.append(f"- Bu hafta {action_count} ACTION ihale var — esikler biraz yukseltilerek kalite arttirilabilir")

    # Check if any keyword produced 0 results across all runs
    # (We can infer from cluster stats with 0 raw hits)
    for ce in cluster_effectiveness:
        if ce["raw_hits"] > 5 and ce["hit_rate"] == 0.0 and ce["cluster_id"] not in {"OKAS", "RECENT"}:
            tuning.append(f"- {ce['cluster_id']} ({ce['name']}) {ce['raw_hits']} ham sonuc ama 0 kaliteli — keyword'ler cok genel olabilir")

    # Suggest keeping effective clusters
    for ce in cluster_effectiveness:
        if ce["hit_rate"] > 30 and (ce["action"] + ce["strong"]) >= 2:
            tuning.append(f"- {ce['cluster_id']} ({ce['name']}) %{ce['hit_rate']} hit rate ile en verimli cluster — oncelik 1'de kalmali")

    if not tuning:
        tuning.append("- Sistem kararlı calisiyor, su an icin ayar onerisi yok")

    # ── GENERATE MARKDOWN REPORT ──────────────────────────────────────
    lines: list[str] = []

    # Header
    lines += [
        f"# Koc Buro Haftalik Ihale Raporu — {week_number}",
        "",
        f"**Olusturulma:** {NOW.strftime('%Y-%m-%d %H:%M %Z')} | **Hafta:** {week_number}",
        f"**Donem:** {week_start_str} — {week_end_str}",
        "",
        "---",
        "",
    ]

    # ── Section 1: Week at a Glance
    lines += [
        "## Haftaya Genel Bakis",
        "",
        "| Metrik | Bu Hafta | Onceki Hafta | Degisim |",
        "|---|---|---|---|",
        f"| Toplam taranan | {total_scanned} | {prev_total if has_prev else '-'} | {_delta_str(total_scanned, prev_total) if has_prev else '-'} |",
        f"| Yeni unique ihale | {new_unique} | {prev_unique if has_prev else '-'} | {_delta_str(new_unique, prev_unique) if has_prev else '-'} |",
        f"| ACTION | {action_count} | {prev_action if has_prev else '-'} | {_delta_str(action_count, prev_action) if has_prev else '-'} |",
        f"| STRONG_CANDIDATE | {strong_count} | {prev_strong if has_prev else '-'} | {_delta_str(strong_count, prev_strong) if has_prev else '-'} |",
        f"| WATCH | {watch_count} | {prev_watch if has_prev else '-'} | {_delta_str(watch_count, prev_watch) if has_prev else '-'} |",
        f"| SILENT_REJECT | {silent_count} | {prev_silent if has_prev else '-'} | {_delta_str(silent_count, prev_silent) if has_prev else '-'} |",
        f"| Hard rejected | {hard_rejected} | {prev_hard if has_prev else '-'} | {_delta_str(hard_rejected, prev_hard) if has_prev else '-'} |",
        f"| Baskilanan (dedup) | {suppressed_count} | {prev_suppressed if has_prev else '-'} | {_delta_str(suppressed_count, prev_suppressed) if has_prev else '-'} |",
        "",
        "---",
        "",
    ]

    # ── Section 2: Top Opportunities
    lines += [
        "## En Iyi Firsatlar (ACTION + STRONG)",
        "",
    ]
    if not top_opportunities:
        lines += ["Bu hafta aktif ACTION/STRONG ihale bulunmadi.", ""]
    for i, item in enumerate(top_opportunities, 1):
        dl = days_until(item.get("deadline"))
        dl_str = f"{dl} gun kaldi" if dl is not None else "tarih bilinmiyor"
        status = item.get("status_tag", "")
        last_call = " **SON GUN!**" if status == "LAST_CALL" else ""
        auth_pts, tier, _matched = authority_points(item.get("authority", ""), authority_cfg)
        lines += [
            f"### {i}. {item.get('title', '?')}",
            "",
            f"- **IKN:** `{item.get('ikn', '?')}` | **Skor:** {item.get('external_score', 0)}/10",
            f"- **Kurum:** {item.get('authority', '?')} ({tier})",
            f"- **Son Teklif:** {item.get('deadline', '?')} ({dl_str}){last_call}",
            f"- **Il:** {item.get('province', '?')} | **Durum:** {status}",
            "",
        ]
    lines += ["---", ""]

    # ── Section 3: Cluster Effectiveness
    lines += [
        "## Keyword Cluster Etkinligi",
        "",
        "| Cluster | Ad | Ham Hit | ACTION | STRONG | Hit Rate | Unique Katki |",
        "|---|---|---|---|---|---|---|",
    ]
    for ce in cluster_effectiveness:
        lines.append(
            f"| {ce['cluster_id']} | {ce['name']} | {ce['raw_hits']} | {ce['action']} | {ce['strong']} | %{ce['hit_rate']} | {ce['unique_contribution']} |"
        )
    lines += ["", "---", ""]

    # ── Section 4: Authority Distribution
    lines += [
        "## Kurum Dagilimi",
        "",
        "### Tier Bazli Ortalama",
        "",
        "| Tier | Ihale Sayisi | Ort. Skor |",
        "|---|---|---|",
    ]
    lines += tier_avg_lines if tier_avg_lines else ["| - | - | - |"]
    lines += [
        "",
        "### En Yuksek Skorlu Kurumlar (Top 5)",
        "",
        "| Kurum | Ihale Sayisi | Ort. Skor | Tier |",
        "|---|---|---|---|",
    ]
    for a in auth_summary[:5]:
        lines.append(f"| {a['authority'][:60]} | {a['count']} | {a['avg_score']}/10 | {a['tier']} |")
    lines += ["", "---", ""]

    # ── Section 5: OKAS Code Effectiveness
    lines += [
        "## OKAS Kod Etkinligi",
        "",
    ]
    if okas_summary:
        lines += [
            "| OKAS Kodu | Aciklama | Bulunan | Ort. Skor | Unique |",
            "|---|---|---|---|---|",
        ]
        for ok in okas_summary[:10]:
            lines.append(f"| {ok['code']} | {ok['description'][:40]} | {ok['count']} | {ok['avg_score']}/10 | {ok['unique']} |")
    else:
        lines.append("Bu hafta OKAS kodu esleyen ihale bulunmadi.")
    lines += ["", "---", ""]

    # ── Section 6: Missed Opportunities
    lines += [
        "## Kacirilan Firsatlar",
        "",
        "WATCH veya SILENT_REJECT olarak siniflandirilmis ama yeniden degerlendirme hak edebilecek ihaleler:",
        "",
    ]
    if not missed:
        lines += ["Bu hafta potansiyel kacirilan firsat tespit edilmedi.", ""]
    for i, m in enumerate(missed, 1):
        lines += [
            f"### {i}. {m.get('title', '?')}",
            "",
            f"- **IKN:** `{m.get('ikn', '?')}` | **Skor:** {m.get('external_score', 0)}/10 | **Sinif:** {m.get('classification', '?')}",
            f"- **Kurum:** {m.get('authority', '?')} | **Il:** {m.get('province', '?')}",
            f"- **Neden isaretlendi:** {m.get('miss_reason', '-')}",
            f"- **Oneri:** {m.get('suggestion', '-')}",
            "",
        ]
    lines += ["---", ""]

    # ── Section 7: Upcoming Deadlines
    lines += [
        "## Yaklasan Son Tarihler (14 Gun)",
        "",
    ]
    if not upcoming:
        lines += ["Onumuzdeki 14 gun icinde son tarihi olan aktif ihale yok.", ""]
    else:
        lines += [
            "| IKN | Ihale | Son Tarih | Kalan | Skor | Aciliyet |",
            "|---|---|---|---|---|---|",
        ]
        for u in upcoming:
            lines.append(
                f"| `{u['ikn']}` | {u['title'][:50]} | {u['deadline']} | {u['days_remaining']}g | {u['external_score']}/10 | {u['urgency']} |"
            )
    lines += ["", "---", ""]

    # ── Section 8: Tuning Suggestions
    lines += [
        "## Oto Ayar Onerileri",
        "",
    ]
    lines += tuning
    lines += [
        "",
        "---",
        "",
        f"*OpenClaw Tender Scanner tarafindan olusturuldu — Haftalik Inceleme — {NOW.strftime('%Y-%m-%d %H:%M %Z')}*",
    ]

    # ── State Summary
    lines_state = [
        "",
        "## Durum Ozeti",
        "",
        f"- **seen_tenders.json:** {len(seen_items)} kayit",
        f"- **tender_decisions.json:** {len(decision_items)} karar",
        f"- **tender_history.json:** {len(history_events)} olay",
    ]

    # Count daily scans this week
    daily_reports = list(REPORTS_DAILY.glob("*.md"))
    daily_this_week = []
    for rp in daily_reports:
        stem = rp.stem
        if stem.startswith("."):
            continue
        try:
            rd = datetime.strptime(stem, "%Y-%m-%d")
            if TZ:
                rd = rd.replace(tzinfo=TZ)
            if rd >= week_start:
                daily_this_week.append(stem)
        except ValueError:
            # might be smoke test etc
            pass
    lines_state.append(f"- **Gunluk taramalar:** {len(daily_this_week)}/7")

    # Insert state before tuning section
    # Find the index of "## Oto Ayar Onerileri"
    tuning_idx = None
    for idx, ln in enumerate(lines):
        if ln == "## Oto Ayar Onerileri":
            tuning_idx = idx
            break
    if tuning_idx is not None:
        for j, sl in enumerate(lines_state):
            lines.insert(tuning_idx + j, sl)
        lines.insert(tuning_idx + len(lines_state), "")
        lines.insert(tuning_idx + len(lines_state) + 1, "---")
        lines.insert(tuning_idx + len(lines_state) + 2, "")

    # ── Write report ──────────────────────────────────────────────────
    report_path = REPORTS_WEEKLY / f"{week_number}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ── Update run_state ──────────────────────────────────────────────
    run_state.update({
        "last_weekly_summary_at": NOW.isoformat(),
        "last_successful_run_at": NOW.isoformat(),
        "last_run_type": "weekly",
        "last_weekly_report_path": str(report_path),
        "updated_at": NOW.isoformat(),
    })
    backup_file(DATA / "run_state.json")
    save_json(DATA / "run_state.json", run_state)

    # ── Build Telegram Summary ────────────────────────────────────────
    tg_lines = [
        f"📊 KOÇ BÜRO — HAFTALIK ÖZET",
        f"Hafta: {week_number} | Taranan: {total_scanned} | Yeni: {new_unique} | Aksiyon: {action_count + strong_count}",
        "━━━ EN İYİ FIRSATLAR ━━━",
    ]
    if not top_opportunities:
        tg_lines.append("Bu hafta aktif güçlü fırsat yok.")
    for i, item in enumerate(top_opportunities[:5], 1):
        dl = days_until(item.get("deadline"))
        dl_str = f"{dl} gün" if dl is not None else "?"
        tg_lines.append(
            f"{i}. [{item.get('external_score', 0)}/10] {item.get('province', '?')} — {item.get('authority', '?')[:30]} — {item.get('title', '?')[:40]} — {dl_str}"
        )

    tg_lines += ["━━━ CLUSTER ETKİNLİĞİ ━━━"]
    # Best cluster
    effective = [ce for ce in cluster_effectiveness if ce["action"] + ce["strong"] > 0]
    if effective:
        best = effective[0]
        tg_lines.append(f"En verimli: {best['cluster_id']} ({best['name']}) %{best['hit_rate']} hit rate")
    # Worst cluster
    dormant_named = [f"{cid} ({cluster_name_map.get(cid, cid)})" for cid in dormant_clusters if cid not in {"OKAS", "RECENT"}]
    if dormant_named:
        tg_lines.append(f"Verimsiz: {', '.join(dormant_named[:3])}")

    tg_lines += ["━━━ ÖNERİLER ━━━"]
    for t in tuning[:4]:
        tg_lines.append(t)

    return "\n".join(tg_lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["daily", "weekly"], default="daily")
    args = parser.parse_args()
    try:
        summary = run_daily() if args.mode == "daily" else run_weekly()
        print(summary)
        return 0
    except Exception as exc:
        print(f"Tender runner failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
