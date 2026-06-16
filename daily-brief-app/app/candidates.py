"""Candidate pool: fetch, score, persist, selection."""



from __future__ import annotations



import json

import re

from datetime import date, datetime

from pathlib import Path



from app.fetchers import fetch_all_sources, load_sources_config

from app import progress as job_progress

from app.models import ScoredArticle

from app.scoring import load_keywords_config, score_article



OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "output"



SECTIONS = ["金融與經濟", "建築與地產", "北都專題"]





def _normalize_range(

    date_start: date | None, date_end: date | None

) -> tuple[date, date]:

    date_end = date_end or date.today()

    date_start = date_start or date_end

    if date_start > date_end:

        date_start, date_end = date_end, date_start

    return date_start, date_end





def report_key(date_start: date, date_end: date) -> str:

    """Directory name for output: single day or date range."""

    if date_start == date_end:

        return date_end.isoformat()

    return f"{date_start.isoformat()}_{date_end.isoformat()}"





def _out_dir(date_start: date, date_end: date | None = None) -> Path:

    date_end = date_end or date_start

    key = report_key(date_start, date_end)

    d = OUTPUT_DIR / key

    d.mkdir(parents=True, exist_ok=True)

    return d





def _candidates_path(date_start: date, date_end: date | None = None) -> Path:

    date_end = date_end or date_start

    return _out_dir(date_start, date_end) / "candidates.json"





def _selection_path(date_start: date, date_end: date | None = None) -> Path:

    date_end = date_end or date_start

    return _out_dir(date_start, date_end) / "selection.json"





def _normalize_title(title: str) -> str:

    return re.sub(r"\s+", "", (title or "").lower())





def _normalize_url(url: str) -> str:

    return (url or "").split("?")[0].rstrip("/").lower()





def _dedupe_scored(scored: list[ScoredArticle]) -> list[ScoredArticle]:

    """Keep highest-scoring article per URL or near-duplicate title."""

    ranked = sorted(scored, key=lambda x: x.total_score, reverse=True)

    seen_urls: set[str] = set()

    seen_titles: set[str] = set()

    result: list[ScoredArticle] = []

    for item in ranked:

        url_key = _normalize_url(item.url)

        title_key = _normalize_title(item.title)

        if url_key in seen_urls or title_key in seen_titles:

            continue

        seen_urls.add(url_key)

        seen_titles.add(title_key)

        result.append(item)

    return result





def _assign_news_ids(scored: list[ScoredArticle], report_date: date) -> None:

    prefix = report_date.strftime("%Y%m%d")

    for i, item in enumerate(scored, start=1):

        if not item.news_id:

            item.news_id = f"{prefix}-{i:03d}"





async def fetch_and_score_candidates(

    date_start: date | None = None,

    date_end: date | None = None,

) -> dict:

    date_start, date_end = _normalize_range(date_start, date_end)

    kw_cfg = load_keywords_config()

    cfg = load_sources_config()

    pool_size = int(cfg.get("candidate_pool_size", 20))

    selection_cfg = cfg.get("selection", {})

    min_score = float(selection_cfg.get("min_total_score", 70))



    raw_list = await fetch_all_sources(date_start, date_end)

    job_progress.update(93, "評分候選", f"共 {len(raw_list)} 篇")

    scored: list[ScoredArticle] = []

    for raw in raw_list:

        s = score_article(raw, raw.section_type, kw_cfg)

        if s.digest_section != "剔除" and s.total_score >= min_score:

            scored.append(s)



    scored = _dedupe_scored(scored)

    _assign_news_ids(scored, date_end)



    digest_by_source: dict[str, dict[str, int]] = {}

    for s in scored:

        digest_by_source.setdefault(s.source_id, {})

        sec = s.digest_section

        digest_by_source[s.source_id][sec] = digest_by_source[s.source_id].get(sec, 0) + 1



    by_section: dict[str, list[dict]] = {sec: [] for sec in SECTIONS}

    for sec in SECTIONS:

        pool = [s for s in scored if s.digest_section == sec]

        pool.sort(key=lambda x: x.total_score, reverse=True)

        by_section[sec] = [s.to_dict() for s in pool[:pool_size]]



    job_progress.update(95, "寫入候選池", "")

    payload = {

        "date": date_end.isoformat(),

        "date_start": date_start.isoformat(),

        "date_end": date_end.isoformat(),

        "report_key": report_key(date_start, date_end),

        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),

        "raw_count": len(raw_list),

        "scored_count": len(scored),

        "pool_size": pool_size,

        "min_total_score": min_score,

        "sections": by_section,

        "section_counts": {sec: len(by_section[sec]) for sec in SECTIONS},

        "source_breakdown": digest_by_source,

        "quotas": cfg.get("quotas", {}),

        "selection": selection_cfg,

    }

    _candidates_path(date_start, date_end).write_text(

        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"

    )

    job_progress.update(100, "完成", "候選已保存")

    return payload





def load_candidates(report_date: date, date_end: date | None = None) -> dict | None:

    path = _candidates_path(report_date, date_end or report_date)

    if not path.exists():

        return None

    return json.loads(path.read_text(encoding="utf-8"))





def load_selection(report_date: date, date_end: date | None = None) -> dict | None:

    path = _selection_path(report_date, date_end or report_date)

    if not path.exists():

        return None

    return json.loads(path.read_text(encoding="utf-8"))





def save_selection(

    date_start: date,

    date_end: date | None,

    body: dict,

) -> Path:

    date_end = date_end or date_start

    body["date"] = date_end.isoformat()

    body["date_start"] = date_start.isoformat()

    body["date_end"] = date_end.isoformat()

    body["report_key"] = report_key(date_start, date_end)

    body["saved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    path = _selection_path(date_start, date_end)

    path.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")

    return path





def selection_to_articles(selection: dict) -> dict[str, list[ScoredArticle]]:

    result: dict[str, list[ScoredArticle]] = {}

    for sec, items in selection.get("sections", {}).items():

        arts = []

        for item in sorted(items, key=lambda x: x.get("sort_order", 0)):

            arts.append(ScoredArticle.from_dict(item))

        result[sec] = arts

    return result





def parse_report_key(key: str) -> tuple[date, date]:

    """Parse output directory name into (start, end)."""

    if "_" in key:

        a, b = key.split("_", 1)

        return date.fromisoformat(a), date.fromisoformat(b)

    d = date.fromisoformat(key)

    return d, d


