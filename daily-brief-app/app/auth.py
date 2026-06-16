"""Optional auto-login from .env credentials (never commit .env)."""

from __future__ import annotations

import os
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext, Page


def _cred(source_id: str) -> tuple[str, str]:
    """Return (username/email, password) for a source from environment."""
    mapping = {
        "hket": ("HKET_USERNAME", "HKET_PASSWORD"),
        "hkej": ("HKEJ_EMAIL", "HKEJ_PASSWORD"),
        "mingpao": ("MINGPAO_USERNAME", "MINGPAO_PASSWORD"),
        "wenweipo": ("WENWEIPO_USERNAME", "WENWEIPO_PASSWORD"),
    }
    keys = mapping.get(source_id)
    if not keys:
        return "", ""
    user = os.getenv(keys[0], "").strip()
    pwd = os.getenv(keys[1], "").strip()
    return user, pwd


def credentials_configured(source_id: str) -> bool:
    user, pwd = _cred(source_id)
    return bool(user and pwd)


async def _fill_first_visible(page: Page, selectors: list[str], value: str) -> bool:
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0 and await loc.is_visible():
                await loc.fill(value)
                return True
        except Exception:
            continue
    return False


async def _click_first(page: Page, selectors: list[str]) -> bool:
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0 and await loc.is_visible():
                await loc.click()
                return True
        except Exception:
            continue
    return False


async def page_needs_login(page: Page, source_id: str) -> bool:
    """Heuristic: True if the current page looks like a login wall."""
    url = page.url.lower()
    if source_id == "hkej":
        if "subscribe.hkej.com" in url and "login" in url:
            return True
        if "subscribe.hkej.com/member/login" in url:
            return True
    if source_id == "mingpao":
        if "login1.php" in url or "/php/login" in url:
            return True
    if source_id == "hket":
        if "login" in url and "hket.com" in url:
            return True

    try:
        pwd = page.locator('input[type="password"]').first
        if await pwd.count() > 0 and await pwd.is_visible():
            login_btn = page.locator(
                'button:has-text("登入"), input[type="submit"], button:has-text("登录")'
            ).first
            if await login_btn.count() > 0 and await login_btn.is_visible():
                return True
    except Exception:
        pass
    return False


async def try_auto_login(source_id: str, page: Page) -> bool:
    """Fill .env credentials and submit. Returns True if form was filled and submitted."""
    user, pwd = _cred(source_id)
    if not user or not pwd:
        return False

    await page.wait_for_timeout(1500)

    if source_id == "hkej":
        filled_user = await _fill_first_visible(
            page,
            [
                'input[name="email"]',
                'input[type="email"]',
                "#email",
                'input[id*="email" i]',
                'input[placeholder*="電郵"]',
                'input[placeholder*="电邮"]',
                'input[name="username"]',
            ],
            user,
        )
        filled_pwd = await _fill_first_visible(
            page,
            ['input[name="password"]', 'input[type="password"]', "#password"],
            pwd,
        )
        clicked = await _click_first(
            page,
            [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("登入")',
                'button:has-text("登 入")',
                'a:has-text("登入")',
                ".btn-login",
                "#loginBtn",
            ],
        )
        if clicked:
            await page.wait_for_timeout(4000)
        return filled_user and filled_pwd and clicked

    if source_id == "mingpao":
        # news.mingpao.com/php/login1.php subscriber form
        filled_user = await _fill_first_visible(
            page,
            [
                'input[name="username"]',
                'input[name="login"]',
                'input[name="member"]',
                'input[name="email"]',
                'input[name="userid"]',
                'input[name="account"]',
                "#username",
                "#login",
                'form input[type="text"]',
            ],
            user,
        )
        filled_pwd = await _fill_first_visible(
            page,
            [
                'input[name="password"]',
                'input[name="pwd"]',
                'input[type="password"]',
                "#password",
            ],
            pwd,
        )
        clicked = await _click_first(
            page,
            [
                'input[type="submit"]',
                'button[type="submit"]',
                'button:has-text("登入")',
                'button:has-text("登录")',
                'input[value*="登入"]',
                'input[value*="登录"]',
            ],
        )
        if clicked:
            await page.wait_for_timeout(4000)
        return filled_user and filled_pwd and clicked

    if source_id == "hket":
        filled_user = await _fill_first_visible(
            page,
            ['input[name="username"]', 'input[type="email"]', 'input[type="text"]'],
            user,
        )
        filled_pwd = await _fill_first_visible(
            page, ['input[name="password"]', 'input[type="password"]'], pwd
        )
        clicked = await _click_first(
            page,
            ['button[type="submit"]', 'button:has-text("登入")', 'input[type="submit"]'],
        )
        if clicked:
            await page.wait_for_timeout(3000)
        return filled_user and filled_pwd and clicked

    return False


