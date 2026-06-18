#!/usr/bin/env python3
"""Build B-consulting style flip deck from docs/brief/{date}.html + selection JSON."""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

# Reuse slide chunking from leadership builder
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_leadership_slides import (  # noqa: E402
    SECTION_ORDER,
    is_image_caption_paragraph,
    is_subhead,
    slide_footer,
    sync_slide_static_files,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SLIDES_DIR = REPO_ROOT / "docs" / "brief" / "slides"
BRIEF_DIR = REPO_ROOT / "docs" / "brief"
SELECTION_DIR = REPO_ROOT / "daily-brief-app" / "scripts"
LOCAL_OUTPUT = REPO_ROOT / "daily-brief-app" / "data" / "output"

DISCLAIMER = re.compile(
    r"本網站的內容概不構成任何投資意見.*?本公司概不負責。",
    re.DOTALL,
)
BODY_BLOCK = re.compile(
    r"<p[^>]*>.*?</p>|<figure[^>]*>.*?</figure>",
    re.DOTALL | re.IGNORECASE,
)
P_TAG = re.compile(r"<p[^>]*>(.*?)</p>", re.DOTALL | re.IGNORECASE)
ARTICLE_BLOCK = re.compile(
    r'<article class="article" id="([^"]+)">(.*?)</article>',
    re.DOTALL | re.IGNORECASE,
)

SECTION_LABELS = {
    "【金融與經濟】": "政策與資本市場",
    "【建築與地產】": "工程與樓市",
    "【北都專題】": "北部都會區",
}

TOC_ACTION = (
    "本期目錄覆蓋<em>就業與金價</em>、<em>地產供應</em>與"
    "<em>北都立法與土地</em>三條決策主線"
)

DECK_BRAND = """    <header class="slide-brand" aria-label="頁首標誌">
      <img src="assets/cscec-hk-logo.png" alt="中國建築工程(香港)有限公司">
      <div class="badge">香港簡訊</div>
    </header>"""


def strip_tags(s: str) -> str:
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    return html.unescape(s).strip()


def rewrite_asset_paths(block: str, asset_prefix: str = "../../") -> str:
    return block.replace('src="assets/', f'src="{asset_prefix}assets/')


def parse_body_blocks(raw_body: str, asset_prefix: str = "../../") -> list[str]:
    blocks: list[str] = []
    for block in BODY_BLOCK.findall(raw_body):
        if block.lower().startswith("<figure"):
            blocks.append(rewrite_asset_paths(block, asset_prefix))
            continue
        text = strip_tags(block)
        if not text or DISCLAIMER.search(text) or is_image_caption_paragraph(text):
            continue
        if re.match(r"^原文[：:]", text):
            continue
        inner_m = P_TAG.search(block)
        inner = inner_m.group(1).strip() if inner_m else text
        if is_subhead(text):
            blocks.append(f'<p class="subhead"><strong>{html.escape(text)}</strong></p>')
        elif re.search(r"<(?:strong|b|em|span|a)\b", inner, re.I):
            blocks.append(f"<p>{inner}</p>")
        else:
            blocks.append(f"<p>{html.escape(text)}</p>")
    return blocks


def first_sentence_lede(art: dict) -> str:
    """First body sentence for TOC summary under each title."""
    for block in art.get("body_blocks", []):
        if block.lower().lstrip().startswith("<figure"):
            continue
        text = strip_tags(block)
        if not text or is_image_caption_paragraph(text) or is_subhead(text):
            continue
        parts = re.split(r"(?<=[。！？])", text, maxsplit=1)
        sentence = parts[0].strip() if parts else text
        if len(sentence) >= 8:
            return sentence
        return text[:120]
    for para in art.get("text", "").split("\n\n"):
        para = para.strip()
        if not para or is_subhead(para):
            continue
        parts = re.split(r"(?<=[。！？])", para, maxsplit=1)
        return parts[0].strip() if parts else para[:120]
    return ""


def ensure_subhead_bold(blocks: list[str]) -> list[str]:
    out: list[str] = []
    for block in blocks:
        if 'class="subhead"' in block and "<strong>" not in block.lower():
            inner_m = P_TAG.search(block)
            if inner_m:
                block = f'<p class="subhead"><strong>{inner_m.group(1).strip()}</strong></p>'
        out.append(block)
    return out


def body_html_from_blocks(blocks: list[str]) -> str:
    return "\n".join(blocks) if blocks else ""


def build_b_slide_plan(
    meta: dict, articles: list[dict]
) -> tuple[list[dict], list[tuple[str, list[dict]]]]:
    by_id = {a["id"]: a for a in articles}
    section_plan: list[tuple[str, list[dict]]] = []
    plan: list[dict] = [{"type": "cover"}]

    for section in SECTION_ORDER:
        items_refs = meta["sections"].get(section, [])
        if not items_refs:
            continue
        items = [by_id[r["id"]] for r in items_refs]
        section_plan.append((section, items))
        plan.append({"type": "section", "section": section, "count": len(items)})
        for i, art in enumerate(items, 1):
            plan.append(
                {
                    "type": "article",
                    "art": art,
                    "section": section,
                    "index": i,
                    "section_count": len(items),
                    "body_html": body_html_from_blocks(art.get("body_blocks") or []),
                }
            )

    plan.append({"type": "end"})
    return plan, section_plan


def parse_brief_html(path: Path, asset_prefix: str = "../../") -> dict[str, dict]:
    raw = path.read_text(encoding="utf-8")
    articles: dict[str, dict] = {}
    for aid, block in ARTICLE_BLOCK.findall(raw):
        title_m = re.search(r"<h3>(.*?)</h3>", block, re.DOTALL | re.I)
        source_m = re.search(r'<div class="source">\[(?:來源：)?([^\]]+)\]</div>', block, re.I)
        date_m = re.search(r'<div class="dateline">([^<]+)</div>', block, re.I)
        body_m = re.search(r'<div class="article-body">(.*?)</div>', block, re.DOTALL | re.I)
        if not (title_m and source_m and body_m):
            continue
        body_blocks = ensure_subhead_bold(parse_body_blocks(body_m.group(1), asset_prefix))
        paras = [
            strip_tags(b)
            for b in body_blocks
            if not b.lower().lstrip().startswith("<figure")
        ]
        text = "\n\n".join(paras)
        dateline = strip_tags(date_m.group(1)) if date_m else ""
        pub_label = "6月17日"
        m = re.search(r"(\d+)月(\d+)日", dateline)
        if m:
            pub_label = f"{m.group(1)}月{m.group(2)}日"
        articles[aid] = {
            "id": aid,
            "title": strip_tags(title_m.group(1)),
            "source": strip_tags(source_m.group(1)),
            "pub_label": pub_label,
            "text": text,
            "body_blocks": body_blocks,
            "body_html": body_html_from_blocks(body_blocks),
        }
    return articles


def load_selection(date: str) -> dict:
    candidates = [
        SELECTION_DIR / f"selection_{date}.json",
        LOCAL_OUTPUT / date / "selection.json",
    ]
    path = next((p for p in candidates if p.is_file()), None)
    if not path:
        raise FileNotFoundError(
            f"No selection JSON for {date}. Tried: {', '.join(str(p) for p in candidates)}"
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    sections: dict[str, list[dict]] = {}
    for sec, items in data.get("sections", {}).items():
        key = sec if sec.startswith("【") else f"【{sec}】"
        sections[key] = [
            {
                "id": it["news_id"],
                "title": it["title"],
                "url": it.get("url", ""),
            }
            for it in items
            if it.get("selected", True)
        ]
    return {
        "date": date,
        "date_range": _date_range_label(date, data),
        "report_key": data.get("report_key", date),
        "sections": sections,
    }


def _date_range_label(date: str, data: dict) -> str:
    start = data.get("date_start") or date
    end = data.get("date_end") or date
    if start == end:
        y, m, d = start.split("-")
        return f"{int(y)}年{int(m)}月{int(d)}日"
    return f"{start} – {end}"


def glance_rows(meta: dict) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    start = meta.get("date", "")
    end = meta.get("date_range", "")
    if "年" in end and "–" not in end:
        rows.append(("日期", end.replace("年", "/").replace("月", "/").replace("日", "")))
    else:
        rows.append(("日期區間", meta["date_range"]))
    total = sum(len(v) for v in meta["sections"].values())
    rows.append(("精選條目", f"{total} 條"))
    for sec in SECTION_ORDER:
        n = len(meta["sections"].get(sec, []))
        if n:
            rows.append((sec.strip("【】"), f"{n} 條"))
    return rows


def build_b_slides(meta: dict, articles: list[dict], *, back_link: str) -> list[str]:
    plan, section_plan = build_b_slide_plan(meta, articles)
    total = len(plan) + 1
    slides: list[str] = []
    article_goto: dict[str, int] = {}
    for i, item in enumerate(plan):
        if item["type"] == "article":
            article_goto[item["art"]["id"]] = i

    glance = "\n".join(
        f'        <div class="row"><span>{html.escape(k)}</span>'
        f'<span class="val">{html.escape(v)}</span></div>'
        for k, v in glance_rows(meta)
    )

    slides.append(
        f"""  <section class="slide slide-cover" data-title="封面">
    <div class="pattern" aria-hidden="true"></div>
    <div class="cover-bar-left"></div>
{DECK_BRAND}
    <div class="cover-main">
      <p class="cover-kicker">香港市場動態日報</p>
      <h1 class="h1">香港簡訊</h1>
      <p class="lede">{html.escape(meta["date_range"])} · 海外與投資部編制</p>
      <p class="cover-action">本期匯總就業與金融政策、地產市場與北都發展三大主線，共精選 {len(articles)} 條市場動態。</p>
    </div>
    <aside class="cover-aside">
      <div class="label">本期一覽</div>
{glance}
    </aside>
    {slide_footer(1, total)}
  </section>"""
    )

    toc_parts = [
        '  <section class="slide slide-toc" data-title="目錄">',
        '    <div class="toc-top-bar" aria-hidden="true"></div>',
        DECK_BRAND,
        '    <div class="toc-head">',
        f'      <h2 class="toc-action-title">{TOC_ACTION}</h2>',
        "    </div>",
        '    <div class="slide-toc-scroll">',
    ]
    for section, items in section_plan:
        label = SECTION_LABELS.get(section, "")
        toc_parts.append('    <div class="toc-section">')
        toc_parts.append(f"      <h4>{html.escape(section)}</h4>")
        toc_parts.append(
            f'      <div class="count">{len(items)} 條 · {html.escape(label)}</div>'
        )
        toc_parts.append("      <ul>")
        for art in items:
            goto = article_goto[art["id"]] + 1
            lede = first_sentence_lede(art)
            lede_html = (
                f'\n          <span class="toc-item-lede">{html.escape(lede)}</span>'
                if lede
                else ""
            )
            toc_parts.append(
                f'        <li data-goto="{goto}">'
                f'<span class="toc-item-title">{html.escape(art["title"])}</span>'
                f"{lede_html}\n        </li>"
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
            slides.append(
                f"""  <section class="slide slide-article" data-title="{html.escape(art["title"], quote=True)}" data-article-id="{html.escape(art["id"], quote=True)}">
{DECK_BRAND}
    <div class="article-top">
      <p class="kicker">{html.escape(tag)} · {item["index"]}/{item["section_count"]}</p>
      <h2 class="h2">{html.escape(art["title"])}</h2>
      <p class="article-meta">[來源：{html.escape(art["source"])}] · <span class="dateline">【本報{html.escape(art["pub_label"])}消息】</span></p>
    </div>
    <div class="slide-body" tabindex="0">
{item["body_html"]}
    </div>
    <div class="slide-scroll-fade" aria-hidden="true"></div>
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


B_DECK_ASSETS = (
    "slide-edit.js",
    "slide-edit.css",
    "mobile.js",
    "b-consulting.css",
)


def sync_b_deck_assets(dest: Path) -> None:
    """Copy/overwrite B-deck JS/CSS into dated folder (self-contained deck)."""
    import shutil

    dest.mkdir(parents=True, exist_ok=True)
    sync_slide_static_files(dest)
    for name in B_DECK_ASSETS:
        src = SLIDES_DIR / name
        if src.is_file():
            shutil.copy2(src, dest / name)
    runtime_src = SLIDES_DIR / "assets" / "runtime.js"
    runtime_dst = dest / "assets" / "runtime.js"
    if runtime_src.is_file():
        runtime_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(runtime_src, runtime_dst)


def build_html(meta: dict, articles: list[dict], *, back_link: str, local_assets: bool = True) -> str:
    blocks = build_b_slides(meta, articles, back_link=back_link)
    v = meta["report_key"].replace("-", "") + "9"
    if local_assets:
        css_bc = f"b-consulting.css?v={v}"
        css_edit = f"slide-edit.css?v={v}"
        js_rt = f"assets/runtime.js?v={v}"
        js_mob = f"mobile.js?v={v}"
        js_edit = f"slide-edit.js?v={v}"
    else:
        css_bc = f"../b-consulting.css?v={v}"
        css_edit = f"../slide-edit.css?v={v}"
        js_rt = f"../assets/runtime.js?v={v}"
        js_mob = f"../mobile.js?v={v}"
        js_edit = f"../slide-edit.js?v={v}"
    return f"""<!DOCTYPE html>
<html lang="zh-Hant" data-theme="b-consulting">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#ffffff">
<meta name="brief-slide-key" content="{html.escape(meta["report_key"])}">
<title>香港簡訊 · B 咨詢簡報 · {html.escape(meta["date_range"])}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/fonts.css">
<link rel="stylesheet" href="assets/base.css">
<link rel="stylesheet" href="{css_bc}">
<link rel="stylesheet" href="{css_edit}">
</head>
<body class="tpl-b-consulting">
<div class="deck">

{chr(10).join(blocks)}

</div>
<div class="tap-zones" aria-hidden="true">
  <span data-nav="prev"></span>
  <span data-nav="next"></span>
</div>
<p class="mobile-hint">左右滑動翻頁 · 正文頁可上下滑動閱讀 · 目錄可點選跳轉</p>
<script src="{js_rt}"></script>
<script src="{js_mob}"></script>
<script src="{js_edit}"></script>
</body>
</html>
"""


def articles_from_meta(meta: dict, parsed: dict[str, dict]) -> list[dict]:
    out: list[dict] = []
    for section in SECTION_ORDER:
        for ref in meta["sections"].get(section, []):
            art = parsed.get(ref["id"])
            if not art:
                raise KeyError(f"Missing article body for {ref['id']} in brief HTML")
            out.append(art)
    return out


def write_latest_redirect(date: str) -> Path:
    """Rolling entry: /brief/slides/ → newest dated folder (small redirect, not a full deck copy)."""
    latest = SLIDES_DIR / "index.html"
    latest.write_text(
        f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="0; url={date}/">
<title>香港簡訊 · 最新簡報</title>
</head>
<body>
<p>正在前往最新一期簡報（{date}）…</p>
<p><a href="{date}/">若未自動跳轉，請點此</a></p>
</body>
</html>
""",
        encoding="utf-8",
    )
    (SLIDES_DIR / "latest.json").write_text(
        json.dumps({"report_key": date}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return latest


def brief_source(date: str) -> tuple[Path, str, bool]:
    """Return (brief_path, asset_prefix, in_issue_folder)."""
    issue_brief = SLIDES_DIR / date / "brief.html"
    if issue_brief.is_file():
        return issue_brief, "brief-assets/", True
    flat = BRIEF_DIR / f"{date}.html"
    if flat.is_file():
        return flat, "../../", False
    raise FileNotFoundError(
        f"No brief HTML for {date}. Expected {issue_brief} or {flat}"
    )


def sync_issue_word(date: str, dest: Path) -> Path | None:
    out_dir = LOCAL_OUTPUT / date
    preferred = out_dir / "daily-brief.docx"
    docx_src = preferred if preferred.is_file() else None
    if not docx_src and out_dir.is_dir():
        found = sorted(out_dir.glob("*.docx"), key=lambda p: p.stat().st_mtime, reverse=True)
        docx_src = found[0] if found else None
    if not docx_src:
        return None
    docx_dest = dest / "brief.docx"
    import shutil

    shutil.copy2(docx_src, docx_dest)
    return docx_dest


def write_deck(date: str) -> Path:
    brief_path, asset_prefix, in_issue = brief_source(date)
    if not brief_path.is_file():
        raise FileNotFoundError(brief_path)
    meta = load_selection(date)
    parsed = parse_brief_html(brief_path, asset_prefix=asset_prefix)
    articles = articles_from_meta(meta, parsed)

    dest = SLIDES_DIR / date
    sync_b_deck_assets(dest)
    sync_issue_word(date, dest)
    # Ensure logo present (sync skips existing files)
    logo_src = REPO_ROOT / "design-demos" / "assets" / "cscec-hk-logo.png"
    if logo_src.is_file():
        import shutil

        for assets_dir in (SLIDES_DIR / "assets", dest / "assets"):
            assets_dir.mkdir(parents=True, exist_ok=True)
            dst_logo = assets_dir / "cscec-hk-logo.png"
            if not dst_logo.exists() or dst_logo.stat().st_size != logo_src.stat().st_size:
                shutil.copy2(logo_src, dst_logo)

    out = dest / "index.html"
    if in_issue:
        back = "brief.html"
    else:
        back = f"../../{date}.html"
    out.write_text(build_html(meta, articles, back_link=back, local_assets=True), encoding="utf-8")

    # Also mirror to design-demos for quick preview
    demo = REPO_ROOT / "design-demos" / f"B-consulting-{date}.html"
    demo_html = build_html(meta, articles, back_link=f"../docs/brief/slides/{date}/brief.html")
    demo_html = demo_html.replace('href="../assets/', 'href="../docs/brief/slides/assets/')
    demo_html = demo_html.replace('href="b-consulting.css', 'href="../docs/brief/slides/b-consulting.css')
    demo_html = demo_html.replace('href="slide-edit.css', 'href="../docs/brief/slides/slide-edit.css')
    demo_html = demo_html.replace('src="assets/', 'src="../docs/brief/slides/assets/')
    demo_html = demo_html.replace('src="mobile.js', 'src="../docs/brief/slides/mobile.js')
    demo_html = demo_html.replace('src="slide-edit.js', 'src="../docs/brief/slides/slide-edit.js')
    demo_html = demo_html.replace(
        'src="../../assets/', 'src="../docs/brief/assets/'
    )
    demo.write_text(demo_html, encoding="utf-8")
    latest = write_latest_redirect(date)
    return out, latest


def main() -> None:
    date = sys.argv[1] if len(sys.argv) > 1 else "2026-06-17"
    out, latest = write_deck(date)
    meta = load_selection(date)
    brief_path, asset_prefix, _ = brief_source(date)
    parsed = parse_brief_html(brief_path, asset_prefix=asset_prefix)
    arts = articles_from_meta(meta, parsed)
    plan, _ = build_b_slide_plan(meta, arts)
    n_figures = sum(
        1
        for a in arts
        for b in a.get("body_blocks", [])
        if b.lower().lstrip().startswith("<figure")
    )
    n_articles = sum(1 for p in plan if p["type"] == "article")
    print(
        f"Wrote {out} and {latest} ({n_articles} article pages, {len(plan)} slides in plan, "
        f"{n_figures} inline images)"
    )


if __name__ == "__main__":
    main()
