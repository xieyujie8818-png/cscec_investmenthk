#!/usr/bin/env python3
"""Build daily-leadership-brief.md and self-contained .html from articles.json."""

from __future__ import annotations

import base64
import csv
import html
import json
import mimetypes
import re
import struct
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

TRIM_MARKERS = [
    "日報新聞-相關報道",
    "相關字詞﹕",
    "■明報報料熱線",
    "讀大公報PDF版面",
    "HKET App已全面升級",
    "追蹤TOPick",
    "關鍵字：",
    "上一篇文章",
]

REMOVE_REF_MARKERS = re.compile(
    r"【詳見另文】|【詳見另稿】|（詳見另文）|（詳見另稿）|【詳見下表】"
)
TABLE_MARKERS = re.compile(r"【見表】|（部分見表）|（見表）")
IMAGE_CAPTION_END = re.compile(r"（[^）]*(攝|資料圖片|圖片)）$")

AD_URL_HINTS = (
    "ad",
    "advert",
    "advertisement",
    "banner",
    "promo",
    "sponsor",
    "doubleclick",
    "googlesyndication",
    "新書推薦",
    "bookcover",
    "/book/",
    "logo",
    "icon",
    "sprite",
    "pixel",
    "tracking",
    "tkww-static",
    "default-img",
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOCS_BRIEF_DIR = REPO_ROOT / "docs" / "brief"

HTML_CSS = """
    :root {
      --red: #c8102e;
      --red-dark: #9b0c24;
      --text: #333;
      --muted: #666;
      --border: #e8d4d8;
      --bg: #ffffff;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Microsoft YaHei", "PingFang TC", "Noto Sans TC", sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.75;
    }
    .wrap { max-width: 820px; margin: 0 auto; padding: 2rem 1.5rem 3rem; }
    header {
      text-align: center;
      border-bottom: 3px solid var(--red);
      padding-bottom: 1.25rem;
      margin-bottom: 2rem;
    }
    header h1 {
      margin: 0 0 0.5rem;
      color: var(--red);
      font-size: 2rem;
      letter-spacing: 0.15em;
    }
    header .date { color: var(--muted); margin: 0.25rem 0; }
    header .dept { font-weight: 600; margin-top: 0.5rem; }
    h2 {
      color: var(--red);
      font-size: 1.25rem;
      border-left: 4px solid var(--red);
      padding-left: 0.6rem;
      margin: 2rem 0 1rem;
    }
    h3.section-label {
      color: var(--red-dark);
      font-size: 1rem;
      margin: 1.25rem 0 0.5rem;
    }
    .toc-item {
      margin-bottom: 0.85rem;
      padding-bottom: 0.65rem;
      border-bottom: 1px solid var(--border);
    }
    .toc-item a {
      color: var(--text);
      font-weight: 600;
      text-decoration: none;
    }
    .toc-item a:hover { color: var(--red); text-decoration: underline; }
    .toc-item .summary {
      color: var(--muted);
      font-size: 0.92rem;
      margin-top: 0.25rem;
    }
    article {
      margin-bottom: 2rem;
      padding-bottom: 1.5rem;
      border-bottom: 1px solid var(--border);
    }
    article h3 {
      color: var(--red);
      font-size: 1.15rem;
      margin: 0 0 0.5rem;
      line-height: 1.45;
    }
    article .source { color: var(--muted); font-size: 0.9rem; margin-bottom: 0.35rem; }
    article .dateline {
      color: var(--red-dark);
      font-weight: 600;
      margin-bottom: 0.75rem;
    }
    article p { margin: 0 0 0.85rem; text-align: justify; }
    article p.caption {
      color: var(--muted);
      font-size: 0.92rem;
      font-style: italic;
      margin-top: -0.35rem;
    }
    article .inline-figure { margin: 0.75rem 0; }
    article .inline-figure img {
      max-width: 100%;
      height: auto;
      display: block;
      border: 1px solid var(--border);
    }
    footer {
      text-align: center;
      color: var(--muted);
      font-size: 0.85rem;
      margin-top: 2rem;
    }
    footer a { color: var(--red); text-decoration: none; }
    footer a:hover { text-decoration: underline; }
"""


def is_ad_image(url: str) -> bool:
    low = url.lower()
    if not url or url.startswith("data:") or low.endswith(".svg"):
        return True
    if low.endswith("/htm/") or "mingpao.com/htm/" in low:
        return True
    return any(hint in low for hint in AD_URL_HINTS)


def filter_images(imgs: list[str], source: str) -> list[str]:
    out: list[str] = []
    for u in imgs:
        if is_ad_image(u):
            continue
        if source == "大公報" and "dw-media.tkww.hk" in u:
            out.append(u)
        elif source == "信報" and "static.hkej.com/hkej/images" in u:
            out.append(u)
        elif "fs.mingpao.com" in u:
            out.append(u)
        elif "static04.hket.com/res/v3/image/content" in u:
            out.append(u)
        elif source == "香港經濟日報" and "hket.com" in u and "/image/" in u:
            out.append(u)
    if out and any("hket.com/res/v3/image" in u for u in out):
        groups: dict[str, list[str]] = {}
        for u in out:
            key = u.rsplit("_", 1)[0]
            groups.setdefault(key, []).append(u)
        out = [
            max(
                g,
                key=lambda x: int(re.search(r"_(\d+)\.", x).group(1))
                if re.search(r"_(\d+)\.", x)
                else 0,
            )
            for g in groups.values()
        ]
    return list(dict.fromkeys(out))


def strip_editorial_refs(text: str) -> str:
    text = REMOVE_REF_MARKERS.sub("", text)
    return re.sub(r"[ \t]{2,}", " ", text)


def clean_body(text: str, title: str) -> str:
    text = text.strip()
    m = re.search(r"20\d{2}年\d{1,2}月\d{1,2}日\s*\n\s*" + re.escape(title), text)
    if m:
        text = text[m.end() :].lstrip()
    elif title in text:
        parts = text.split(title, 1)
        if len(parts) > 1:
            text = parts[1].lstrip()
    text = re.sub(r"^.*?\n(?:要聞|港聞)\s*\n\n", "", text, count=1, flags=re.S)
    text = re.sub(r"撰文：.*?\n\n", "", text, count=1)
    text = re.sub(r"發布時間：.*?\n\n", "", text, count=1)
    text = re.sub(r"最後更新：.*?\n\n", "", text, count=1)
    if text.startswith("放大圖片"):
        text = text[len("放大圖片") :].lstrip()
    if "AI 摘要" in text:
        text = re.split(r"AI 摘要\s*\n", text, maxsplit=1)[-1]
        text = re.sub(r"^[^\n]+\n(?:[^\n]+\n){0,4}", "", text, count=1)
    if "今日大公" in text[:80]:
        text = re.split(r"分享\s*\n\n", text, maxsplit=1)[-1]
    for marker in TRIM_MARKERS:
        if marker in text:
            text = text.split(marker, 1)[0].rstrip()
    if "責任編輯" in text:
        text = text.split("責任編輯", 1)[0].rstrip()
    return strip_editorial_refs(text.strip())


def first_summary(text: str, max_len: int = 120) -> str:
    parts = [p.replace("\n", "").strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    para = parts[0]
    if para.startswith("▲") and len(parts) > 1:
        para = parts[1]
    if para.startswith("【") and "】" in para:
        para = para.split("】", 1)[-1].lstrip()
    if len(para) > max_len:
        para = para[: max_len - 1] + "…"
    return para


def body_paragraphs(text: str) -> list[str]:
    parts = re.split(r"\n\s*\n", text.strip())
    return [p.replace("\n", "").strip() for p in parts if p.strip()]


def is_image_caption_paragraph(para: str) -> bool:
    para = para.strip()
    if para.startswith("▲"):
        return True
    return bool(IMAGE_CAPTION_END.search(para))


def editorial_paragraphs(text: str) -> list[str]:
    out: list[str] = []
    for para in body_paragraphs(text):
        if is_image_caption_paragraph(para):
            continue
        clean = TABLE_MARKERS.sub("", para).strip()
        if clean:
            out.append(clean)
    return out


@dataclass
class EmbeddedImage:
    uri: str
    width: int
    height: int
    url: str = ""


def image_size(data: bytes) -> tuple[int, int] | None:
    if len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    if len(data) >= 2 and data[:2] == b"\xff\xd8":
        i = 2
        while i < len(data) - 8:
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            i += 2
            if marker in (0xD8, 0xD9):
                continue
            if i + 2 > len(data):
                break
            seg_len = struct.unpack(">H", data[i : i + 2])[0]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                if i + 7 <= len(data):
                    h, w = struct.unpack(">HH", data[i + 3 : i + 7])
                    return w, h
                break
            i += seg_len
    if len(data) >= 10 and data[:6] in (b"GIF87a", b"GIF89a"):
        return struct.unpack("<HH", data[6:10])
    return None


def is_ad_dimensions(width: int, height: int) -> bool:
    if width <= 0 or height <= 0:
        return False
    if max(width, height) < 120:
        return True
    aspect = width / height
    if aspect > 2.5 and height < 280:
        return True
    return False


def image_slots(body: str) -> list[str]:
    slots: list[str] = []
    for para in editorial_paragraphs(body):
        if TABLE_MARKERS.search(para):
            slots.append("table")
    return slots


def load_source_urls(base: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    csv_path = base / "news-register.csv"
    if not csv_path.exists():
        return mapping
    with csv_path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            news_id = (row.get("news_id") or "").strip()
            url = (row.get("source_url") or "").strip()
            if not news_id or not url:
                continue
            suffix = news_id.rsplit("-", 1)[-1]
            if suffix.isdigit():
                mapping[f"news-{int(suffix):03d}"] = url
    return mapping


def encode_url(url: str) -> str:
    from urllib.parse import quote, urlsplit, urlunsplit

    parts = urlsplit(url.strip())
    if not parts.scheme or not parts.netloc:
        return url
    path = quote(parts.path, safe="/%:@&=+$,;~*-._")
    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))


def scrape_page_image_urls(page_url: str) -> list[str]:
    req = urllib.request.Request(
        encode_url(page_url),
        headers={"User-Agent": "Mozilla/5.0 (compatible; cohl-brief/1.0)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            page_html = resp.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError):
        return []
    found: list[str] = []
    for pattern in (
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        r'static04\.hket\.com/res/v3/image/content/[^"\'\s<>]+',
        r'fs\.mingpao\.com/ins/[^"\'\s<>]+',
        r'static\.hkej\.com/hkej/images/[^"\'\s<>]+',
        r'dw-media\.tkww\.hk/[^"\'\s<>]+\.(?:jpg|jpeg|png|webp)',
    ):
        for match in re.finditer(pattern, page_html, flags=re.I):
            url = match.group(1) if match.lastindex else match.group(0)
            if url.startswith("http") and url not in found:
                found.append(url)
    return found


def _guess_mime(url: str, content_type: str | None, data: bytes) -> str:
    if content_type and content_type.startswith("image/"):
        return content_type.split(";")[0].strip()
    ext = Path(urlparse_path(url)).suffix.lower()
    mime, _ = mimetypes.guess_type(f"file{ext}")
    if mime:
        return mime
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:2] == b"\xff\xd8":
        return "image/jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    return "image/jpeg"


def urlparse_path(url: str) -> str:
    from urllib.parse import urlparse

    return urlparse(url).path


def download_image(url: str, cache: dict[str, EmbeddedImage | None]) -> EmbeddedImage | None:
    if url in cache:
        return cache[url]
    if url.startswith("data:image"):
        img = EmbeddedImage(uri=url, width=0, height=0, url=url)
        cache[url] = img
        return img
    fetch_url = encode_url(url)
    referer = "/".join(url.split("/")[:3]) + "/"
    req = urllib.request.Request(
        fetch_url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; cohl-brief/1.0)",
            "Referer": referer,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = resp.read()
            if len(data) < 500:
                cache[url] = None
                return None
            size = image_size(data)
            width, height = size if size else (0, 0)
            mime = _guess_mime(url, resp.headers.get("Content-Type"), data)
            uri = f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
            img = EmbeddedImage(uri=uri, width=width, height=height, url=url)
            cache[url] = img
            return img
    except (urllib.error.URLError, TimeoutError, OSError):
        cache[url] = None
        return None


def collect_image_urls(raw: dict, body: str, source_urls: dict[str, str]) -> list[str]:
    urls = list(raw.get("images") or [])
    urls = filter_images(urls, raw["source"])
    slots = image_slots(body)
    if len(slots) <= len(urls):
        return list(dict.fromkeys(urls))
    page_url = (raw.get("source_url") or source_urls.get(raw["id"]) or "").strip()
    if page_url:
        for scraped in scrape_page_image_urls(page_url):
            if scraped not in urls and not is_ad_image(scraped):
                urls.append(scraped)
        urls = filter_images(urls, raw["source"])
    return list(dict.fromkeys(urls))


def prepare_embedded_images(
    raw: dict,
    body: str,
    source_urls: dict[str, str],
    cache: dict[str, EmbeddedImage | None],
) -> list[EmbeddedImage]:
    embedded: list[EmbeddedImage] = []
    for url in collect_image_urls(raw, body, source_urls):
        img = download_image(url, cache)
        if img:
            embedded.append(img)
    return embedded


def pick_for_table(pool: list[EmbeddedImage]) -> EmbeddedImage | None:
    if not pool:
        return None
    editorial = [img for img in pool if not is_ad_dimensions(img.width, img.height)]
    if editorial:
        candidates = editorial
    else:
        # 信報等來源有時兩張都是橫幅比例；表格通常比書封廣告更高
        candidates = pool
    best = max(
        candidates,
        key=lambda img: (img.height, img.width * img.height, pool.index(img)),
    )
    pool.remove(best)
    return best


def pick_for_photo(pool: list[EmbeddedImage]) -> EmbeddedImage | None:
    if not pool:
        return None
    for i, img in enumerate(pool):
        if not is_ad_dimensions(img.width, img.height):
            return pool.pop(i)
    return pool.pop(0)


def _figure_html(data_uri: str, alt: str = "") -> str:
    return (
        f'<figure class="inline-figure">'
        f'<img src="{data_uri}" alt="{html.escape(alt)}">'
        f"</figure>"
    )


def render_article_body(art: dict) -> list[str]:
    """Text-only body; no images or image-caption paragraphs."""
    return [f"<p>{html.escape(para)}</p>" for para in editorial_paragraphs(art["body"])]


def build_md(meta: dict, articles: list) -> str:
    date_range = meta["date_range"]
    lines = [
        "# 香港簡訊",
        "",
        f"**{date_range}**",
        "",
        "**海外與投資部 編制**",
        "",
        "---",
        "",
        "## 目 錄",
        "",
    ]
    for section, items in meta["sections"].items():
        lines.append(f"**{section}**")
        lines.append("")
        for item in items:
            aid = item["id"]
            art = next(a for a in articles if a["id"] == aid)
            summary = first_summary(art["body"])
            lines.append(f"- [{art['title']}](#{aid})")
            lines.append("")
            lines.append(f"【{summary}】")
            lines.append("")
    lines.extend(["---", "", "## 正文", ""])
    for art in articles:
        lines.extend(
            [
                f'<a id="{art["id"]}"></a>',
                "",
                f"### {art['title']}",
                "",
                f"[來源：{art['source']}]",
                "",
                f"【本報{art['pub_label']}】",
                "",
            ]
        )
        for para in editorial_paragraphs(art["body"]):
            lines.append(para)
            lines.append("")
        lines.extend(["---", ""])
    lines.extend(
        [
            "## 編制說明",
            "",
            f"- 本稿共 **{len(articles)}條**："
            + "、".join(f"{s}{len(items)}條" for s, items in meta["sections"].items())
            + "。",
            "- 正文為會員全文照錄；對外產出不含原文鏈接。",
            "- 同目錄內容見 `daily-leadership-brief.html`（紅白純文字版）及 GitHub Pages `docs/brief/latest.html`。",
            "",
        ]
    )
    return "\n".join(lines)


def build_html(meta: dict, articles: list) -> str:
    parts = [
        "<!DOCTYPE html>",
        '<html lang="zh-Hant">',
        "<head>",
        '<meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>香港簡訊 {html.escape(meta['date_range'])}</title>",
        f"<style>{HTML_CSS}</style>",
        "</head>",
        "<body>",
        '<div class="wrap">',
        "<header>",
        "<h1>香港簡訊</h1>",
        f'<p class="date">{html.escape(meta["date_range"])}</p>',
        '<p class="dept">海外與投資部 編制</p>',
        "</header>",
        '<h2 id="toc">目 錄</h2>',
    ]
    for section, items in meta["sections"].items():
        parts.append(f'<h3 class="section-label">{html.escape(section)}</h3>')
        for item in items:
            art = next(a for a in articles if a["id"] == item["id"])
            summary = first_summary(art["body"])
            parts.append('<div class="toc-item">')
            parts.append(
                f'<a href="#{art["id"]}">{html.escape(art["title"])}</a>'
                f'<div class="summary">【{html.escape(summary)}】</div>'
            )
            parts.append("</div>")
    parts.append('<h2 id="body">正 文</h2>')
    for art in articles:
        parts.append(f'<article id="{art["id"]}">')
        parts.append(f"<h3>{html.escape(art['title'])}</h3>")
        parts.append(f'<p class="source">[來源：{html.escape(art["source"])}]</p>')
        parts.append(f'<p class="dateline">【本報{html.escape(art["pub_label"])}】</p>')
        parts.extend(render_article_body(art))
        parts.append("</article>")
    parts.extend(
        [
            "<footer>",
            f"香港簡訊 · {html.escape(meta['date_range'])} · 海外與投資部",
            ' · <a href="slides/index.html" style="color:var(--red)">手機簡報版</a>',
            "</footer>",
            "</div>",
            "</body>",
            "</html>",
        ]
    )
    return "\n".join(parts)


def slug_from_base(base: Path) -> str:
    return base.name


def publish_to_docs(html_content: str, slug: str) -> tuple[Path, Path]:
    DOCS_BRIEF_DIR.mkdir(parents=True, exist_ok=True)
    dated = DOCS_BRIEF_DIR / f"{slug}.html"
    latest = DOCS_BRIEF_DIR / "latest.html"
    dated.write_text(html_content, encoding="utf-8")
    latest.write_text(html_content, encoding="utf-8")
    return dated, latest


def main() -> None:
    default_base = (
        Path(__file__).resolve().parent.parent / "output" / "2026-06-13_2026-06-15"
    )
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else default_base
    data = json.loads((base / "articles.json").read_text(encoding="utf-8"))
    articles = []
    for raw in data["articles"]:
        body = clean_body(raw["text"], raw["title"])
        articles.append(
            {
                "id": raw["id"],
                "title": raw["title"],
                "source": raw["source"],
                "pub_label": raw["pub_label"],
                "body": body,
            }
        )

    md = build_md(data["meta"], articles)
    html_out = build_html(data["meta"], articles)
    (base / "daily-leadership-brief.md").write_text(md, encoding="utf-8")
    (base / "daily-leadership-brief.html").write_text(html_out, encoding="utf-8")

    slug = slug_from_base(base)
    dated_doc, latest_doc = publish_to_docs(html_out, slug)

    slides_script = Path(__file__).resolve().parent / "build_leadership_slides.py"
    subprocess.run([sys.executable, str(slides_script), str(base)], check=True)

    print(f"Wrote {base / 'daily-leadership-brief.md'} and .html ({len(articles)} articles, text-only)")
    print(f"Published to {dated_doc} and {latest_doc}")


if __name__ == "__main__":
    main()
