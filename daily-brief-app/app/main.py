"""FastAPI web UI — v2 candidate pool + brief generation."""

from __future__ import annotations

import json
import logging
import os
from datetime import date
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel

from app.brief_generator import generate_brief_from_report_key, generate_brief_from_selection
from app.candidates import (
    OUTPUT_DIR,
    fetch_and_score_candidates,
    load_candidates,
    load_selection,
    parse_report_key,
    report_key,
    save_selection,
)
from app.fetchers import (
    close_login_browser,
    load_sources_config,
    open_login_browser,
    playwright_available,
)
from app.browser_sessions import ProfileLockedError
from app import progress as job_progress
from app.scheduler import get_last_run, run_scheduled_job, start_scheduler, stop_scheduler

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="香港簡訊 · 日報系統 v2", version="0.2.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

_jinja = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)

_jinja.filters["tojson"] = lambda v: json.dumps(v, ensure_ascii=False)

_job_status: dict = {
    "running": False,
    "message": "",
    "action": "",
    "progress": 0,
    "stage": "",
    "detail": "",
}


def _merge_job_status() -> dict:
    p = job_progress.snapshot()
    return {**_job_status, **p}


class SelectionBody(BaseModel):
    sections: dict[str, list[dict[str, Any]]]


def _list_dates() -> list[str]:
    if not OUTPUT_DIR.exists():
        return []
    return sorted([p.name for p in OUTPUT_DIR.iterdir() if p.is_dir()], reverse=True)


def _dashboard_html() -> str:
    cfg = load_sources_config()
    pw_ok, pw_err = playwright_available()
    tpl = _jinja.get_template("dashboard.html")
    return tpl.render(
        sources=cfg.get("sources", {}),
        dates=_list_dates(),
        job_status=_job_status,
        quotas=cfg.get("quotas", {}),
        selection_rules=cfg.get("selection", {}),
        playwright_ok=pw_ok,
        playwright_error=pw_err,
    )


def _candidates_html(report_key_str: str) -> str:
    cfg = load_sources_config()
    date_start, date_end = parse_report_key(report_key_str)
    data = load_candidates(date_start, date_end)
    sel = load_selection(date_start, date_end)
    selection_cfg = cfg.get("selection", {})
    tpl = _jinja.get_template("candidates.html")
    return tpl.render(
        date=report_key_str,
        date_label=data.get("date_start", report_key_str) if data else report_key_str,
        candidates=data,
        selection=sel,
        quotas=cfg.get("quotas", {}),
        selection_rules=selection_cfg,
        sources=cfg.get("sources", {}),
        job_status=_job_status,
    )


async def _run_fetch(date_start: date, date_end: date) -> None:
    global _job_status
    job_progress.reset()
    range_label = (
        date_end.isoformat()
        if date_start == date_end
        else f"{date_start.isoformat()}–{date_end.isoformat()}"
    )
    _job_status = {
        "running": True,
        "action": "fetch",
        "message": f"抓取候選 {range_label}…",
        "progress": 0,
        "stage": "啟動",
        "detail": "",
    }
    try:
        result = await fetch_and_score_candidates(date_start, date_end)
        counts = {k: len(v) for k, v in result.get("sections", {}).items()}
        rk = result.get("report_key", report_key(date_start, date_end))
        _job_status = {
            "running": False,
            "action": "fetch",
            "message": f"完成：{counts}（共 {result.get('raw_count', 0)} 篇真新聞）",
            "date": date_end.isoformat(),
            "date_start": date_start.isoformat(),
            "date_end": date_end.isoformat(),
            "report_key": rk,
            "progress": 100,
            "stage": "完成",
            "detail": str(counts),
            "success": True,
        }
    except Exception as exc:
        logger.exception("fetch-candidates failed")
        _job_status = {
            "running": False,
            "action": "fetch",
            "message": f"失敗：{exc}",
            "progress": 0,
            "stage": "失敗",
            "detail": str(exc),
            "success": False,
        }


async def _run_generate(report_key_str: str) -> None:
    global _job_status
    _job_status = {"running": True, "action": "generate", "message": f"生成定稿 {report_key_str}…"}
    try:
        out = await generate_brief_from_report_key(report_key_str)
        _job_status = {
            "running": False,
            "action": "generate",
            "message": f"完成：{out / 'daily-brief.md'}、daily-brief.html、daily-brief.docx",
            "report_key": report_key_str,
        }
    except Exception as exc:
        logger.exception("generate-brief failed")
        _job_status = {"running": False, "action": "generate", "message": f"失敗：{exc}"}


