"""Shared Playwright persistent contexts for headed sources (HKET / 明報)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

_PROFILE_LOCK_MARKERS = (
    "being used by another process",
    "正由另一個程序",
    "另一个程序",
    "單一實例",
    "profile appears to be in use",
    "lock",
    "無法存取",
    "cannot access",
)


class ProfileLockedError(Exception):
    """Browser profile directory is locked by another Chrome/Playwright process."""

    def __init__(self, source_id: str, source_name: str, detail: str = "") -> None:
        self.source_id = source_id
        self.source_name = source_name
        msg = (
            f"【{source_name}】瀏覽器 profile 被占用（{source_id}）。"
            "請關閉該報社的登入/抓取 Chrome 窗口，或在儀表板點「完成登入」釋放 profile 後重試。"
        )
        if detail:
            msg += f" ({detail[:120]})"
        super().__init__(msg)


class BrowserClosedError(Exception):
    """Headed browser window was closed while fetch was in progress."""

    def __init__(self, source_id: str, source_name: str) -> None:
        self.source_id = source_id
        self.source_name = source_name
        super().__init__(
            f"【{source_name}】抓取瀏覽器已關閉。請勿關閉彈出的 Chrome 窗口；若已關閉請重新抓取。"
        )


_sessions: dict[str, dict[str, Any]] = {}


def _is_profile_lock_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return any(m.lower() in text for m in _PROFILE_LOCK_MARKERS)


async def _context_alive(context) -> bool:
    try:
        if context is None:
            return False
        browser = context.browser
        if browser is None:
            return True
        return browser.is_connected()
    except Exception:
        return False


async def release_context(source_id: str, *, stop_pw: bool = False) -> None:
    """Close persistent context and free profile lock."""
    entry = _sessions.pop(source_id, None)
    if not entry:
        return
    ctx = entry.get("context")
    if ctx:
        try:
            await ctx.close()
        except Exception:
            pass
    pw = entry.get("pw")
    if stop_pw and pw and entry.get("own_pw"):
        try:
            await pw.stop()
        except Exception:
            pass


def has_open_session(source_id: str) -> bool:
    return source_id in _sessions


async def register_login_session(
    source_id: str, pw, context, *, own_pw: bool = True
) -> None:
    await release_context(source_id, stop_pw=True)
    _sessions[source_id] = {
        "pw": pw,
        "context": context,
        "own_pw": own_pw,
        "mode": "login",
    }


async def acquire_persistent_context(
    pw,
    source_id: str,
    profile: Path,
    *,
    headless: bool,
    source_name: str = "",
) -> tuple[Any, bool]:
    """
    Return (context, reused_login_session).
    Reuses an open login browser when still alive to avoid profile lock.
    """
    entry = _sessions.get(source_id)
    if entry and await _context_alive(entry.get("context")):
        entry["mode"] = "fetch"
        return entry["context"], True

    if entry:
        await release_context(source_id, stop_pw=True)

    viewport = {"width": 1400, "height": 900}
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            context = await pw.chromium.launch_persistent_context(
                user_data_dir=str(profile),
                headless=headless,
                viewport=viewport,
            )
            _sessions[source_id] = {
                "pw": pw,
                "context": context,
                "own_pw": False,
                "mode": "fetch",
            }
            return context, False
        except Exception as exc:
            last_exc = exc
            if _is_profile_lock_error(exc):
                if attempt >= 2:
                    raise ProfileLockedError(
                        source_id, source_name or source_id, str(exc)
                    ) from exc
                await asyncio.sleep(2)
                continue
            raise
    if last_exc:
        if _is_profile_lock_error(last_exc):
            raise ProfileLockedError(
                source_id, source_name or source_id, str(last_exc)
            ) from last_exc
        raise last_exc
    raise RuntimeError(f"failed to launch browser for {source_id}")


async def ensure_context_ready(
    pw,
    source_id: str,
    profile: Path,
    *,
    headless: bool,
    source_name: str = "",
) -> Any:
    """Relaunch persistent context if the user closed the headed window."""
    entry = _sessions.get(source_id)
    ctx = entry.get("context") if entry else None
    if ctx and await _context_alive(ctx):
        return ctx
    if entry:
        await release_context(source_id, stop_pw=False)
    ctx, _ = await acquire_persistent_context(
        pw, source_id, profile, headless=headless, source_name=source_name
    )
    return ctx


async def finish_login_and_release(source_id: str) -> str:
    """Called when user confirms login is done — closes browser, keeps cookies on disk."""
    had = source_id in _sessions
    await release_context(source_id, stop_pw=True)
    if had:
        return "已關閉登入瀏覽器並釋放 profile。Cookie 已保存，可開始抓取。"
    return "沒有進行中的登入瀏覽器（profile 已釋放）。"
