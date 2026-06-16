"""Fetch articles from news site listing + article pages (no flipbook)."""

from __future__ import annotations

import asyncio
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import unquote, urljoin, urlparse
from zoneinfo import ZoneInfo

import yaml
from bs4 import BeautifulSoup

from app.models import RawArticle
from app.scoring import is_opinion_content, load_keywords_config, title_passes_listing_gate
from app.auth import ensure_logged_in, open_login_flow, page_needs_login
from app import progress as job_progress
from app.browser_sessions import (
    BrowserClosedError,
    ProfileLockedError,
    _is_profile_lock_error,
    acquire_persistent_context,
    ensure_context_ready,
    finish_login_and_release,
    register_login_session,
    release_context,
)


class LoginRequiredError(Exception):
    """Subscriber session missing or paywall detected — fetch must pause for login."""

    def __init__(self, source_id: str, source_name: str, message: str) -> None:
        self.source_id = source_id
        self.source_name = source_name
        super().__init__(message)

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext, Page

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PROFILES_DIR = DATA_DIR / "browser_profiles"

SKIP_TEXT_PARTS = ("訂閱", "登入", "會員", "廣告", "下載", "搜尋", "分享至")

HKT = ZoneInfo("Asia/Hong_Kong")

# 按栏严格白名单：source_id:section_id → 正文 URL 必须匹配
SECTION_ARTICLE_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    # srap001 要闻列表会链到 invest 或 paper 两种正文域名
    "hket:finance_invest": [
        re.compile(r"invest\.hket\.com/article/\d+", re.I),
        re.compile(r"paper\.hket\.com/article/\d+", re.I),
    ],
    "hket:property": [re.compile(r"paper\.hket\.com/article/\d+", re.I)],
    "hket:instant_news": [re.compile(r"inews\.hket\.com/article/\d+", re.I)],
    "hkej:headline": [re.compile(r"hkej\.com/dailynews/headline/article/\d+", re.I)],
    "hkej:property": [re.compile(r"hkej\.com/dailynews/property/article/\d+", re.I)],
    "mingpao:economy": [
        re.compile(r"news\.mingpao\.com/pns/[^/?#]+/article/\d{8}/s00004/", re.I),
    ],
    **{
        f"wenweipo:{sid}": [
            re.compile(r"wenweipo\.com/a/\d{6}/\d{2}/AP[a-f0-9]+\.html", re.I),
        ]
        for sid in (
            "economy",
            "finance",
            "property",
            "investment",
        )
    },
}

# Always reject these in path (列表页 index，非正文)
BLOCKED_URL_RE = [
    re.compile(p, re.I)
    for p in (
        r"/author",
        r"/search",
        r"/login",
        r"/register",
        r"/subscribe",
        r"/member",
        r"/quote",
        r"/marketprice",
        r"/opinion",
        r"/column",
        r"/comment",
        r"financial-comment",
        r"/author/",
        r"/latest/?$",
        r"/firsthand/?$",
        r"/business/?$",
        r"/resident/?$",
        r"/education/",
        r"/bayarea",
        r"stock360",
        r"dailynews/(headline|investment|property)/?$",
        r"hkej\.com/property/?$",
        r"hkej\.com/property/(opinion|marketprice|quote)",
        r"hkej\.com/instantnews/",
        r"ps\.hket\.com/srae\d+/%E5%8D%B3%E6%99%82",  # 即時樓市 index
        r"ps\.hket\.com/srae007",
        r"paper\.hket\.com/srap\d+/?$",
        r"wenweipo\.com/business/?$",
        r"wenweipo\.com/business/finance/?$",
        r"wenweipo\.com/business/real-estate/?$",
        r"wenweipo\.com/business/investment/?$",
        r"web-flip",
        r"wenweipo\.com/business/digital-economy",
        r"#\d+$",
    )
]

JUNK_SITE_TITLES = frozenset(
    {"信報網站", "香港文匯網", "文匯網", "香港經濟日報", "明報", "即時樓市"}
)

# Regex fallback: pull article URLs directly from listing HTML
HTML_ARTICLE_RES: dict[str, list[re.Pattern[str]]] = {
    "hket": [
        re.compile(r"https?://inews\.hket\.com/article/\d+[^\"'\\s<]*", re.I),
        re.compile(r"https?://invest\.hket\.com/article/\d+[^\"'\\s<]*", re.I),
        re.compile(r"https?://paper\.hket\.com/article/\d+[^\"'\\s<]*", re.I),
        re.compile(r'["\'](https?://invest\.hket\.com/article/\d+[^"\']*)', re.I),
        re.compile(r'["\'](https?://paper\.hket\.com/article/\d+[^"\']*)', re.I),
        re.compile(r'["\'](/article/\d+[^"\']*)', re.I),
        re.compile(r'["\'](article/\d+[^"\']*)', re.I),
    ],
    "mingpao": [
        re.compile(
            r"https?://news\.mingpao\.com/pns/[^\"'\\s<]+/article/\d{8}/s00004/[^\"'\\s<]*",
            re.I,
        ),
        re.compile(
            r'["\'](/pns/[^"\']+/article/\d{8}/s00004/[^"\']*)',
            re.I,
        ),
    ],
    "hkej": [
        re.compile(
            r"https?://www\.hkej\.com/dailynews/[^\"'\\s<]+/article/\d+[^\"'\\s<]*",
            re.I,
        ),
    ],
    "wenweipo": [
        re.compile(
            r"https?://www\.wenweipo\.com/a/\d{6}/\d{2}/AP[a-f0-9]+\.html",
            re.I,
        ),
    ],
}

MAX_LINKS_PER_SECTION = 40
HKET_MAX_LINKS_PER_SECTION = 20
MIN_BODY_LEN = 60
DATE_TOLERANCE_DAYS = 2

# Per-source article body selectors (Playwright + BeautifulSoup)
BODY_SELECTORS: dict[str, list[str]] = {
    "hket": [
        ".article-content",
        "#article-content",
        ".subscriber-content",
        "[class*='ArticleContent']",
        "article .content",
        "article",
        ".story-content",
        "[itemprop='articleBody']",
    ],
    "hkej": [
        "#articleDetail .scrollRead",
        "#articleDetail",
        ".articleDetail .scrollRead",
        ".scrollRead",
        "#article-content",
        ".paywall-article",
        ".article-content",
        ".article-body",
    ],
    "wenweipo": [
        ".article-content",
        "#content-article",
        ".detail-content",
        "#zoom",
        ".TRS_Editor",
        ".content",
        "article",
    ],
    "mingpao": [
        ".article-content",
        "#article-content",
        ".main-content",
        ".content",
        "article",
    ],
}

PAYWALL_MARKERS = (
    "訂閱",
    "續訂",
    "登入以閱讀",
    "會員專享",
    "付費牆",
    "訂戶專享",
    "訂戶登入",
    "成為訂戶",
    "請登入",
)


def _looks_like_paywall(text: str) -> bool:
    if not text:
        return False
    sample = text[:800]
    hits = sum(1 for m in PAYWALL_MARKERS if m in sample)
    if hits >= 2:
        return True
    if "登入以閱讀" in sample or "會員專享" in sample:
        return len(text.strip()) < MIN_BODY_LEN * 4
    return False


async def _listing_failure_reason(
    page: Page, source_id: str, html: str, *, needs_login: bool
) -> str:
    """Distinguish empty listing due to login/paywall vs genuinely no links."""
    if needs_login:
        try:
            if await page_needs_login(page, source_id):
                return "login_required"
        except Exception:
            pass
    if _looks_like_paywall(html):
        return "paywall"
    if needs_login and any(m in html[:4000] for m in PAYWALL_MARKERS):
        return "paywall"
    return "no_links"


def playwright_available() -> tuple[bool, str]:
    try:
        from playwright.async_api import async_playwright  # noqa: F401
        return True, ""
    except ImportError as exc:
        return False, str(exc)


def _require_playwright() -> None:
    ok, err = playwright_available()
    if not ok:
        raise RuntimeError(
            "Playwright unavailable. Install VC++ Redistributable x64: "
            "https://aka.ms/vs/17/release/vc_redist.x64.exe "
            f"Error: {err}"
        )


def load_sources_config() -> dict:
    path = Path(__file__).resolve().parent.parent / "config" / "sources.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _profile_path(source_id: str) -> Path:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    return PROFILES_DIR / source_id


def _fetch_headless(source_id: str) -> bool:
    """HKET / 明报列表在 headless 下常为 0 links，抓取时用 headed。"""
    return source_id not in ("hket", "mingpao")


