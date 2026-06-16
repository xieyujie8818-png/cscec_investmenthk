"""APScheduler: weekday 10:00 HKT fetch candidates only."""

from __future__ import annotations

import logging
import os
from datetime import date

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from app.candidates import fetch_and_score_candidates

logger = logging.getLogger(__name__)
HKT = pytz.timezone("Asia/Hong_Kong")
_scheduler: AsyncIOScheduler | None = None
_last_run: dict | None = None


def get_last_run() -> dict | None:
    return _last_run


async def run_scheduled_job() -> None:
    global _last_run
    today = date.today()
    if today.weekday() >= 5:
        logger.info("Skip weekend: %s", today)
        return
    try:
        logger.info("Scheduled fetch-candidates for %s", today)
        result = await fetch_and_score_candidates(date_end=today)
        counts = {k: len(v) for k, v in result.get("sections", {}).items()}
        _last_run = {
            "date": today.isoformat(),
            "status": "ok",
            "action": "fetch-candidates",
            "sections": counts,
        }
        logger.info("Candidates saved: %s", counts)
    except Exception as exc:
        logger.exception("Scheduled job failed")
        _last_run = {"date": today.isoformat(), "status": "error", "error": str(exc)}


def start_scheduler() -> AsyncIOScheduler | None:
    global _scheduler
    if os.getenv("ENABLE_SCHEDULER", "true").lower() not in ("1", "true", "yes"):
        return None
    hour = int(os.getenv("SCHEDULE_HOUR", "10"))
    minute = int(os.getenv("SCHEDULE_MINUTE", "0"))

    _scheduler = AsyncIOScheduler(timezone=HKT)
    _scheduler.add_job(
        run_scheduled_job,
        CronTrigger(day_of_week="mon-fri", hour=hour, minute=minute, timezone=HKT),
        id="fetch_candidates",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scheduler: Mon-Fri %02d:%02d HKT fetch-candidates only", hour, minute)
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
