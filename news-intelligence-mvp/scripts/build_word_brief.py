#!/usr/bin/env python3
"""Build daily-leadership-brief.docx from articles.json using brief-template.docx."""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_ROOT = ROOT.parent / "daily-brief-app"
sys.path.insert(0, str(APP_ROOT))

from app.brief_exports import write_word_brief  # noqa: E402
from app.models import DailyReport, ScoredArticle  # noqa: E402
from app.scoring import catalog_summary_from_body, extract_body_paragraphs  # noqa: E402

TEMPLATE = APP_ROOT / "templates" / "brief-template.docx"
DEFAULT_OUT = ROOT / "output" / "2026-06-13_2026-06-15"


def _parse_pub_label(pub_label: str, default_year: int = 2026) -> str:
    m = re.search(r"(\d{1,2})月(\d{1,2})日", pub_label)
    if not m:
        return ""
    month, day = int(m.group(1)), int(m.group(2))
    return date(default_year, month, day).isoformat()


def _article_to_scored(raw: dict, sort_order: int) -> ScoredArticle:
    body = (raw.get("text") or "").strip()
    paragraphs = extract_body_paragraphs(body)
    publish_date = _parse_pub_label(raw.get("pub_label", ""))
    return ScoredArticle(
        news_id=raw["id"],
        title=raw["title"],
        url="",
        original_url="",
        source_name=raw["source"],
        digest_section="",
        catalog_summary=catalog_summary_from_body(body, title=raw["title"]),
        paragraphs=paragraphs,
        topic_tags=[],
        importance_score=0,
        relevance_score=0,
        actionability_score=0,
        credibility_score=0,
        total_score=0.0,
        business_implication="",
        selected=True,
        sort_order=sort_order,
        publish_date=publish_date,
        body=body,
        body_paragraphs=paragraphs,
    )


def build_report(data: dict) -> DailyReport:
    meta = data["meta"]
    by_id = {a["id"]: a for a in data["articles"]}
    sections: dict[str, list[ScoredArticle]] = {}
    sort_order = 1
    for section_name, items in meta["sections"].items():
        section_articles: list[ScoredArticle] = []
        for item in items:
            raw = by_id[item["id"]]
            section_articles.append(_article_to_scored(raw, sort_order))
            sort_order += 1
        sections[section_name] = section_articles

    return DailyReport(
        date="2026-06-15",
        date_start="2026-06-13",
        date_end="2026-06-15",
        weekday_label=meta["date_range"],
        headline="",
        sections=sections,
    )


def main() -> None:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    articles_path = out_dir / "articles.json"
    if not articles_path.exists():
        raise SystemExit(f"Missing {articles_path}")

    if not TEMPLATE.exists():
        raise SystemExit(f"Word template not found: {TEMPLATE}")

    data = json.loads(articles_path.read_text(encoding="utf-8"))
    report = build_report(data)
    out_path = out_dir / "daily-leadership-brief.docx"
    write_word_brief(report, out_path, date_end=date(2026, 6, 15))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