async def _launch_fetch_context(
    pw, source_id: str, needs_login: bool, source_name: str = ""
):
    """Launch browser for fetch; reuse login session or raise ProfileLockedError."""
    headless = _fetch_headless(source_id)
    if not needs_login:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1400, "height": 900})
        return browser, context

    if source_id in ("hket", "mingpao"):
        name = source_name or ("經濟日報" if source_id == "hket" else "明報")
        print(
            f"[fetch] {source_id}: headed 模式 — "
            f"可复用已打开的「登入 {name}」窗口；抓取中请勿关闭 Chrome"
        )

    profile = _profile_path(source_id)
    if source_id in ("hket", "mingpao"):
        context, reused = await acquire_persistent_context(
            pw,
            source_id,
            profile,
            headless=headless,
            source_name=source_name or source_id,
        )
        if reused:
            print(f"[fetch] {source_id}: 复用登入浏览器 session（同一 context）")
        return None, context

    try:
        context = await pw.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=headless,
            viewport={"width": 1400, "height": 900},
        )
    except Exception as exc:
        if _is_profile_lock_error(exc):
            raise ProfileLockedError(
                source_id, source_name or source_id, str(exc)
            ) from exc
        raise
    return None, context


async def _get_fetch_context(
    pw,
    source_id: str,
    needs_login: bool,
    source_name: str = "",
):
    """Return a live context; relaunch if the headed window was closed."""
    if not needs_login:
        return None
    profile = _profile_path(source_id)
    headless = _fetch_headless(source_id)
    try:
        return await ensure_context_ready(
            pw,
            source_id,
            profile,
            headless=headless,
            source_name=source_name or source_id,
        )
    except ProfileLockedError:
        raise
    except Exception as exc:
        raise BrowserClosedError(source_id, source_name or source_id) from exc


def _detect_source_id(url: str) -> str:
    low = url.lower()
    if "hkej.com" in low:
        return "hkej"
    if "hket.com" in low:
        return "hket"
    if "mingpao.com" in low:
        return "mingpao"
    if "wenweipo.com" in low:
        return "wenweipo"
    return ""


def _section_key(source_id: str, section_id: str) -> str:
    return f"{source_id}:{section_id}"


def _is_article_url(url: str, source_id: str, section_id: str = "") -> bool:
    if not url or not url.startswith("http"):
        return False
    low = url.lower()
    for pat in BLOCKED_URL_RE:
        if pat.search(low):
            return False
    if not section_id:
        return False
    patterns = SECTION_ARTICLE_PATTERNS.get(_section_key(source_id, section_id), [])
    if not patterns:
        return False
    return any(p.search(low) for p in patterns)


def _iter_dates(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def _url_date_in_range(url: str, start: date, end: date) -> bool:
    ud = _date_from_url(url)
    if ud:
        try:
            d = date.fromisoformat(ud)
            return start <= d <= end
        except ValueError:
            pass
    return True


def _publish_in_range(pub: str, url: str, start: date, end: date) -> bool:
    ud = _date_from_url(url)
    if ud:
        try:
            d = date.fromisoformat(ud)
            return start <= d <= end
        except ValueError:
            pass
    if pub:
        try:
            d = date.fromisoformat(pub[:10])
            return start <= d <= end
        except ValueError:
            pass
    return True


def _listing_uses_per_day(section: dict) -> bool:
    """True when listing URL template includes {date} or {date_compact}."""
    for key in ("listing_url", "listing_url_alt", "listing_url_fallback"):
        tpl = section.get(key) or ""
        if "{date_compact}" in tpl or "{date}" in tpl:
            return True
    return False


def _resolve_listing_url(template: str, report_date: date) -> str:
    return (
        template.replace("{date}", report_date.isoformat())
        .replace("{date_compact}", report_date.strftime("%Y%m%d"))
    )


def _is_junk_site_title(title: str) -> bool:
    t = (title or "").strip()
    if not t:
        return True
    if t in JUNK_SITE_TITLES:
        return True
    if re.match(r"^(hkej|hket|mingpao|wenweipo)\.com$", t, re.I):
        return True
    return False


def _is_junk_article_title(title: str) -> bool:
    if _is_junk_site_title(title):
        return True
    if is_opinion_content(title):
        return True
    for pat in (
        r"作者.*搜尋",
        r"理財投資\s*-\s*信報",
        r"地產投資\s*-\s*信報",
    ):
        if re.search(pat, title, re.I):
            return True
    if "作者搜尋" in title or "作者/專欄" in title:
        return True
    return False


def _decode_link_title(text: str, url: str = "") -> str:
    """Decode URL-encoded anchor text or path slug for title_hint."""
    text = (text or "").strip()
    if not text and url:
        text = urlparse(url).path.rsplit("/", 1)[-1]
    text = unquote(text).replace("+", " ").strip()
    return text


def _is_encoded_slug(text: str) -> bool:
    """True if text is mostly percent-encoding without readable Chinese."""
    if not text:
        return True
    decoded = unquote(text).strip()
    if re.search(r"[\u4e00-\u9fff]", decoded):
        return False
    if "%" in text and re.search(r"%[0-9A-Fa-f]{2}", text):
        return True
    if text and not re.search(r"[\u4e00-\u9fff\u3400-\u4dbf]", text):
        if re.fullmatch(r"[\w\-./%]+", text) and len(text) >= 8:
            return True
    return False


def _has_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text or ""))


def _sanitize_display_title(title: str, source_id: str = "") -> str:
    title = (title or "").strip()
    for suffix in (
        " - 香港文匯網",
        " - 文匯網",
        " | 香港文匯網",
        " - 信報網站 hkej.com",
        " - 信報網站",
    ):
        if title.endswith(suffix):
            title = title[: -len(suffix)].strip()
        elif suffix in title:
            title = title.split(suffix)[0].strip()
    if source_id == "hkej" and " - " in title:
        parts = [p.strip() for p in title.split(" - ") if p.strip()]
        if len(parts) >= 2 and parts[0] in ("今日信報", "信報"):
            title = parts[-1]
    return title


def _resolve_title(og: str, h1: str, title_hint: str, source_id: str = "") -> str:
    og = (og or "").strip()
    h1 = (h1 or "").strip()
    hint = _decode_link_title(title_hint)
    if og and not _is_junk_site_title(og):
        return _sanitize_display_title(og, source_id)
    if h1 and not _is_junk_site_title(h1) and len(h1) >= 6:
        return _sanitize_display_title(h1, source_id)
    if hint and len(hint) >= 6 and not _is_encoded_slug(hint):
        return _sanitize_display_title(hint, source_id)
    if og:
        return _sanitize_display_title(og, source_id)
    return _sanitize_display_title(h1 or hint, source_id)


def _clean_article_text(text: str) -> str:
    if not text:
        return ""
    lines = []
    # 只剔除明确的 UI 元数据行（行首匹配），不删含「撰文」的正文
    ui_prefixes = (
        "欄名：", "欄名:", "發布時間", "最後更新", "關注", "儲存文章",
        "分享：", "分享:", "訂閱", "會員專享", "登入以閱讀",
    )
    for line in text.splitlines():
        s = line.strip()
        if not s or len(s) < 2:
            continue
        if any(s.startswith(p) for p in ui_prefixes):
            continue
        if s in ("關注", "儲存文章", "分享"):
            continue
        lines.append(s)
    cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    return cleaned.strip()


def _first_paragraph(text: str, *, skip_prefixes: tuple[str, ...] = ()) -> str:
    if not text:
        return ""
    for line in text.splitlines():
        s = re.sub(r"\s+", " ", line).strip()
        if len(s) < 15:
            continue
        if any(s.startswith(p) for p in skip_prefixes):
            continue
        if s in ("全文", "關注", "儲存文章"):
            continue
        return s
    parts = re.split(r"(?<=[。！？])\s*", text.strip())
    for p in parts:
        s = re.sub(r"\s+", " ", p).strip()
        if len(s) >= 15:
            return s
    return ""


def _make_snippet(body: str, source_id: str) -> str:
    skip = ("文章：", "文章:")
    para = _first_paragraph(body, skip_prefixes=skip)
    base = para or body.strip()
    return base[:300] if base else ""


def _hkej_article_id(url: str) -> str | None:
    m = re.search(r"/article/(\d+)", url or "", re.I)
    return m.group(1) if m else None


def _normalize_title_key(text: str) -> str:
    return re.sub(r"[\s\u3000\-—|｜:：，,．.!！?？'\"“”]+", "", (text or "").lower())


