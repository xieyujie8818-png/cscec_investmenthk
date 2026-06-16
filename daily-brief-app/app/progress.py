"""Shared fetch job progress for UI polling (overall + per-source + pause/resume)."""

from __future__ import annotations

import asyncio

_progress: dict = {
    "progress": 0,
    "stage": "",
    "detail": "",
    "current_source": "",
    "sources": {},
}

_pause_event: asyncio.Event | None = None
_paused: bool = False
_pause_reason: str = ""


def _event() -> asyncio.Event:
    global _pause_event
    if _pause_event is None:
        _pause_event = asyncio.Event()
        _pause_event.set()
    return _pause_event


def reset() -> None:
    _progress["progress"] = 0
    _progress["stage"] = ""
    _progress["detail"] = ""
    _progress["current_source"] = ""
    _progress["sources"] = {}
    resume()


def init_sources(source_ids: list[str], names: dict[str, str] | None = None) -> None:
    names = names or {}
    _progress["sources"] = {
        sid: {
            "id": sid,
            "name": names.get(sid, sid),
            "status": "pending",
            "detail": "",
            "articles": 0,
        }
        for sid in source_ids
    }


def update(progress: int, stage: str = "", detail: str = "") -> None:
    _progress["progress"] = max(0, min(100, progress))
    if stage:
        _progress["stage"] = stage
    if detail:
        _progress["detail"] = detail


def source_start(source_id: str, detail: str = "") -> None:
    _progress["current_source"] = source_id
    src = _progress["sources"].get(source_id)
    if src:
        src["status"] = "running"
        src["detail"] = detail


def source_update(source_id: str, detail: str) -> None:
    src = _progress["sources"].get(source_id)
    if src:
        src["detail"] = detail


def source_done(source_id: str, articles: int, detail: str = "") -> None:
    src = _progress["sources"].get(source_id)
    if src:
        src["status"] = "done"
        src["articles"] = articles
        if detail:
            src["detail"] = detail
        elif articles:
            src["detail"] = f"{articles} 篇"
        else:
            src["detail"] = "0 篇"


def source_error(source_id: str, detail: str) -> None:
    src = _progress["sources"].get(source_id)
    if src:
        src["status"] = "error"
        src["detail"] = detail[:150] if detail else "失敗"


def source_login_required(source_id: str, detail: str) -> None:
    src = _progress["sources"].get(source_id)
    if src:
        src["status"] = "login_required"
        src["detail"] = detail[:150] if detail else "需要登入"


def source_skipped(source_id: str, detail: str) -> None:
    src = _progress["sources"].get(source_id)
    if src:
        src["status"] = "skipped"
        src["detail"] = detail[:150] if detail else "已跳過"


def request_pause(reason: str = "") -> None:
    global _paused, _pause_reason
    _paused = True
    _pause_reason = reason
    _event().clear()
    if reason:
        _progress["stage"] = "已暫停"
        _progress["detail"] = reason


def resume() -> None:
    global _paused, _pause_reason
    _paused = False
    _pause_reason = ""
    _event().set()


def is_paused() -> bool:
    return _paused


async def wait_if_paused() -> None:
    """Block until resume() is called (manual pause or post-login wait)."""
    ev = _event()
    while not ev.is_set():
        await asyncio.sleep(0.3)


def snapshot() -> dict:
    return {
        "progress": _progress["progress"],
        "stage": _progress["stage"],
        "detail": _progress["detail"],
        "current_source": _progress["current_source"],
        "sources": {k: dict(v) for k, v in _progress["sources"].items()},
        "paused": _paused,
        "pause_reason": _pause_reason,
    }