@app.on_event("startup")
async def startup() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    start_scheduler()


@app.on_event("shutdown")
async def shutdown() -> None:
    stop_scheduler()


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    return HTMLResponse(_dashboard_html())


@app.get("/candidates/{report_key_str:path}", response_class=HTMLResponse)
async def candidates_page(report_key_str: str) -> HTMLResponse:
    return HTMLResponse(_candidates_html(report_key_str))


@app.get("/api/status")
async def api_status() -> dict:
    return {"job": _merge_job_status(), "last_scheduled": get_last_run(), "dates": _list_dates()}


@app.post("/api/fetch-pause")
async def api_fetch_pause() -> dict:
    if not _job_status.get("running"):
        raise HTTPException(400, "沒有進行中的抓取任務")
    job_progress.request_pause("使用者暫停 — 按「繼續」恢復抓取")
    return {"ok": True, "message": "已暫停抓取"}


@app.post("/api/fetch-resume")
async def api_fetch_resume() -> dict:
    if not _job_status.get("running"):
        raise HTTPException(400, "沒有進行中的抓取任務")
    job_progress.resume()
    return {"ok": True, "message": "已繼續抓取"}


@app.post("/api/fetch-candidates")
async def api_fetch_candidates(
    background_tasks: BackgroundTasks,
    report_date: str | None = None,
    date_start: str | None = None,
    date_end: str | None = None,
) -> dict:
    if _job_status.get("running"):
        raise HTTPException(409, "已有任務在執行")
    if date_start or date_end:
        ds = date.fromisoformat(date_start) if date_start else date.today()
        de = date.fromisoformat(date_end) if date_end else ds
    elif report_date:
        ds = de = date.fromisoformat(report_date)
    else:
        ds = de = date.today()
    if ds > de:
        ds, de = de, ds
    background_tasks.add_task(_run_fetch, ds, de)
    rk = report_key(ds, de)
    return {
        "ok": True,
        "date_start": ds.isoformat(),
        "date_end": de.isoformat(),
        "report_key": rk,
        "message": "已開始抓取候選",
    }


@app.get("/api/candidates/{report_key_str:path}")
async def api_get_candidates(report_key_str: str) -> dict:
    date_start, date_end = parse_report_key(report_key_str)
    data = load_candidates(date_start, date_end)
    if not data:
        raise HTTPException(404, "尚無候選池，請先抓取")
    return data


@app.put("/api/candidates/{report_key_str:path}/selection")
async def api_save_selection(report_key_str: str, body: SelectionBody) -> dict:
    date_start, date_end = parse_report_key(report_key_str)
    path = save_selection(date_start, date_end, body.model_dump())
    return {"ok": True, "path": str(path)}


@app.post("/api/generate-brief")
async def api_generate_brief(
    background_tasks: BackgroundTasks,
    report_date: str | None = None,
    report_key_str: str | None = None,
    date_start: str | None = None,
    date_end: str | None = None,
) -> dict:
    if _job_status.get("running"):
        raise HTTPException(409, "已有任務在執行")
    if report_key_str:
        rk = report_key_str
    elif date_start or date_end:
        ds = date.fromisoformat(date_start) if date_start else date.today()
        de = date.fromisoformat(date_end) if date_end else ds
        if ds > de:
            ds, de = de, ds
        rk = report_key(ds, de)
    elif report_date:
        rk = report_date
    else:
        rk = date.today().isoformat()
    ds, de = parse_report_key(rk)
    if not load_selection(ds, de):
        raise HTTPException(400, "請先在候選池保存選擇")
    background_tasks.add_task(_run_generate, rk)
    return {"ok": True, "report_key": rk, "message": "已開始生成定稿"}


@app.post("/api/login/{source_id}")
async def api_login(source_id: str, background_tasks: BackgroundTasks) -> dict:
    cfg = load_sources_config()
    if source_id not in cfg.get("sources", {}):
        raise HTTPException(404, f"未知來源: {source_id}")

    async def _login() -> None:
        try:
            msg = await open_login_browser(source_id)
            logger.info(msg)
        except ProfileLockedError as exc:
            logger.warning(str(exc))

    background_tasks.add_task(_login)
    name = cfg["sources"][source_id]["name"]
    return {"ok": True, "message": f"正在打開 {name} 登入瀏覽器"}