def _titles_match(expected: str, actual: str) -> bool:
    a = _normalize_title_key(expected)
    b = _normalize_title_key(actual)
    if not a or not b:
        return True
    if a in b or b in a:
        return True
    return False


def _looks_like_hkej_article_list(text: str) -> bool:
    """Detect sidebar/list block mistaken as article body."""
    if not text:
        return False
    head = text.strip()[:400]
    if head.startswith("文章：") or head.startswith("文章:"):
        return True
    lines = [ln.strip() for ln in text.splitlines() if len(ln.strip()) > 6]
    if len(lines) < 4:
        return False
    short_lines = sum(
        1
        for ln in lines[:10]
        if len(ln) < 90 and not re.search(r"[。！？]$", ln) and "全文" not in ln
    )
    return short_lines >= 4


async def _read_hkej_article_body(page: Page, soup: BeautifulSoup | None = None) -> str:
    """Prefer #articleDetail / .scrollRead paragraphs only."""
    for sel in (
        "#articleDetail .scrollRead",
        "#articleDetail",
        ".articleDetail .scrollRead",
        ".scrollRead",
    ):
        try:
            loc = page.locator(sel).first
            if await loc.count() == 0:
                continue
            paras: list[str] = []
            p_loc = loc.locator("p")
            count = await p_loc.count()
            if count > 0:
                for i in range(min(count, 20)):
                    t = (await p_loc.nth(i).inner_text()).strip()
                    if len(t) > 15 and "全文" not in t:
                        paras.append(t)
            if paras:
                return "\n\n".join(paras)
            raw = (await loc.inner_text()).strip()
            if len(raw) >= MIN_BODY_LEN and not _looks_like_hkej_article_list(raw):
                return raw
        except Exception:
            continue

    if soup is None:
        try:
            html = await page.content()
            soup = BeautifulSoup(html, "lxml")
        except Exception:
            soup = None
    if soup:
        for sel in (
            "#articleDetail .scrollRead",
            "#articleDetail",
            ".articleDetail .scrollRead",
            ".scrollRead",
        ):
            node = soup.select_one(sel)
            if not node:
                continue
            paras = [
                p.get_text(strip=True)
                for p in node.select("p")
                if len(p.get_text(strip=True)) > 15 and "全文" not in p.get_text()
            ]
            if paras:
                return "\n\n".join(paras[:12])
            raw = node.get_text("\n", strip=True)
            if len(raw) >= MIN_BODY_LEN and not _looks_like_hkej_article_list(raw):
                return raw
    return ""


def _body_for_validation(
    body: str, snippet: str, raw_body: str, title: str, title_hint: str
) -> str:
    cleaned = _clean_article_text(body or snippet or "")
    if len(cleaned) >= MIN_BODY_LEN and _has_chinese(cleaned) and not _is_encoded_slug(cleaned):
        return cleaned
    raw = (raw_body or body or snippet or "").strip()
    if len(raw) >= MIN_BODY_LEN and _has_chinese(raw) and not _is_encoded_slug(raw):
        return raw
    hint = _decode_link_title(title_hint or title)
    if hint and not _is_encoded_slug(hint) and raw and _has_chinese(raw):
        combined = f"{hint}\n\n{raw}"
        if len(combined) >= MIN_BODY_LEN:
            return combined
    # Never pass validation on encoded slug or title-only hint
    return cleaned


def _invalid_reason(
    title: str,
    body: str,
    snippet: str,
    url: str,
    *,
    raw_body: str = "",
    title_hint: str = "",
    source_id: str = "",
) -> str | None:
    title = (title or "").strip()
    if len(title) < 6:
        hint = _decode_link_title(title_hint)
        if hint and len(hint) >= 6 and not _is_encoded_slug(hint):
            title = hint
        else:
            return "title_short"
    if _is_junk_article_title(title):
        return "junk_title"
    text = _body_for_validation(body, snippet, raw_body, title, title_hint)
    if source_id == "hkej" and _looks_like_hkej_article_list(text or raw_body):
        return "junk_content"
    if _looks_like_paywall(text) or _looks_like_paywall(raw_body):
        return "paywall"
    if len(text) < MIN_BODY_LEN:
        return "body_short"
    junk_phrases = ("休刊日", "下載App", "個人中心", "精選作者", "目錄", "訂閱 / 續訂")
    head = text[:200]
    if sum(1 for p in junk_phrases if p in head) >= 2:
        return "junk_content"
    return None


def _is_valid_article(title: str, body: str, snippet: str, url: str) -> bool:
    return _invalid_reason(title, body, snippet, url) is None


async def open_login_browser(source_id: str) -> str:
    _require_playwright()
    from playwright.async_api import async_playwright

    cfg = load_sources_config()["sources"][source_id]
    profile = _profile_path(source_id)
    name = cfg.get("name", source_id)
    pw = await async_playwright().start()
    try:
        context = await pw.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=False,
            viewport={"width": 1400, "height": 900},
        )
    except Exception as exc:
        await pw.stop()
        if _is_profile_lock_error(exc):
            raise ProfileLockedError(source_id, name, str(exc)) from exc
        raise

    await register_login_session(source_id, pw, context, own_pw=True)
    page = context.pages[0] if context.pages else await context.new_page()
    auto, msg = await open_login_flow(page, source_id, cfg)

    if auto and "登入成功" in msg:
        await finish_login_and_release(source_id)
        return msg + " 已自動關閉登入窗口並釋放 profile。"

    if source_id in ("hket", "mingpao"):
        return (
            msg
            + " 完成後請點「完成登入」釋放 profile，或直接開始抓取（將复用此窗口）。"
        )
    return msg + " 完成後請點「完成登入」釋放 profile，再開始抓取。"


async def close_login_browser(source_id: str) -> str:
    return await finish_login_and_release(source_id)


def _links_from_html_regex(
    html: str,
    base_url: str,
    source_id: str,
    section_id: str,
    report_date: date | None = None,
    *,
    enforce_mingpao_date: bool = True,
    filter_log: list[tuple[str, str]] | None = None,
) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    date_compact = report_date.strftime("%Y%m%d") if report_date else ""
    for pat in HTML_ARTICLE_RES.get(source_id, []):
        for m in pat.finditer(html):
            raw_match = m.group(0).split('"')[0].split("'")[0]
            if source_id == "hket" and re.match(r"/?article/\d", raw_match, re.I):
                full = _resolve_href(base_url, raw_match, source_id, section_id)
            elif raw_match.startswith("http"):
                full = raw_match
            else:
                full = _resolve_href(base_url, raw_match, source_id, section_id)
            canon = _canonical_article_url(full)
            if canon in seen:
                continue
            if (
                enforce_mingpao_date
                and source_id == "mingpao"
                and date_compact
                and f"/article/{date_compact}/" not in canon
            ):
                _log_filtered_link(filter_log, canon, "date_mismatch")
                continue
            sid = source_id or _detect_source_id(canon)
            if not _is_article_url(canon, sid, section_id):
                _log_filtered_link(filter_log, canon, "pattern_mismatch")
                continue
            seen.add(canon)
            slug = _decode_link_title("", canon)
            title = slug if slug and not _is_encoded_slug(slug) else canon.rsplit("/", 1)[-1][:80]
            found.append((title[:200], canon))
    if not found:
        for m in re.finditer(r'href=["\']([^"\']+)["\']', html, re.I):
            full = _resolve_href(base_url, m.group(1).strip(), source_id, section_id)
            if not full:
                continue
            canon = _canonical_article_url(full)
            if canon in seen:
                continue
            if (
                enforce_mingpao_date
                and source_id == "mingpao"
                and date_compact
                and f"/article/{date_compact}/" not in canon
            ):
                _log_filtered_link(filter_log, canon, "date_mismatch")
                continue
            sid = source_id or _detect_source_id(canon)
            if not _is_article_url(canon, sid, section_id):
                _log_filtered_link(filter_log, canon, "pattern_mismatch")
                continue
            seen.add(canon)
            slug = _decode_link_title("", canon)
            title = slug if slug and not _is_encoded_slug(slug) else canon.rsplit("/", 1)[-1][:80]
            found.append((title[:200], canon))
    return found


def _log_filtered_link(
    filter_log: list[tuple[str, str]] | None, url: str, reason: str
) -> None:
    if filter_log is not None and len(filter_log) < 20:
        filter_log.append((url[:120], reason))