def _session_check_url(cfg: dict, report_date: date | None = None) -> str:
    """Resolve session check URL; substitute {date} / {date_compact} when present."""
    report_date = report_date or date.today()
    if cfg.get("session_check_url"):
        url = cfg["session_check_url"]
    else:
        sections = cfg.get("sections") or []
        if sections and sections[0].get("listing_url"):
            url = sections[0]["listing_url"]
        else:
            url = cfg.get("login_url", "")
    return (
        url.replace("{date}", report_date.isoformat()).replace(
            "{date_compact}", report_date.strftime("%Y%m%d")
        )
    )


async def ensure_logged_in(context: BrowserContext, source_id: str, cfg: dict) -> bool:
    """
    Verify subscriber session; if expired and .env has credentials, auto-login once.
    Returns True when session appears valid (or source does not require login).
    """
    if not cfg.get("requires_login", True):
        return True

    check_url = _session_check_url(cfg)
    if not check_url:
        return True

    page = await context.new_page()
    try:
        await page.goto(check_url, wait_until="domcontentloaded", timeout=35000)
        await page.wait_for_timeout(2000)
        if not await page_needs_login(page, source_id):
            print(f"[auth] {source_id}: session OK")
            return True

        if not credentials_configured(source_id):
            print(f"[auth] {source_id}: session expired, no .env credentials")
            return False

        print(f"[auth] {source_id}: session expired, trying .env auto-login…")
        login_urls = [u for u in (cfg.get("login_url"), cfg.get("login_url_alt")) if u]

        for login_url in login_urls:
            await page.goto(login_url, wait_until="domcontentloaded", timeout=35000)
            await page.wait_for_timeout(1500)
            submitted = await try_auto_login(source_id, page)
            if not submitted:
                continue
            await page.goto(check_url, wait_until="domcontentloaded", timeout=35000)
            await page.wait_for_timeout(2000)
            if not await page_needs_login(page, source_id):
                print(f"[auth] {source_id}: auto-login succeeded")
                return True

        print(f"[auth] {source_id}: auto-login failed — use dashboard「登入」button")
        return False
    except Exception as exc:
        print(f"[auth] {source_id}: session check error: {exc}")
        return False
    finally:
        await page.close()


async def open_login_flow(page: Page, source_id: str, cfg: dict) -> tuple[bool, str]:
    """
    Navigate login URL(s) and attempt .env auto-login.
    Returns (auto_submitted, message_hint).
    """
    await page.goto(cfg["login_url"], wait_until="domcontentloaded", timeout=35000)
    auto = await try_auto_login(source_id, page)
    if not auto and cfg.get("login_url_alt"):
        await page.goto(cfg["login_url_alt"], wait_until="domcontentloaded", timeout=35000)
        auto = await try_auto_login(source_id, page)

    if auto and credentials_configured(source_id):
        check_url = _session_check_url(cfg)
        if check_url:
            await page.goto(check_url, wait_until="domcontentloaded", timeout=35000)
            await page.wait_for_timeout(2000)
            if not await page_needs_login(page, source_id):
                return True, "已用 .env 登入成功。可關閉窗口。"
            return True, "已提交 .env 帳密；若仍有驗證碼請手動完成後關閉窗口。"
        return True, "已用 .env 帳號嘗試登入。確認已登入後關閉窗口。"

    if cfg.get("requires_login") is False:
        return False, "已打開（免登入）。確認後關閉窗口。"
    if credentials_configured(source_id):
        return False, "已打開登入頁；自動填表未成功，請手動登入或檢查 .env 帳密。"
    return False, "已打開登入頁。請手動登入，或在 .env 填帳密後重試。"
