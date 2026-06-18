#!/usr/bin/env python3
"""Build mobile-friendly leadership slide deck from articles.json."""

from __future__ import annotations

import html
import json
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SLIDES_DIR = REPO_ROOT / "docs" / "brief" / "slides"
DEFAULT_BASE = Path(__file__).resolve().parent.parent / "output" / "2026-06-13_2026-06-15"

SECTION_ORDER = ("【金融與經濟】", "【建築與地產】", "【北都專題】")
MOBILE_BODY_CHAR_LIMIT = 1100

REMOVE_REF_MARKERS = re.compile(
    r"【詳見另文】|【詳見另稿】|（詳見另文）|（詳見另稿）|【詳見下表】"
)
TABLE_MARKERS = re.compile(r"【見表】|（部分見表）|（見表）")
IMAGE_CAPTION_END = re.compile(r"（[^）]*(攝|資料圖片|圖片)）$")


def clean_para(text: str) -> str:
    text = REMOVE_REF_MARKERS.sub("", text)
    text = TABLE_MARKERS.sub("", text)
    return text.strip()


def is_subhead(para: str) -> bool:
    if len(para) > 40:
        return False
    if para.startswith("▲"):
        return False
    if para.endswith("。"):
        return False
    return True


def is_image_caption_paragraph(para: str) -> bool:
    para = para.strip()
    if para.startswith("▲"):
        return True
    return bool(IMAGE_CAPTION_END.search(para))


def body_paragraphs(text: str) -> list[str]:
    parts = [clean_para(p) for p in text.split("\n\n")]
    return [p for p in parts if p and not is_image_caption_paragraph(p)]


def paragraph_html(para: str) -> str:
    if is_subhead(para):
        return f'<p class="subhead"><strong>{html.escape(para)}</strong></p>'
    return f"<p>{html.escape(para)}</p>"


def chunk_paragraphs(paragraphs: list[str], max_chars: int = MOBILE_BODY_CHAR_LIMIT) -> list[list[str]]:
    if not paragraphs:
        return [[]]
    chunks: list[list[str]] = []
    current: list[str] = []
    current_len = 0
    for para in paragraphs:
        para_len = len(para)
        if current and current_len + para_len > max_chars:
            chunks.append(current)
            current = [para]
            current_len = para_len
        else:
            current.append(para)
            current_len += para_len
    if current:
        chunks.append(current)
    return chunks


def chunks_to_html(chunks: list[list[str]]) -> list[str]:
    return ["\n".join(paragraph_html(p) for p in group) for group in chunks]


def article_body_html(art: dict) -> str:
    return chunks_to_html([body_paragraphs(art["text"])])[0]


def article_body_chunks(art: dict) -> list[str]:
    return chunks_to_html(chunk_paragraphs(body_paragraphs(art["text"])))


def slide_footer(current: int, total: int, label: str = "香港簡訊") -> str:
    return (
        f'<div class="deck-footer">'
        f"<span>{html.escape(label)}</span>"
        f'<span class="slide-number" data-current="{current}" data-total="{total}"></span>'
        f"</div>"
    )


DECK_BRAND = """    <header class="slide-brand" aria-label="頁首標誌">
      <div class="brand-slot brand-logo-wrap">
        <img src="assets/cscec-hk-logo.png" alt="中國建築工程(香港)有限公司" class="brand-logo">
      </div>
      <div class="brand-slot brand-daily"><span>香港市場動態日報</span></div>
    </header>"""


def build_slide_plan(meta: dict, articles: list[dict]) -> tuple[list[dict], list[tuple[str, list[dict]]]]:
    by_id = {a["id"]: a for a in articles}
    section_plan: list[tuple[str, list[dict]]] = []
    for section in SECTION_ORDER:
        items = meta["sections"].get(section, [])
        if items:
            section_plan.append((section, [by_id[i["id"]] for i in items]))

    plan: list[dict] = [{"type": "cover"}]
    article_goto: dict[str, int] = {}

    for section, items in section_plan:
        plan.append({"type": "section", "section": section, "count": len(items)})
        for i, art in enumerate(items, 1):
            chunks = article_body_chunks(art)
            for part_idx, body_html in enumerate(chunks, 1):
                if part_idx == 1:
                    article_goto[art["id"]] = len(plan)
                plan.append(
                    {
                        "type": "article",
                        "art": art,
                        "section": section,
                        "index": i,
                        "section_count": len(items),
                        "part": part_idx,
                        "part_total": len(chunks),
                        "body_html": body_html,
                    }
                )

    plan.append({"type": "end"})
    return plan, section_plan