_HKET_MAIN_LINK_JS = """
() => {
  const isArticleHref = (href) =>
    /inews\\.hket\\.com\\/article\\/\\d+/i.test(href) ||
    /\\/article\\/\\d+/i.test(href) ||
    /invest\\.hket\\.com\\/article\\//i.test(href) ||
    /paper\\.hket\\.com\\/article\\//i.test(href);

  const isExcludedBlock = (el) => {
    let p = el;
    while (p && p !== document.body) {
      const head = (p.innerText || '').trim().slice(0, 120);
      if (/^熱門文章|^热门文章|^熱門|^人氣|^即時新聞|^编辑推荐/.test(head)) return true;
      if (head.includes('熱門文章') || head.includes('热门文章') || head.includes('點擊排行') || head.includes('点击排行')) return true;
      if (p.tagName === 'ASIDE') return true;
      const cls = (p.className || '').toString();
      const id = (p.id || '').toString();
      if (/hotArticle|hot-article|popular|sidebar|side-bar|sideBar|rank|recommend|right-col|rightCol|widget/i.test(cls + id)) {
        return true;
      }
      p = p.parentElement;
    }
    return false;
  };

  const roots = [
    document.querySelector('.article-list'),
    document.querySelector('.news-list'),
    document.querySelector('[class*="ArticleList"]'),
    document.querySelector('[class*="article-list"]'),
    document.querySelector('.listing-content'),
    document.querySelector('.list-content'),
    document.querySelector('main'),
    document.querySelector('#content'),
  ].filter(Boolean);

  const root = roots[0] || document.body;
  const out = [];
  const seen = new Set();
  root.querySelectorAll('a[href]').forEach((a) => {
    if (isExcludedBlock(a) || a.closest('aside, [class*="sidebar"], [class*="side-bar"], [class*="rank"]')) return;
    const href = a.href || '';
    if (!href || !isArticleHref(href) || seen.has(href)) return;
    seen.add(href);
    out.push({ href, text: (a.innerText || a.textContent || '').trim() });
  });
  return out;
}
"""

_HKEJ_MAIN_LINK_JS = """
() => {
  const isArticleHref = (href) =>
    /hkej\\.com\\/dailynews\\/[^/]+\\/article\\/\\d+/i.test(href);

  const isExcludedBlock = (el) => {
    let p = el;
    while (p && p !== document.body) {
      const head = (p.innerText || '').slice(0, 300);
      if (/點擊排行|点击排行|熱門文章|热门文章|人氣文章|精選作者|相關文章/.test(head)) return true;
      if (p.tagName === 'ASIDE') return true;
      const cls = (p.className || '').toString();
      if (/rank|sidebar|side-bar|hot-list|click-rank|popular|recommend|right/i.test(cls)) return true;
      p = p.parentElement;
    }
    return false;
  };

  const roots = [
    document.querySelector('main'),
    document.querySelector('#content'),
    document.querySelector('.content'),
    document.querySelector('.article-list'),
  ].filter(Boolean);
  const root = roots[0] || document.body;
  const out = [];
  const seen = new Set();
  root.querySelectorAll('a[href]').forEach((a) => {
    if (isExcludedBlock(a) || a.closest('aside, [class*="sidebar"], [class*="rank"]')) return;
    const href = a.href || '';
    if (!href || !isArticleHref(href) || seen.has(href)) return;
    seen.add(href);
    out.push({ href, text: (a.innerText || a.textContent || '').trim() });
  });
  return out;
}
"""

_MINGPAO_MAIN_LINK_JS = """
() => {
  const isArticleHref = (href) =>
    /news\\.mingpao\\.com\\/pns\\/[^/]+\\/article\\/\\d{8}\\/s00004\\//i.test(href);

  const isExcludedBlock = (el) => {
    let p = el;
    while (p && p !== document.body) {
      const head = (p.innerText || '').slice(0, 300);
      if (/點擊排行|点击排行|熱門|热门|人氣|精選|相關文章|編輯推薦/.test(head)) return true;
      if (p.tagName === 'ASIDE') return true;
      const cls = (p.className || '').toString();
      if (/rank|sidebar|side-bar|hot-list|popular|recommend|right/i.test(cls)) return true;
      p = p.parentElement;
    }
    return false;
  };

  const roots = [
    document.querySelector('main'),
    document.querySelector('.main-content'),
    document.querySelector('#content'),
    document.querySelector('.article-list'),
  ].filter(Boolean);
  const root = roots[0] || document.body;
  const out = [];
  const seen = new Set();
  root.querySelectorAll('a[href]').forEach((a) => {
    if (isExcludedBlock(a) || a.closest('aside, [class*="sidebar"], [class*="rank"]')) return;
    const href = a.href || '';
    if (!href || !isArticleHref(href) || seen.has(href)) return;
    seen.add(href);
    out.push({ href, text: (a.innerText || a.textContent || '').trim() });
  });
  return out;
}
"""

_WENWEIPO_MAIN_LINK_JS = """
() => {
  const isSidebar = (el) => {
    let p = el;
    while (p) {
      const t = (p.innerText || '').slice(0, 300);
      if (t.includes('點擊排行') || t.includes('点击排行') || t.includes('熱門') || t.includes('人氣')) return true;
      if (p.tagName === 'ASIDE') return true;
      const cls = (p.className || '').toString();
      if (/rank|sidebar|side-bar|hot-list|click-rank|popular|recommend|right/i.test(cls)) return true;
      p = p.parentElement;
    }
    return false;
  };
  const roots = [
    document.querySelector('main'),
    document.querySelector('.main-content'),
    document.querySelector('#content'),
    document.querySelector('.content'),
  ].filter(Boolean);
  const root = roots[0] || document.body;
  const out = [];
  const seen = new Set();
  root.querySelectorAll('a[href*="/a/"]').forEach((a) => {
    if (isSidebar(a) || a.closest('aside')) return;
    const href = a.href || '';
    if (!href || seen.has(href)) return;
    seen.add(href);
    out.push({ href, text: (a.innerText || a.textContent || '').trim() });
  });
  return out;
}
"""


async def _extract_hket_links(
    page: Page,
    base_url: str,
    section_id: str,
    filter_log: list[tuple[str, str]] | None = None,
) -> list[tuple[str, str]]:
    """Main listing only; exclude 熱門文章 / sidebar (no full-page HTML scan)."""
    links: list[tuple[str, str]] = []
    seen: set[str] = set()
    try:
        anchors = await page.evaluate(_HKET_MAIN_LINK_JS)
    except Exception:
        anchors = []
    for item in anchors:
        href = (item.get("href") or "").strip()
        text = (item.get("text") or "").strip()
        if not href:
            continue
        full = _resolve_href(base_url, href, "hket", section_id)
        if not full:
            continue
        canon = _canonical_article_url(full)
        if canon in seen:
            continue
        if not _is_article_url(canon, "hket", section_id):
            _log_filtered_link(filter_log, canon, "pattern_mismatch")
            continue
        text = _decode_link_title(text)
        if text and any(x in text for x in SKIP_TEXT_PARTS):
            continue
        seen.add(canon)
        links.append((text[:200] if text else canon.rsplit("/", 1)[-1][:80], canon))
    return links[:HKET_MAX_LINKS_PER_SECTION]


async def _extract_hkej_links(
    page: Page,
    base_url: str,
    section_id: str,
    filter_log: list[tuple[str, str]] | None = None,
) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    seen: set[str] = set()
    try:
        anchors = await page.evaluate(_HKEJ_MAIN_LINK_JS)
    except Exception:
        anchors = []
    for item in anchors:
        href = (item.get("href") or "").strip()
        text = (item.get("text") or "").strip()
        if not href:
            continue
        full = _resolve_href(base_url, href, "hkej", section_id)
        if not full:
            continue
        canon = _canonical_article_url(full)
        if canon in seen:
            continue
        if not _is_article_url(canon, "hkej", section_id):
            _log_filtered_link(filter_log, canon, "pattern_mismatch")
            continue
        text = _decode_link_title(text)
        if text and any(x in text for x in SKIP_TEXT_PARTS):
            continue
        seen.add(canon)
        links.append((text[:200] if text else canon.rsplit("/", 1)[-1][:80], canon))
    return links


async def _extract_mingpao_links(
    page: Page,
    base_url: str,
    section_id: str,
    filter_log: list[tuple[str, str]] | None = None,
) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    seen: set[str] = set()
    try:
        anchors = await page.evaluate(_MINGPAO_MAIN_LINK_JS)
    except Exception:
        anchors = []
    for item in anchors:
        href = (item.get("href") or "").strip()
        text = (item.get("text") or "").strip()
        if not href:
            continue
        full = _resolve_href(base_url, href, "mingpao", section_id)
        if not full:
            continue
        canon = _canonical_article_url(full)
        if canon in seen:
            continue
        if not _is_article_url(canon, "mingpao", section_id):
            _log_filtered_link(filter_log, canon, "pattern_mismatch")
            continue
        text = _decode_link_title(text)
        if text and any(x in text for x in SKIP_TEXT_PARTS):
            continue
        seen.add(canon)
        links.append((text[:200] if text else canon.rsplit("/", 1)[-1][:80], canon))
    return links


