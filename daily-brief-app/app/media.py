"""Article image extraction and screenshot for 阅读原文."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.fetchers import _require_playwright

SKIP_IMG = ("logo", "icon", "avatar", "banner", "ad", "advert", "sprite", "pixel")


async def download_article_image(
    page_html: str,
    page_url: str,
    news_id: str,
    assets_dir: Path,
) -> str:
    """Download og:image or first suitable article img. Returns relative path or ''."""
    assets_dir.mkdir(parents=True, exist_ok=True)
    soup = BeautifulSoup(page_html, "lxml")

    candidates: list[str] = []
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        candidates.append(og["content"])

    for img in soup.select("article img, .article-content img, .content img, main img"):
        src = img.get("src") or img.get("data-src") or ""
        if not src:
            continue
        low = src.lower()
        if any(x in low for x in SKIP_IMG):
            continue
        w = img.get("width")
        if w and str(w).isdigit() and int(w) < 200:
            continue
        candidates.append(src)

    for src in candidates:
        full = urljoin(page_url, src)
        ext = _ext_from_url(full)
        rel = f"assets/{news_id}{ext}"
        dest = assets_dir / f"{news_id}{ext}"
        if await _download_file(full, dest, page_url):
            return rel
    return ""


def _ext_from_url(url: str) -> str:
    path = urlparse(url).path.lower()
    for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        if ext in path:
            return ext
    return ".jpg"


async def _download_file(url: str, dest: Path, referer: str) -> bool:
    try:
        headers = {"User-Agent": "Mozilla/5.0", "Referer": referer}
        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            r = await client.get(url, headers=headers)
            if r.status_code == 200 and len(r.content) > 1000:
                dest.write_bytes(r.content)
                return True
    except Exception:
        pass
    return False


async def screenshot_article(url: str, news_id: str, screenshots_dir: Path, source_id: str) -> str:
    """Screenshot article page with logged-in profile. Returns relative path."""
    _require_playwright()
    from playwright.async_api import async_playwright

    from app.auth import ensure_logged_in
    from app.fetchers import _profile_path, load_sources_config

    screenshots_dir.mkdir(parents=True, exist_ok=True)
    rel = f"screenshots/{news_id}.png"
    dest = screenshots_dir / f"{news_id}.png"

    cfg = load_sources_config()["sources"].get(source_id, {})
    needs_login = cfg.get("requires_login", True)

    async with async_playwright() as pw:
        browser = None
        if needs_login:
            context = await pw.chromium.launch_persistent_context(
                user_data_dir=str(_profile_path(source_id)),
                headless=True,
                viewport={"width": 1200, "height": 900},
            )
        else:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(viewport={"width": 1200, "height": 900})

        if needs_login:
            await ensure_logged_in(context, source_id, cfg)

        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=35000)
            await page.wait_for_timeout(1000)
            selectors = ["article", ".article-content", ".content", "main", "body"]
            shot = False
            for sel in selectors:
                loc = page.locator(sel).first
                try:
                    if await loc.count() > 0:
                        await loc.screenshot(path=str(dest))
                        shot = True
                        break
                except Exception:
                    continue
            if not shot:
                await page.screenshot(path=str(dest), full_page=True)
        finally:
            await page.close()
            await context.close()
            if browser:
                await browser.close()

    return rel if dest.exists() else ""


async def capture_media_for_article(
    url: str,
    news_id: str,
    source_id: str,
    out_dir: Path,
) -> tuple[str, str]:
    """Return (image_asset rel path, screenshot_path rel path)."""
    _require_playwright()
    from playwright.async_api import async_playwright
    from app.auth import ensure_logged_in
    from app.fetchers import _profile_path, load_sources_config

    assets_dir = out_dir / "assets"
    screenshots_dir = out_dir / "screenshots"
    image_asset = ""
    html = ""

    cfg = load_sources_config()["sources"].get(source_id, {})
    needs_login = cfg.get("requires_login", True)

    async with async_playwright() as pw:
        browser = None
        if needs_login:
            context = await pw.chromium.launch_persistent_context(
                user_data_dir=str(_profile_path(source_id)),
                headless=True,
                viewport={"width": 1200, "height": 900},
            )
        else:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(viewport={"width": 1200, "height": 900})

        if needs_login:
            await ensure_logged_in(context, source_id, cfg)

        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=35000)
            await page.wait_for_timeout(1000)
            html = await page.content()
            image_asset = await download_article_image(html, url, news_id, assets_dir)

            screenshots_dir.mkdir(parents=True, exist_ok=True)
            dest = screenshots_dir / f"{news_id}.png"
            selectors = ["article", ".article-content", ".content", "main"]
            shot = False
            for sel in selectors:
                loc = page.locator(sel).first
                try:
                    if await loc.count() > 0:
                        await loc.screenshot(path=str(dest))
                        shot = True
                        break
                except Exception:
                    continue
            if not shot:
                await page.screenshot(path=str(dest), full_page=True)
        finally:
            await page.close()
            await context.close()
            if browser:
                await browser.close()

    screenshot_path = f"screenshots/{news_id}.png" if (screenshots_dir / f"{news_id}.png").exists() else ""
    return image_asset, screenshot_path
