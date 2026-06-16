import os
import pytz
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

IST = pytz.timezone("Asia/Kolkata")

SCHEDULE_STATE = os.getenv("SCHEDULE_STATE", "Tamil Nadu")
SCHEDULE_DATE = os.getenv("SCHEDULE_DATE", "2026-06-16")
SCHEDULE_INTERVAL_MINS = int(os.getenv("SCHEDULE_INTERVAL_MINS", "5"))
SCHEDULE_START_TIME = os.getenv("SCHEDULE_START_TIME", "12:15")
SCHEDULE_END_TIME = os.getenv("SCHEDULE_END_TIME", "12:45")


def _ist_dt(date_str: str, time_str: str) -> datetime:
    d = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    return IST.localize(d)


def build_scheduler(job_fn) -> BackgroundScheduler:
    start_dt = _ist_dt(SCHEDULE_DATE, SCHEDULE_START_TIME)
    end_dt = _ist_dt(SCHEDULE_DATE, SCHEDULE_END_TIME)

    sched = BackgroundScheduler(timezone=IST)
    sched.add_job(
        job_fn,
        trigger=IntervalTrigger(
            minutes=SCHEDULE_INTERVAL_MINS,
            start_date=start_dt,
            end_date=end_dt,
            timezone=IST,
        ),
        id="weather_scheduled",
        name=f"{SCHEDULE_STATE} weather — {SCHEDULE_DATE}",
    )
    return sched


def scheduler_info(sched: BackgroundScheduler) -> dict:
    job = sched.get_job("weather_scheduled")
    next_run = None
    if job and job.next_run_time:
        next_run = job.next_run_time.strftime("%I:%M %p IST")

    now = datetime.now(IST)
    start_dt = _ist_dt(SCHEDULE_DATE, SCHEDULE_START_TIME)
    end_dt = _ist_dt(SCHEDULE_DATE, SCHEDULE_END_TIME)
    window_passed = now > end_dt

    return {
        "state": SCHEDULE_STATE,
        "date": SCHEDULE_DATE,
        "window": f"{SCHEDULE_START_TIME} – {SCHEDULE_END_TIME} IST",
        "interval_mins": SCHEDULE_INTERVAL_MINS,
        "next_run": next_run,
        "active": job is not None and next_run is not None,
        "window_passed": window_passed,
    }