async def _extract_wenweipo_links(
    page: Page,
    base_url: str,
    section_id: str,
    filter_log: list[tuple[str, str]] | None = None,
) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    seen: set[str] = set()
    try:
        anchors = await page.evaluate(_WENWEIPO_MAIN_LINK_JS)
    except Exception:
        anchors = []
    for item in anchors:
        href = (item.get("href") or "").strip()
        text = (item.get("text") or "").strip()
        if not href:
            continue
        full = _resolve_href(base_url, href, "wenweipo", section_id)
        if not full:
            continue
        canon = _canonical_article_url(full)
        if canon in seen:
            continue
        if not _is_article_url(canon, "wenweipo", section_id):
            _log_filtered_link(filter_log, canon, "pattern_mismatch")
            continue
        text = _decode_link_title(text)
        if text and any(x in text for x in SKIP_TEXT_PARTS):
            continue
        seen.add(canon)
        links.append((text[:200] if text else canon.rsplit("/", 1)[-1][:80], canon))
    return links


async def _extract_links_from_page(
    page: Page,
    base_url: str,
    source_id: str,
    section_id: str,
    report_date: date | None = None,
    *,
    enforce_mingpao_date: bool = True,
    filter_log: list[tuple[str, str]] | None = None,
    section_max_links: int | None = None,
) -> list[tuple[str, str]]:
    if source_id == "wenweipo":
        links = await _extract_wenweipo_links(
            page, base_url, section_id, filter_log=filter_log
        )
        cap = section_max_links or MAX_LINKS_PER_SECTION
        return links[:cap]

    if source_id == "hket":
        links = await _extract_hket_links(
            page, base_url, section_id, filter_log=filter_log
        )
        cap = section_max_links or HKET_MAX_LINKS_PER_SECTION
        return links[:cap]

    if source_id == "hkej":
        links = await _extract_hkej_links(
            page, base_url, section_id, filter_log=filter_log
        )
        if not links:
            links = await _extract_links_fallback(
                page, base_url, source_id, section_id, report_date,
                enforce_mingpao_date=enforce_mingpao_date,
                filter_log=filter_log,
            )
        cap = section_max_links or MAX_LINKS_PER_SECTION
        return links[:cap]

    if source_id == "mingpao":
        links = await _extract_mingpao_links(
            page, base_url, section_id, filter_log=filter_log
        )
        if not links:
            links = await _extract_links_fallback(
                page, base_url, source_id, section_id, report_date,
                enforce_mingpao_date=enforce_mingpao_date,
                filter_log=filter_log,
            )
        cap = section_max_links or MAX_LINKS_PER_SECTION
        return links[:cap]

    links = await _extract_links_fallback(
        page, base_url, source_id, section_id, report_date,
        enforce_mingpao_date=enforce_mingpao_date,
        filter_log=filter_log,
    )
    cap = section_max_links or MAX_LINKS_PER_SECTION
    return links[:cap]


async def _extract_links_fallback(
    page: Page,
    base_url: str,
    source_id: str,
    section_id: str,
    report_date: date | None = None,
    *,
    enforce_mingpao_date: bool = True,
    filter_log: list[tuple[str, str]] | None = None,
) -> list[tuple[str, str]]:
    """Fallback anchor scan when main-list JS returns no links."""
    selectors = [
        "main a[href]",
        "article a[href]",
        ".article-list a[href]",
        ".news-list a[href]",
        ".content a[href]",
        "#content a[href]",
    ]
    links: list[tuple[str, str]] = []
    seen: set[str] = set()
    min_text_len = 4 if source_id == "mingpao" else 6
    date_compact = report_date.strftime("%Y%m%d") if report_date else ""

    for sel in selectors:
        try:
            anchors = await page.eval_on_selector_all(
                sel,
                """els => els.map(a => ({
                    href: a.href,
                    text: (a.innerText || a.textContent || '').trim()
                }))""",
            )
        except Exception:
            continue
        for item in anchors:
            href = (item.get("href") or "").strip()
            text = (item.get("text") or "").strip()
            if not href:
                continue
            full = _resolve_href(base_url, href, source_id, section_id)
            if not full:
                continue
            canon = _canonical_article_url(full)
            if canon in seen:
                continue
            if (
                enforce_mingpao_date
                and source_id == "mingpao"
                and date_compact
                and f"/article/{date_compact}/" not in canon
            ):
                _log_filtered_link(filter_log, canon, "date_mismatch")
                continue
            sid = source_id or _detect_source_id(canon)
            if not _is_article_url(canon, sid, section_id):
                _log_filtered_link(filter_log, canon, "pattern_mismatch")
                continue
            text = _decode_link_title(text)
            if len(text) < min_text_len:
                slug = _decode_link_title("", canon)
                if slug and len(slug) >= min_text_len and not _is_encoded_slug(slug):
                    text = slug
                elif source_id not in ("hket", "mingpao", "hkej"):
                    continue
                else:
                    text = ""
            if text and any(x in text for x in SKIP_TEXT_PARTS):
                continue
            seen.add(canon)
            links.append((text[:200], canon))

    html_content = ""
    try:
        html_content = await page.content()
        regex_links = _links_from_html_regex(
            html_content,
            base_url,
            source_id,
            section_id,
            report_date,
            enforce_mingpao_date=enforce_mingpao_date,
            filter_log=filter_log,
        )
        for text, canon in regex_links:
            if canon not in seen:
                seen.add(canon)
                links.append((text, canon))
    except Exception:
        pass

    if source_id in ("mingpao", "hkej"):
        if not html_content:
            try:
                html_content = await page.content()
            except Exception:
                html_content = ""
        if html_content:
            for canon in _scan_html_for_article_urls(
                html_content, base_url, source_id, section_id
            ):
                if canon not in seen:
                    if (
                        enforce_mingpao_date
                        and source_id == "mingpao"
                        and report_date
                        and f"/article/{report_date.strftime('%Y%m%d')}/" not in canon
                    ):
                        _log_filtered_link(filter_log, canon, "date_mismatch")
                        continue
                    if not _is_article_url(canon, source_id, section_id):
                        _log_filtered_link(filter_log, canon, "pattern_mismatch")
                        continue
                    seen.add(canon)
                    title = _decode_link_title("", canon)
                    if _is_encoded_slug(title):
                        title = ""
                    links.append((title[:200], canon))

    if (
        not links
        and source_id == "mingpao"
        and enforce_mingpao_date
        and report_date
    ):
        try:
            if not html_content:
                html_content = await page.content()
            relaxed = _links_from_html_regex(
                html_content,
                base_url,
                source_id,
                section_id,
                report_date,
                enforce_mingpao_date=False,
                filter_log=filter_log,
            )
            for text, canon in relaxed:
                if _url_date_in_range(canon, report_date, report_date) and canon not in seen:
                    if _is_article_url(canon, source_id, section_id):
                        seen.add(canon)
                        links.append((text, canon))
        except Exception:
            pass

    return links[:MAX_LINKS_PER_SECTION]


async def _scroll_listing_page(page: Page, source_id: str) -> None:
    """Lazy-loaded listings need scroll + wait before link extraction."""
    if source_id not in ("mingpao", "hket"):
        return
    scroll_rounds = 4 if source_id == "hket" else 5
    for _ in range(scroll_rounds):
        try:
            await page.evaluate(
                "window.scrollBy(0, Math.max(document.body.scrollHeight, 1200) / 4)"
            )
        except Exception:
            pass
        await page.wait_for_timeout(800 if source_id == "hket" else 600)

    if source_id == "hket":
        selectors = (
            'a[href*="inews.hket.com/article"]',
            'a[href*="invest.hket.com/article"]',
            'a[href*="paper.hket.com/article"]',
            'a[href*="/article/"]',
            ".article-list a",
            ".news-list a",
            "main a[href]",
        )
    else:
        selectors = (
            'a[href*="/article/"]',
            ".article-list a",
            ".news-list a",
            "main a[href]",
        )
    for sel in selectors:
        try:
            await page.wait_for_selector(sel, timeout=12000 if source_id == "hket" else 8000)
            break
        except Exception:
            continue
    await page.wait_for_timeout(2500 if source_id == "hket" else 1500)