def sync_slide_static_files(dest_slides_dir: Path) -> None:
    """Copy CSS/JS/assets from docs template; skip generated index.html."""
    dest_slides_dir.mkdir(parents=True, exist_ok=True)
    for item in SLIDES_DIR.iterdir():
        if item.name == "index.html":
            continue
        # Only copy the slide runtime assets (avoid recursively copying dated decks).
        if item.is_dir() and item.name != "assets":
            continue
        dest = dest_slides_dir / item.name
        if item.is_dir():
            # Be Windows-friendly: avoid overwriting files that may be open/locked.
            dest.mkdir(parents=True, exist_ok=True)
            for src_path in item.rglob("*"):
                if src_path.is_dir():
                    continue
                rel = src_path.relative_to(item)
                dst_path = dest / rel
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                if dst_path.exists():
                    continue
                try:
                    shutil.copy2(src_path, dst_path)
                except FileNotFoundError:
                    # Race / transient (e.g. generated assets cleaned while copying)
                    continue
        else:
            if dest.exists():
                continue
            try:
                shutil.copy2(item, dest)
            except FileNotFoundError:
                continue


def build_slides(
    meta: dict, articles: list[dict], *, back_link: str = "../latest.html"
) -> list[str]:
    plan, section_plan = build_slide_plan(meta, articles)
    total = len(plan) + 1  # +1 for TOC slide (not stored in plan)
    slides: list[str] = []
    article_goto: dict[str, int] = {}
    for i, item in enumerate(plan):
        if item["type"] == "article" and item.get("part", 1) == 1:
            article_goto[item["art"]["id"]] = i

    slides.append(
        f"""  <section class="slide slide-cover" data-title="封面">
{DECK_BRAND}
    <p class="kicker">LEADERSHIP BRIEF</p>
    <h1 class="h1">香港簡訊</h1>
    <div class="cover-bar"></div>
    <p class="lede">{html.escape(meta["date_range"])}</p>
    <p class="date-chip">海外與投資部 編制 · 共 {len(articles)} 條</p>
    {slide_footer(1, total)}
  </section>"""
    )

    toc_parts = [
        '  <section class="slide slide-toc" data-title="目錄">',
        DECK_BRAND,
        '    <p class="kicker">AGENDA</p>',
        '    <h2 class="h2">本期目錄</h2>',
        '    <div class="slide-toc-scroll">',
    ]
    for section, items in section_plan:
        toc_parts.append('    <div class="toc-section">')
        toc_parts.append(f"      <h4>{html.escape(section)}</h4>")
        toc_parts.append("      <ul>")
        for art in items:
            goto = article_goto[art["id"]] + 1
            toc_parts.append(
                f'        <li data-goto="{goto}">{html.escape(art["title"])}</li>'
            )
        toc_parts.append("      </ul>")
        toc_parts.append("    </div>")
    toc_parts.append("    </div>")
    toc_parts.append(slide_footer(2, total))
    toc_parts.append("  </section>")
    slides.append("\n".join(toc_parts))

    slide_no = 3
    for item in plan[1:-1]:
        if item["type"] == "section":
            section = item["section"]
            slides.append(
                f"""  <section class="slide slide-section" data-title="{html.escape(section, quote=True)}">
{DECK_BRAND}
    <p class="kicker">SECTION</p>
    <h1 class="h1">{html.escape(section.strip("【】"))}</h1>
    <p class="section-count">本節 {item["count"]} 條</p>
    {slide_footer(slide_no, total)}
  </section>"""
            )
        elif item["type"] == "article":
            art = item["art"]
            tag = item["section"].strip("【】")
            continued = ""
            if item["part_total"] > 1:
                if item["part"] == 1:
                    continued = '<span class="article-continued">（全文分頁）</span>'
                else:
                    continued = (
                        f'<span class="article-continued">（續 {item["part"]}/{item["part_total"]}）</span>'
                    )
            slides.append(
                f"""  <section class="slide slide-article" data-title="{html.escape(art["title"], quote=True)}" data-article-id="{html.escape(art["id"], quote=True)}">
{DECK_BRAND}
    <div class="article-top">
      <p class="kicker">{html.escape(tag)} · {item["index"]}/{item["section_count"]}{continued}</p>
      <h2 class="h2">{html.escape(art["title"])}</h2>
      <p class="article-meta">[來源：{html.escape(art["source"])}] · <span class="dateline">【本報{html.escape(art["pub_label"])}】</span></p>
    </div>
    <div class="slide-body">
{item["body_html"]}
    </div>
    {slide_footer(slide_no, total)}
  </section>"""
            )
        slide_no += 1

    slides.append(
        f"""  <section class="slide slide-end" data-title="完">
{DECK_BRAND}
    <p class="kicker">END</p>
    <h1 class="h1">完</h1>
    <p class="lede">{html.escape(meta["date_range"])} · 海外與投資部</p>
    <p class="dim" style="margin-top:1.5rem;font-size:14px"><a href="{html.escape(back_link, quote=True)}">返回長文版</a></p>
    {slide_footer(total, total)}
  </section>"""
    )
    return slides