@app.post("/api/login/{source_id}/done")
async def api_login_done(source_id: str) -> dict:
    cfg = load_sources_config()
    if source_id not in cfg.get("sources", {}):
        raise HTTPException(404, f"未知來源: {source_id}")
    msg = await close_login_browser(source_id)
    return {"ok": True, "message": msg}


@app.get("/report/{report_key_str:path}/brief", response_class=PlainTextResponse)
async def view_brief_md(report_key_str: str) -> PlainTextResponse:
    path = OUTPUT_DIR / report_key_str / "daily-brief.md"
    if not path.exists():
        raise HTTPException(404, "尚無定稿，請先生成")
    return PlainTextResponse(path.read_text(encoding="utf-8"), media_type="text/markdown; charset=utf-8")


@app.get("/report/{report_key_str:path}/brief.html", response_class=HTMLResponse)
async def view_brief_html(report_key_str: str) -> HTMLResponse:
    path = OUTPUT_DIR / report_key_str / "daily-brief.html"
    if not path.exists():
        raise HTTPException(404, "尚無 HTML 定稿，請先生成")
    return HTMLResponse(path.read_text(encoding="utf-8"))


@app.get("/report/{report_key_str:path}/brief.docx")
async def download_brief_docx(report_key_str: str) -> FileResponse:
    path = OUTPUT_DIR / report_key_str / "daily-brief.docx"
    if not path.exists():
        raise HTTPException(404, "尚無 Word 定稿，請先生成")
    return FileResponse(
        path,
        filename=f"daily-brief-{report_key_str}.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@app.get("/report/{report_key_str:path}/feishu", response_class=PlainTextResponse)
async def view_feishu(report_key_str: str) -> PlainTextResponse:
    path = OUTPUT_DIR / report_key_str / "feishu.txt"
    if not path.exists():
        raise HTTPException(404, "尚無 feishu.txt")
    return PlainTextResponse(path.read_text(encoding="utf-8"))


@app.get("/report/{report_key_str:path}/monthly", response_class=PlainTextResponse)
async def view_monthly(report_key_str: str) -> PlainTextResponse:
    path = OUTPUT_DIR / report_key_str / "monthly.md"
    if not path.exists():
        raise HTTPException(404, "尚無 monthly.md")
    return PlainTextResponse(path.read_text(encoding="utf-8"))


@app.get("/report/{report_key_str:path}/assets/{filename}")
async def serve_asset(report_key_str: str, filename: str) -> FileResponse:
    path = OUTPUT_DIR / report_key_str / "assets" / filename
    if not path.exists():
        raise HTTPException(404)
    return FileResponse(path)


@app.get("/report/{report_key_str:path}/screenshots/{filename}")
async def serve_screenshot(report_key_str: str, filename: str) -> FileResponse:
    path = OUTPUT_DIR / report_key_str / "screenshots" / filename
    if not path.exists():
        raise HTTPException(404)
    return FileResponse(path)


@app.get("/report/{report_key_str:path}/download/{filename}")
async def download_file(report_key_str: str, filename: str) -> FileResponse:
    allowed = {
        "daily-brief.md",
        "daily-brief.html",
        "daily-brief.docx",
        "feishu.txt",
        "monthly.md",
        "report.json",
        "candidates.json",
        "selection.json",
    }
    if filename not in allowed:
        raise HTTPException(400, "不允許的文件")
    path = OUTPUT_DIR / report_key_str / filename
    if not path.exists():
        raise HTTPException(404)
    return FileResponse(path, filename=filename)


@app.post("/api/run-scheduler-now")
async def run_now(background_tasks: BackgroundTasks) -> dict:
    if _job_status.get("running"):
        raise HTTPException(409, "已有任務在執行")
    today = date.today()
    if today.weekday() >= 5:
        return {"ok": False, "message": "週末不執行定時抓取"}
    background_tasks.add_task(_run_fetch, today, today)
    return {"ok": True, "message": "已觸發定時抓取候選"}


def main() -> None:
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8765"))
    import uvicorn

    uvicorn.run("app.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