def _parse_publish_date(soup: BeautifulSoup) -> str | None:
    meta_keys = [
        ("property", "article:published_time"),
        ("property", "og:published_time"),
        ("name", "pubdate"),
        ("name", "publishdate"),
        ("name", "date"),
    ]
    for attr, val in meta_keys:
        tag = soup.find("meta", {attr: val})
        if tag and tag.get("content"):
            d = _normalize_date(tag["content"])
            if d:
                return d
    for sel in ["time[datetime]", "time", ".date", ".publish-date", ".article-date"]:
        tag = soup.select_one(sel)
        if tag:
            raw = tag.get("datetime") or tag.get_text(strip=True)
            d = _normalize_date(raw)
            if d:
                return d
    return None


def _normalize_date(raw: str) -> str | None:
    if not raw:
        return None
    raw = raw.strip()[:40]
    if "T" in raw:
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if dt.tzinfo is not None:
                return dt.astimezone(HKT).date().isoformat()
            return dt.date().isoformat()
        except ValueError:
            pass
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw[:10], fmt).date().isoformat()
        except ValueError:
            continue
    m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", raw)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
    m = re.search(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", raw)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return date(y, mo, d).isoformat()
    m2 = re.search(r"/a/(\d{4})(\d{2})/(\d{2})/", raw)
    if m2:
        return date(int(m2.group(1)), int(m2.group(2)), int(m2.group(3))).isoformat()
    m3 = re.search(r"/article/(\d{8})/", raw)
    if m3:
        s = m3.group(1)
        return date(int(s[:4]), int(s[4:6]), int(s[6:8])).isoformat()
    return None


def _hket_article_origin(section_id: str) -> str:
    if section_id == "instant_news":
        return "https://inews.hket.com"
    if section_id == "property":
        return "https://paper.hket.com"
    return "https://invest.hket.com"


def _resolve_href(
    base_url: str, href: str, source_id: str = "", section_id: str = ""
) -> str:
    """Resolve href; fix HKET relative article paths to correct domain."""
    href = (href or "").strip()
    if not href or href.startswith("#") or href.lower().startswith("javascript"):
        return ""
    if href.startswith("http"):
        return href
    parsed = urlparse(base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if source_id == "hket" and re.match(r"/?article/\d", href, re.I):
        horigin = _hket_article_origin(section_id or "finance_invest")
        return f"{horigin}/{href.lstrip('/')}"
    if href.startswith("/"):
        return origin + href
    if re.match(r"(article/\d|dailynews/|pns/|a/\d{6}/)", href, re.I):
        return f"{origin}/{href.lstrip('/')}"
    return urljoin(base_url, href)


def _scan_html_for_article_urls(
    html: str, base_url: str, source_id: str, section_id: str
) -> list[str]:
    """Deep-scan rendered HTML/JSON for article URLs missed by anchor extraction."""
    found: list[str] = []
    seen: set[str] = set()
    patterns: list[str] = [
        r"https?://[^\"'\\s<>]+/article/\d+[^\"'\\s<]*",
        r'["\']/(article/\d+[^"\']*)',
        r'["\'](article/\d+[^"\']*)',
    ]
    if source_id == "hket":
        patterns.extend(
            [
                r"https?://inews\.hket\.com/article/\d+[^\"'\\s<]*",
                r"https?://invest\.hket\.com/article/\d+[^\"'\\s<]*",
                r"https?://paper\.hket\.com/article/\d+[^\"'\\s<]*",
            ]
        )
    if source_id == "mingpao":
        patterns.extend(
            [
                r"https?://news\.mingpao\.com/pns/[^\"'\\s<>]+/article/\d{8}/s00004/[^\"'\\s<>]+",
                r'["\'](/pns/[^"\']+/article/\d{8}/s00004/[^"\']*)',
            ]
        )
    if source_id == "hkej":
        patterns.append(
            r"https?://www\.hkej\.com/dailynews/[^\"'\\s<>]+/article/\d+[^\"'\\s<]*"
        )
    for pat in patterns:
        for m in re.finditer(pat, html, re.I):
            raw = (m.group(1) if m.lastindex else m.group(0)).strip("\"'")
            if raw.startswith("http"):
                full = raw.split('"')[0].split("'")[0]
            else:
                full = _resolve_href(base_url, raw, source_id, section_id)
            if not full:
                continue
            canon = _canonical_article_url(full)
            if canon in seen:
                continue
            sid = source_id or _detect_source_id(canon)
            if not _is_article_url(canon, sid, section_id):
                continue
            seen.add(canon)
            found.append(canon)
    return found


def _canonical_article_url(url: str) -> str:
    """Strip tracking query params; keep path for dedup."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")


def _date_from_url(url: str) -> str | None:
    low = url.lower()
    m = re.search(r"/a/(\d{4})(\d{2})/(\d{2})/", low)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
    m = re.search(r"/article/(\d{8})/", low)
    if m:
        s = m.group(1)
        return date(int(s[:4]), int(s[4:6]), int(s[6:8])).isoformat()
    return None


def _date_matches_report(url: str, pub: str, report_iso: str) -> bool:
    url_date = _date_from_url(url)
    if url_date:
        return url_date == report_iso
    if not pub:
        return True
    try:
        pub_d = date.fromisoformat(pub[:10])
        rep_d = date.fromisoformat(report_iso)
        return abs((pub_d - rep_d).days) <= DATE_TOLERANCE_DAYS
    except ValueError:
        return pub[:10] == report_iso[:10]


async def _read_article_body(page: Page, sid: str) -> str:
    text = ""
    for sel in BODY_SELECTORS.get(sid, BODY_SELECTORS.get("hket", [])):
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0:
                raw = await loc.inner_text()
                if len(raw.strip()) > len(text):
                    text = raw
        except Exception:
            continue
    if len(text.strip()) < MIN_BODY_LEN:
        try:
            text = await page.evaluate(
                """() => {
                    const sels = ['article', 'main', '[class*="article"]', '[class*="content"]'];
                    let best = '';
                    for (const s of sels) {
                        document.querySelectorAll(s).forEach(el => {
                            const t = (el.innerText || '').trim();
                            if (t.length > best.length) best = t;
                        });
                    }
                    return best;
                }"""
            ) or ""
        except Exception:
            pass
    return text.strip()


async def fetch_article_detail(
    context: BrowserContext,
    url: str,
    title_hint: str = "",
    source_id: str = "",
    *,
    pw=None,
    source_name: str = "",
) -> tuple[str, str, str, str, str]:
    """Returns title, body, snippet, pub, raw_body. Retries for member full text."""
    sid = source_id or _detect_source_id(url)
    last_result = ("", "", "", "", "")
    needs_login_ctx = sid in ("hket", "mingpao")

    for attempt in range(3):
        if needs_login_ctx and pw is not None:
            context = await _get_fetch_context(
                pw, sid, True, source_name or sid
            )
        try:
            page = await context.new_page()
        except Exception as exc:
            if needs_login_ctx and pw is not None:
                context = await _get_fetch_context(
                    pw, sid, True, source_name or sid
                )
                page = await context.new_page()
            else:
                raise exc
        try:
            wait_ms = 2500 + attempt * 1500
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(wait_ms)
            if sid == "hkej":
                for sel in ("#articleDetail", ".scrollRead", "#article-content"):
                    try:
                        await page.wait_for_selector(sel, timeout=6000)
                        break
                    except Exception:
                        continue
            elif sid == "hket":
                for sel in (
                    "#article-content",
                    ".article-content",
                    "[itemprop='articleBody']",
                    ".subscriber-content",
                ):
                    try:
                        await page.wait_for_selector(sel, timeout=6000)
                        break
                    except Exception:
                        continue

            pub = _date_from_url(url) or ""
            og_title = ""
            try:
                og_title = await page.locator('meta[property="og:title"]').get_attribute("content") or ""
            except Exception:
                pass
            h1_title = ""
            for sel in ("h1", ".article-title", ".headline"):
                try:
                    loc = page.locator(sel).first
                    if await loc.count() > 0:
                        h1_title = (await loc.inner_text()).strip()
                        if h1_title and len(h1_title) >= 6:
                            break
                except Exception:
                    continue
            title = _resolve_title(og_title, h1_title, title_hint, sid)
            if sid == "hkej" and (len(title) < 6 or _is_junk_site_title(title)):
                try:
                    title = _sanitize_display_title(await page.title(), sid)
                except Exception:
                    pass
            if sid == "hkej" and h1_title and title and not _titles_match(title, h1_title):
                title = _sanitize_display_title(h1_title, sid)

            html = ""
            soup = None
            if sid == "hkej":
                html = await page.content()
                soup = BeautifulSoup(html, "lxml")
                text = await _read_hkej_article_body(page, soup)
            else:
                text = await _read_article_body(page, sid)

            if len(text.strip()) < MIN_BODY_LEN:
                if not html:
                    html = await page.content()
                if soup is None:
                    soup = BeautifulSoup(html, "lxml")
                if not pub:
                    pub = _parse_publish_date(soup) or ""
                if _is_junk_site_title(title):
                    og = soup.find("meta", property="og:title")
                    og_val = (og["content"] if og and og.get("content") else "").strip()
                    h1 = soup.select_one("h1")
                    h1_val = h1.get_text(strip=True) if h1 else ""
                    title = _resolve_title(og_val, h1_val, title_hint, sid)
                for tag in soup.select("script, style, nav, footer, aside"):
                    tag.decompose()
                for sel in BODY_SELECTORS.get(sid, []):
                    node = soup.select_one(sel)
                    if node and len(node.get_text(strip=True)) > len(text):
                        text = node.get_text("\n", strip=True)
                if len(text.strip()) < MIN_BODY_LEN:
                    article = soup.select_one("article") or soup.select_one("main")
                    if article:
                        text = article.get_text("\n", strip=True)
                if len(text.strip()) < MIN_BODY_LEN:
                    for meta_sel in (
                        ("meta", {"property": "og:description"}),
                        ("meta", {"name": "description"}),
                        ("meta", {"property": "twitter:description"}),
                    ):
                        tag = soup.find(meta_sel[0], meta_sel[1])
                        if tag and tag.get("content"):
                            desc = tag["content"].strip()
                            if len(desc) > len(text):
                                text = desc
                if sid == "hkej" and len(text.strip()) < MIN_BODY_LEN:
                    text = await _read_hkej_article_body(page, soup)

            raw_body = text.strip()
            if sid == "hkej" and _looks_like_hkej_article_list(raw_body):
                raw_body = ""
                text = ""

            cleaned = _clean_article_text(raw_body)
            body = cleaned if len(cleaned) >= MIN_BODY_LEN and _has_chinese(cleaned) else raw_body
            if len(body) < MIN_BODY_LEN and raw_body and _has_chinese(raw_body):
                body = cleaned if len(cleaned) >= MIN_BODY_LEN else raw_body
            title = _sanitize_display_title(title, sid)
            snippet = _make_snippet(body, sid) if body else ""
            last_result = (title[:300], body[:8000], snippet, pub, raw_body[:8000])
            if (
                len(body) >= MIN_BODY_LEN
                and _has_chinese(body)
                and not (sid == "hkej" and _looks_like_hkej_article_list(body))
            ):
                return last_result
        except Exception:
            pass
        finally:
            await page.close()

    return last_result


async def _fetch_listing(
    context: BrowserContext,
    url: str,
    source_id: str,
    section_id: str,
    report_date: date | None = None,
    *,
    needs_login: bool = False,
    source_name: str = "",
    pw=None,
    section_max_links: int | None = None,
) -> list[tuple[str, str]]:
    if needs_login and source_id in ("hket", "mingpao") and pw is not None:
        context = await _get_fetch_context(
            pw, source_id, True, source_name or source_id
        )
    page = await context.new_page()
    filter_log: list[tuple[str, str]] = []
    try:
        if source_id == "hket":
            await page.goto(url, wait_until="domcontentloaded", timeout=50000)
        else:
            try:
                await page.goto(url, wait_until="networkidle", timeout=45000)
            except Exception:
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
    except Exception as exc:
        print(f"[fetch] listing goto failed {url}: {exc}")
        await page.close()
        return []
    try:
        wait_ms = 7000 if source_id == "hket" else (5000 if source_id == "mingpao" else 2500)
        await page.wait_for_timeout(wait_ms)
        await _scroll_listing_page(page, source_id)
        links = await _extract_links_from_page(
            page, url, source_id, section_id, report_date,
            filter_log=filter_log, section_max_links=section_max_links,
        )
        if not links and source_id in ("hket", "mingpao"):
            try:
                html_len = len(await page.content())
            except Exception:
                html_len = 0
            print(
                f"[fetch] {source_id} listing 0 links (html_len={html_len}) — "
                f"retry scroll {url}"
            )
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(3000)
            links = await _extract_links_from_page(
                page, url, source_id, section_id, report_date,
                filter_log=filter_log, section_max_links=section_max_links,
            )
        if filter_log:
            sample = "; ".join(f"{u} ({r})" for u, r in filter_log[:6])
            print(f"[fetch] {source_id} filtered links sample: {sample}")
        if not links:
            try:
                html = await page.content()
            except Exception:
                html = ""
            fail = await _listing_failure_reason(
                page, source_id, html, needs_login=needs_login
            )
            if fail in ("login_required", "paywall") and needs_login:
                label = (
                    "未登入或 session 已失效"
                    if fail == "login_required"
                    else "偵測到付費牆（可能未登入）"
                )
                raise LoginRequiredError(
                    source_id,
                    source_name or source_id,
                    f"列表頁 0 連結：{label}。請先登入後按「繼續」。",
                )
            if fail == "no_links":
                print(f"[fetch] {source_id} listing: genuinely 0 links at {url}")
        return links
    except LoginRequiredError:
        raise
    except Exception as exc:
        print(f"[fetch] listing failed {url}: {exc}")
        return []
    finally:
        await page.close()


def _section_listing_urls(section: dict, report_date: date) -> list[str]:
    urls: list[str] = []
    primary = section.get("listing_url")
    if primary:
        urls.append(_resolve_listing_url(primary, report_date))
    alt = section.get("listing_url_alt")
    if alt:
        urls.append(_resolve_listing_url(alt, report_date))
    return urls


async def _fetch_section_links(
    context: BrowserContext,
    section: dict,
    source_id: str,
    date_start: date,
    date_end: date,
    *,
    needs_login: bool = False,
    source_name: str = "",
    pw=None,
) -> list[tuple[str, str]]:
    """Fetch links from listing page(s) within date range."""
    section_id = section["id"]
    sec_label = section.get("label", section_id)
    section_cap = section.get("max_links")
    all_links: list[tuple[str, str]] = []
    seen: set[str] = set()

    if _listing_uses_per_day(section):
        for d in _iter_dates(date_start, date_end):
            day_added = 0
            for listing in _section_listing_urls(section, d):
                batch = await _fetch_listing(
                    context,
                    listing,
                    source_id,
                    section_id,
                    d,
                    needs_login=needs_login,
                    source_name=source_name,
                    pw=pw,
                    section_max_links=section_cap,
                )
                print(f"[fetch] {source_id}/{sec_label}: {len(batch)} links from {listing}")
                job_progress.source_update(
                    source_id, f"{sec_label} · {listing.split('?')[0][-40:]}… {len(batch)} 鏈"
                )
                for title, url in batch:
                    if url not in seen:
                        seen.add(url)
                        all_links.append((title, url))
                        day_added += 1
            if day_added == 0:
                fb = section.get("listing_url_fallback")
                if fb:
                    listing = _resolve_listing_url(fb, d)
                    batch = await _fetch_listing(
                        context,
                        listing,
                        source_id,
                        section_id,
                        d,
                        needs_login=needs_login,
                        source_name=source_name,
                        pw=pw,
                        section_max_links=section_cap,
                    )
                    print(
                        f"[fetch] {source_id}/{sec_label}: {len(batch)} links (fallback) "
                        f"from {listing}"
                    )
                    for title, url in batch:
                        if url not in seen:
                            seen.add(url)
                            all_links.append((title, url))
    else:
        for listing in _section_listing_urls(section, date_end):
            batch = await _fetch_listing(
                context,
                listing,
                source_id,
                section_id,
                date_end,
                needs_login=needs_login,
                source_name=source_name,
                pw=pw,
                section_max_links=section_cap,
            )
            print(f"[fetch] {source_id}/{sec_label}: {len(batch)} links from {listing}")
            job_progress.source_update(
                source_id, f"{sec_label} · {len(batch)} 鏈"
            )
            for title, url in batch:
                if url not in seen:
                    seen.add(url)
                    all_links.append((title, url))

        if not all_links:
            fb = section.get("listing_url_fallback")
            if fb:
                listing = _resolve_listing_url(fb, date_end)
                batch = await _fetch_listing(
                    context,
                    listing,
                    source_id,
                    section_id,
                    date_end,
                    needs_login=needs_login,
                    source_name=source_name,
                    pw=pw,
                    section_max_links=section_cap,
                )
                print(
                    f"[fetch] {source_id}/{sec_label}: {len(batch)} links (fallback) "
                    f"from {listing}"
                )
                for title, url in batch:
                    if url not in seen:
                        seen.add(url)
                        all_links.append((title, url))

    filtered: list[tuple[str, str]] = []
    for title, url in all_links:
        if _url_date_in_range(url, date_start, date_end):
            filtered.append((title, url))
    cap = section_cap or (
        HKET_MAX_LINKS_PER_SECTION if source_id == "hket" else MAX_LINKS_PER_SECTION
    )
    return filtered[:cap]


async def fetch_source(
    source_id: str,
    date_start: date | None = None,
    date_end: date | None = None,
    progress_base: int = 0,
    progress_span: int = 25,
) -> list[RawArticle]:
    _require_playwright()
    from playwright.async_api import async_playwright

    date_end = date_end or date.today()
    date_start = date_start or date_end
    if date_start > date_end:
        date_start, date_end = date_end, date_start

    cfg = load_sources_config()["sources"][source_id]
    needs_login = cfg.get("requires_login", True)
    articles: list[RawArticle] = []
    seen_urls: set[str] = set()
    link_candidates: list[tuple[str, str, str, str, bool]] = []
    skip: dict[str, int] = {
        "title_short": 0,
        "body_short": 0,
        "paywall": 0,
        "junk_title": 0,
        "junk_content": 0,
        "date": 0,
        "title_prefilter": 0,
    }
    kw_cfg = load_keywords_config()
    debug_done = False

    range_label = (
        date_start.isoformat()
        if date_start == date_end
        else f"{date_start.isoformat()}–{date_end.isoformat()}"
    )
    job_progress.update(progress_base, f"抓取 {cfg['name']}", f"讀取列表頁 ({range_label})…")
    job_progress.source_start(source_id, f"登入檢查 · 列表 ({range_label})")

    async with async_playwright() as pw:
        browser, context = await _launch_fetch_context(
            pw, source_id, needs_login, cfg["name"]
        )

        try:
            await job_progress.wait_if_paused()

            if needs_login:
                if source_id in ("hket", "mingpao"):
                    context = await _get_fetch_context(
                        pw, source_id, True, cfg["name"]
                    )
                logged_in = await ensure_logged_in(context, source_id, cfg)
                if not logged_in:
                    raise LoginRequiredError(
                        source_id,
                        cfg["name"],
                        "Session 失效或未登入。請在儀表板點「登入」或檢查 .env 帳密，完成後按「繼續」。",
                    )

            job_progress.source_update(source_id, "讀取列表頁…")
            for section in cfg.get("sections", []):
                await job_progress.wait_if_paused()
                sec_label = section.get("label", section["id"])
                sec_type = section.get("section_type", "finance")
                job_progress.source_update(source_id, f"列表：{sec_label}")
                if needs_login and source_id in ("hket", "mingpao"):
                    context = await _get_fetch_context(
                        pw, source_id, True, cfg["name"]
                    )
                links = await _fetch_section_links(
                    context,
                    section,
                    source_id,
                    date_start,
                    date_end,
                    needs_login=needs_login,
                    source_name=cfg["name"],
                    pw=pw,
                )
                for title, url in links:
                    title = _decode_link_title(title, url)
                    if url not in seen_urls:
                        seen_urls.add(url)
                        prefilter = section.get("title_prefilter", True)
                        link_candidates.append(
                            (title, url, sec_label, sec_type, prefilter)
                        )

            total = max(len(link_candidates), 1)
            job_progress.source_update(source_id, f"正文 {total} 篇")
            for idx, (title_hint, url, sec_label, sec_type, title_prefilter) in enumerate(
                link_candidates
            ):
                await job_progress.wait_if_paused()
                pct = progress_base + int((idx + 1) / total * progress_span)
                job_progress.update(pct, f"抓取 {cfg['name']}", f"文章 {idx + 1}/{total}")
                job_progress.source_update(source_id, f"正文 {idx + 1}/{total}")

                if title_prefilter and not title_passes_listing_gate(
                    title_hint, sec_type, kw_cfg
                ):
                    skip["title_prefilter"] += 1
                    continue

                title, body, snippet, pub, raw_body = await fetch_article_detail(
                    context,
                    url,
                    title_hint,
                    source_id=source_id,
                    pw=pw,
                    source_name=cfg["name"],
                )
                if _is_junk_site_title(title) and title_hint and len(title_hint) >= 6:
                    hint = _decode_link_title(title_hint)
                    if hint and not _is_encoded_slug(hint):
                        title = hint
                title = _sanitize_display_title(title, source_id)
                reason = _invalid_reason(
                    title,
                    body,
                    snippet,
                    url,
                    raw_body=raw_body,
                    title_hint=title_hint,
                    source_id=source_id,
                )
                if reason:
                    skip[reason] = skip.get(reason, 0) + 1
                    if not debug_done:
                        debug_done = True
                        clean_len = len(_clean_article_text(raw_body or body))
                        print(
                            f"[fetch] debug {source_id}: {reason} url={url[:80]} "
                            f"title_len={len(title)} body_len={len(body)} "
                            f"raw_len={len(raw_body)} clean_len={clean_len} "
                            f"title={title[:50]!r}"
                        )
                    continue
                if not _publish_in_range(pub, url, date_start, date_end):
                    skip["date"] += 1
                    continue
                pub = _date_from_url(url) or pub or date_end.isoformat()

                articles.append(
                    RawArticle(
                        title=title,
                        url=url,
                        source_name=cfg["name"],
                        source_id=source_id,
                        section_label=sec_label,
                        section_type=sec_type,
                        credibility=cfg.get("credibility", "A"),
                        publish_date=pub,
                        body=body,
                        snippet=snippet,
                    )
                )

            if (
                needs_login
                and link_candidates
                and not articles
                and skip.get("paywall", 0) > 0
            ):
                raise LoginRequiredError(
                    source_id,
                    cfg["name"],
                    f"共 {len(link_candidates)} 連結但均為付費牆摘要（paywall={skip['paywall']}）。"
                    "請登入後按「繼續」重試。",
                )
        finally:
            if source_id in ("hket", "mingpao") and needs_login:
                await release_context(source_id, stop_pw=False)
            else:
                try:
                    await context.close()
                except Exception:
                    pass
            if browser:
                await browser.close()

    job_progress.update(progress_base + progress_span, f"完成 {cfg['name']}", f"{len(articles)} 篇")
    job_progress.source_done(source_id, len(articles))
    print(
        f"[fetch] {source_id}: {len(articles)} articles "
        f"(from {len(link_candidates)} links, skip={skip})"
    )
    return articles


async def fetch_all_sources(
    date_start: date | None = None,
    date_end: date | None = None,
) -> list[RawArticle]:
    date_end = date_end or date.today()
    date_start = date_start or date_end
    if date_start > date_end:
        date_start, date_end = date_end, date_start

    cfg = load_sources_config()
    source_ids = list(cfg["sources"].keys())
    names = {k: v.get("name", k) for k, v in cfg["sources"].items()}
    job_progress.init_sources(source_ids, names)
    total = len(source_ids)
    span = 90 // max(total, 1)
    all_articles: list[RawArticle] = []

    i = 0
    while i < len(source_ids):
        source_id = source_ids[i]
        base = i * span
        await job_progress.wait_if_paused()
        try:
            batch = await fetch_source(
                source_id, date_start, date_end, progress_base=base, progress_span=span
            )
            all_articles.extend(batch)
            i += 1
        except LoginRequiredError as exc:
            msg = str(exc)
            print(f"[fetch] {source_id} login required: {msg}")
            job_progress.source_login_required(source_id, msg)
            job_progress.request_pause(
                f"【{exc.source_name}】需要登入：{msg}"
            )
            await job_progress.wait_if_paused()
            continue
        except ProfileLockedError as exc:
            msg = str(exc)
            print(f"[fetch] {source_id} profile locked: {msg}")
            job_progress.source_login_required(source_id, msg)
            job_progress.request_pause(msg)
            await job_progress.wait_if_paused()
            continue
        except BrowserClosedError as exc:
            msg = str(exc)
            print(f"[fetch] {source_id} browser closed: {msg}")
            job_progress.source_error(source_id, msg)
            job_progress.request_pause(msg)
            await job_progress.wait_if_paused()
            continue
        except Exception as exc:
            print(f"[fetch] {source_id} failed: {exc}")
            job_progress.source_error(source_id, str(exc))
            i += 1

    job_progress.update(92, "評分候選", f"共 {len(all_articles)} 篇")
    return all_articles
