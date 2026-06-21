from __future__ import annotations

from typing import Any

from .errors import PredictValidationError
from .workflow import run_workflow


def create_blocking_scheduler(timezone: str):
    from apscheduler.schedulers.blocking import BlockingScheduler

    return BlockingScheduler(timezone=timezone)


def configure_daily_job(
    *,
    config_path: str,
    run_time: str,
    timezone: str,
    scheduler: Any | None = None,
):
    hour, minute = _parse_run_time(run_time)
    scheduler = scheduler or create_blocking_scheduler(timezone)
    scheduler.add_job(
        lambda: run_workflow(config_path),
        "cron",
        hour=hour,
        minute=minute,
        timezone=timezone,
    )
    return scheduler


def _parse_run_time(value: str) -> tuple[int, int]:
    parts = value.split(":")
    if len(parts) != 2:
        raise PredictValidationError("run time must use HH:MM format.")
    hour = int(parts[0])
    minute = int(parts[1])
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise PredictValidationError("run time must use HH:MM format.")
    return hour, minute
