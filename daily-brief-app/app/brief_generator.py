"""Generate daily-brief.md, HTML, Word and secondary outputs from selection."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.brief_exports import write_word_brief
from app.candidates import load_selection, parse_report_key, selection_to_articles, _out_dir
from app.media import capture_media_for_article
from app.models import DailyReport, ScoredArticle
from app.scoring import WEEKDAYS, catalog_summary_from_body, extract_body_paragraphs

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def _guess_source_id(url: str) -> str:
    low = url.lower()
    if "hket.com" in low or "ps.hket.com" in low:
        return "hket"
    if "hkej.com" in low:
        return "hkej"
    if "mingpao.com" in low:
        return "mingpao"
    if "wenweipo.com" in low:
        return "wenweipo"
    return "hket"


def _prepare_item_body(item: ScoredArticle) -> None:
    """Attach verbatim body paragraphs; no LLM rewriting."""
    text = (item.body or "").strip()
    if not text and item.paragraphs:
        text = "\n\n".join(item.paragraphs)
    item.body = text
    item.body_paragraphs = extract_body_paragraphs(text)
    if not item.body_paragraphs and item.paragraphs:
        item.body_paragraphs = list(item.paragraphs)
    item.catalog_summary = catalog_summary_from_body(
        text,
        title=item.title,
    )


def _parse_iso_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _item_dateline(item: ScoredArticle, fallback: date) -> str:
    pub = _parse_iso_date(item.publish_date) or fallback
    return f"【本報{pub.month}月{pub.day}日消息】"


def _format_date_label(date_start: date, date_end: date) -> str:
    if date_start == date_end:
        weekday = WEEKDAYS[date_end.weekday()]
        return f"{date_end.year}年{date_end.month}月{date_end.day}日 {weekday}"
    if date_start.year == date_end.year and date_start.month == date_end.month:
        return (
            f"{date_start.year}年{date_start.month}月{date_start.day}日"
            f"–{date_end.day}日"
        )
    return (
        f"{date_start.year}年{date_start.month}月{date_start.day}日"
        f"–{date_end.year}年{date_end.month}月{date_end.day}日"
    )


async def generate_brief_from_selection(
    report_date: date | None = None,
    date_end: date | None = None,
) -> Path:
    date_end = date_end or report_date or date.today()
    date_start = report_date or date_end
    if date_start > date_end:
        date_start, date_end = date_end, date_start

    selection = load_selection(date_start, date_end)
    if not selection or not selection.get("sections"):
        key = f"{date_start.isoformat()}_{date_end.isoformat()}" if date_start != date_end else date_end.isoformat()
        raise ValueError(f"无 selection.json，请先在候选池审核并保存：{key}")

    out_dir = _out_dir(date_start, date_end)
    sections = selection_to_articles(selection)

    for items in sections.values():
        for i, item in enumerate(items):
            item.sort_order = i
            item.original_url = item.original_url or item.url
            _prepare_item_body(item)

            sid = item.source_id or _guess_source_id(item.original_url)
            img, shot = await capture_media_for_article(
                item.original_url,
                item.news_id,
                sid,
                out_dir,
            )
            item.image_asset = img
            item.screenshot_path = shot
            item.selected = True

    date_label = _format_date_label(date_start, date_end)
    all_items = [a for sec in sections.values() for a in sec]
    headline = "；".join(a.title[:30] for a in all_items[:2]) or "香港宏觀及地產要聞更新"
    monthly = [a for a in all_items if a.monthly_candidate]

    report = DailyReport(
        date=date_end.isoformat(),
        date_start=date_start.isoformat(),
        date_end=date_end.isoformat(),
        weekday_label=date_label,
        headline=headline,
        sections=sections,
        monthly_candidates=monthly,
        meta={
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "item_count": len(all_items),
            "date_range": date_start.isoformat() != date_end.isoformat(),
        },
    )

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.globals["item_dateline"] = lambda item: _item_dateline(item, date_end)

    md = env.get_template("daily-brief.md.j2").render(report=report)
    (out_dir / "daily-brief.md").write_text(md, encoding="utf-8")

    html = env.get_template("daily-brief.html.j2").render(report=report)
    (out_dir / "daily-brief.html").write_text(html, encoding="utf-8")

    write_word_brief(report, out_dir / "daily-brief.docx", date_end=date_end)

    feishu = env.get_template("feishu.txt").render(report=report)
    (out_dir / "feishu.txt").write_text(feishu, encoding="utf-8")

    monthly_md = env.get_template("monthly.md").render(report=report)
    (out_dir / "monthly.md").write_text(monthly_md, encoding="utf-8")

    (out_dir / "report.json").write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return out_dir


async def generate_brief_from_report_key(report_key: str) -> Path:
    date_start, date_end = parse_report_key(report_key)
    return await generate_brief_from_selection(date_start, date_end)