def build_html(
    meta: dict, articles: list[dict], *, back_link: str = "../latest.html"
) -> str:
    slide_blocks = build_slides(meta, articles, back_link=back_link)
    return f"""<!DOCTYPE html>
<html lang="zh-Hant" data-theme="hk-brief-red">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#c8102e">
<title>香港簡訊 · 簡報版 · {html.escape(meta["date_range"])}</title>
<link rel="stylesheet" href="assets/fonts.css">
<link rel="stylesheet" href="assets/base.css">
<link rel="stylesheet" id="theme-link" href="assets/themes/hk-brief-red.css">
<link rel="stylesheet" href="assets/animations.css">
<link rel="stylesheet" href="style.css">
</head>
<body class="tpl-hk-brief">
<div class="deck">

{chr(10).join(slide_blocks)}

</div>
<div class="tap-zones" aria-hidden="true">
  <span data-nav="prev"></span>
  <span data-nav="next"></span>
</div>
<p class="mobile-hint">左右滑動翻頁 · 點擊兩側 · 目錄可點選跳轉 · O 總覽</p>
<script src="assets/runtime.js"></script>
<script src="mobile.js"></script>
</body>
</html>
"""


def write_slides(
    dest_slides_dir: Path,
    meta: dict,
    articles: list[dict],
    *,
    back_link: str,
) -> Path:
    sync_slide_static_files(dest_slides_dir)
    out = dest_slides_dir / "index.html"
    out.write_text(build_html(meta, articles, back_link=back_link), encoding="utf-8")
    return out


def main() -> None:
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_BASE
    data = json.loads((base / "articles.json").read_text(encoding="utf-8"))
    articles = [
        {
            "id": raw["id"],
            "title": raw["title"],
            "source": raw["source"],
            "pub_label": raw["pub_label"],
            "text": raw["text"],
            "images": raw.get("images") or [],
        }
        for raw in data["articles"]
    ]
    meta = data["meta"]

    rk = meta.get("report_key") or meta.get("reportKey") or meta.get("date") or "latest"
    # Publish a dated deck under docs/brief/slides/{report_key}/
    docs_dated_dir = SLIDES_DIR / str(rk)
    docs_out = write_slides(
        docs_dated_dir, meta, articles, back_link=f"../{rk}.html"
    )
    # Do not overwrite B-consulting rolling redirect at docs/brief/slides/index.html
    latest_marker = SLIDES_DIR / "latest.json"
    if not latest_marker.is_file():
        _docs_latest = write_slides(
            SLIDES_DIR, meta, articles, back_link="../latest.html"
        )
    output_out = write_slides(
        base / "slides", meta, articles, back_link="../daily-brief.html"
    )
    plan, _section_plan = build_slide_plan(meta, articles)
    article_slides = sum(1 for p in plan if p["type"] == "article")
    print(
        f"Wrote {docs_out} and {output_out} ({len(articles)} articles, "
        f"{len(plan)} slides, {article_slides} article pages)"
    )


if __name__ == "__main__":
    main()
