#!/usr/bin/env python3
"""Build mobile-friendly leadership slide deck from articles.json."""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SLIDES_DIR = REPO_ROOT / "docs" / "brief" / "slides"
DEFAULT_BASE = Path(__file__).resolve().parent.parent / "output" / "2026-06-13_2026-06-15"

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


def article_body_html(art: dict) -> str:
    chunks: list[str] = []
    for para in body_paragraphs(art["text"]):
        if is_subhead(para):
            chunks.append(f'<p class="subhead"><strong>{html.escape(para)}</strong></p>')
        else:
            chunks.append(f"<p>{html.escape(para)}</p>")
    return "\n".join(chunks)


def slide_footer(current: int, total: int, label: str = "香港簡訊") -> str:
    return (
        f'<div class="deck-footer">'
        f"<span>{html.escape(label)}</span>"
        f'<span class="slide-number" data-current="{current}" data-total="{total}"></span>'
        f"</div>"
    )


def build_slides(meta: dict, articles: list[dict]) -> list[str]:
    by_id = {a["id"]: a for a in articles}
    slides: list[str] = []

    section_plan: list[tuple[str, list[dict]]] = []
    for section, items in meta["sections"].items():
        section_plan.append((section, [by_id[i["id"]] for i in items]))

    article_count = len(articles)
    total = 1 + 1 + len(section_plan) + article_count + 1
    n = 1

    slides.append(
        f"""  <section class="slide slide-cover" data-title="封面">
    <p class="kicker">LEADERSHIP BRIEF</p>
    <h1 class="h1">香港簡訊</h1>
    <div class="cover-bar"></div>
    <p class="lede">{html.escape(meta["date_range"])}</p>
    <p class="date-chip">海外與投資部 編制 · 共 {article_count} 條</p>
    {slide_footer(n, total)}
  </section>"""
    )
    n += 1

    toc_parts = ['  <section class="slide slide-toc" data-title="目錄">', '    <p class="kicker">AGENDA</p>', '    <h2 class="h2">本期目錄</h2>']
    for section, items in section_plan:
        toc_parts.append(f'    <div class="toc-section">')
        toc_parts.append(f"      <h4>{html.escape(section)}</h4>")
        toc_parts.append("      <ul>")
        for art in items:
            toc_parts.append(f"        <li>{html.escape(art['title'])}</li>")
        toc_parts.append("      </ul>")
        toc_parts.append("    </div>")
    toc_parts.append(slide_footer(n, total))
    toc_parts.append("  </section>")
    slides.append("\n".join(toc_parts))
    n += 1

    for section, items in section_plan:
        slides.append(
            f"""  <section class="slide slide-section" data-title="{html.escape(section, quote=True)}">
    <p class="kicker">SECTION</p>
    <h1 class="h1">{html.escape(section.strip("【】"))}</h1>
    <p class="section-count">本節 {len(items)} 條</p>
    {slide_footer(n, total)}
  </section>"""
        )
        n += 1

        for i, art in enumerate(items, 1):
            tag = section.strip("【】")
            slides.append(
                f"""  <section class="slide slide-article" data-title="{html.escape(art["title"], quote=True)}">
    <div class="article-top">
      <p class="kicker">{html.escape(tag)} · {i}/{len(items)}</p>
      <h2 class="h2">{html.escape(art["title"])}</h2>
      <p class="article-meta">[來源：{html.escape(art["source"])}] · <span class="dateline">【本報{html.escape(art["pub_label"])}】</span></p>
    </div>
    <div class="slide-body">
{article_body_html(art)}
    </div>
    {slide_footer(n, total)}
  </section>"""
            )
            n += 1

    slides.append(
        f"""  <section class="slide slide-end" data-title="完">
    <p class="kicker">END</p>
    <h1 class="h1">完</h1>
    <p class="lede">{html.escape(meta["date_range"])} · 海外與投資部</p>
    <p class="dim" style="margin-top:1.5rem;font-size:14px"><a href="../latest.html">返回長文版</a></p>
    {slide_footer(n, total)}
  </section>"""
    )
    return slides


def build_html(meta: dict, articles: list[dict]) -> str:
    slide_blocks = build_slides(meta, articles)
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
<p class="mobile-hint">左右滑動翻頁 · 點擊兩側 · O 總覽</p>
<script src="assets/runtime.js"></script>
<script src="mobile.js"></script>
</body>
</html>
"""


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
    out = SLIDES_DIR / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_html(data["meta"], articles), encoding="utf-8")
    print(f"Wrote {out} ({len(articles)} articles, {2 + len(data['meta']['sections']) + len(articles) + 1} slides)")


if __name__ == "__main__":
    main()
