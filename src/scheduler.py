#!/usr/bin/env python3
"""
Challenge Hunter AI v2.0 — Persistent Background Job System
Wraps APScheduler with safe lifecycle management.
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import threading
import time
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config import (
    DAILY_DIGEST_HOUR_UTC, DB_PATH, SCAN_INTERVAL_HOURS, WEEKLY_SUMMARY_DAY
)
from notifier import daily_digest, error as notif_error, info as notif_info
from scanner import ScannerEngine

logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    level=logging.INFO
)
log = logging.getLogger('scheduler')


# ----------------------------------------------------------------------------
# Job callbacks
# ----------------------------------------------------------------------------

def job_full_scan():
    log.info("Running scheduled full scan")
    try:
        engine = ScannerEngine(DB_PATH)
        result = engine.run_full_scan()
        log.info(f"Scan result: {result}")
        notif_info(
            f"🔍 Scheduled scan complete: {result['new_found']} new, "
            f"{result['high_value_found']} high-value"
        )
    except Exception as e:
        log.exception("Scheduled scan failed")
        notif_error(f"Scan failed: {e}")


def job_daily_digest():
    log.info("Running daily digest")
    try:
        daily_digest()
    except Exception as e:
        log.exception("Daily digest failed")


def job_weekly_summary():
    log.info("Running weekly summary")
    try:
        daily_digest()  # reuse digest format
        notif_info("📈 Weekly summary sent")
    except Exception as e:
        log.exception("Weekly summary failed")


def job_health_ping():
    log.info("Health ping (keeps Render free tier alive)")


# ----------------------------------------------------------------------------
# Scheduler manager
# ----------------------------------------------------------------------------

class SchedulerManager:
    _lock = threading.Lock()
    _instance: Optional[BackgroundScheduler] = None

    @classmethod
    def get(cls) -> Optional[BackgroundScheduler]:
        return cls._instance

    @classmethod
    def start(cls) -> BackgroundScheduler:
        with cls._lock:
            if cls._instance and cls._instance.running:
                return cls._instance
            scheduler = BackgroundScheduler(timezone='UTC')
            scheduler.add_job(
                job_full_scan,
                IntervalTrigger(hours=SCAN_INTERVAL_HOURS),
                id='full_scan',
                name='Full opportunity scan',
                replace_existing=True,
                next_run_time=datetime_now()  # run once on startup
            )
            scheduler.add_job(
                job_daily_digest,
                CronTrigger(hour=DAILY_DIGEST_HOUR_UTC, minute=0),
                id='daily_digest',
                name='Daily digest',
                replace_existing=True
            )
            scheduler.add_job(
                job_weekly_summary,
                CronTrigger(day_of_week=WEEKLY_SUMMARY_DAY, hour=DAILY_DIGEST_HOUR_UTC + 1, minute=0),
                id='weekly_summary',
                name='Weekly summary',
                replace_existing=True
            )
            scheduler.add_job(
                job_health_ping,
                IntervalTrigger(minutes=14),
                id='health_ping',
                name='Health ping',
                replace_existing=True
            )
            scheduler.start()
            cls._instance = scheduler
            log.info(f"Scheduler started (scan every {SCAN_INTERVAL_HOURS}h)")
            return scheduler

    @classmethod
    def shutdown(cls):
        with cls._lock:
            if cls._instance and cls._instance.running:
                cls._instance.shutdown(wait=False)
                log.info("Scheduler stopped")
            cls._instance = None


def datetime_now():
    from datetime import datetime
    return datetime.now()


# ----------------------------------------------------------------------------
# Signal handling
# ----------------------------------------------------------------------------

def _install_signal_handlers():
    def handler(signum, frame):
        log.info(f"Received signal {signum}, shutting down scheduler")
        SchedulerManager.shutdown()
        sys.exit(0)
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, handler)
        except (ValueError, OSError):
            pass  # not main thread


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

if __name__ == '__main__':
    _install_signal_handlers()
    scheduler = SchedulerManager.start()
    print(f"Scheduler started with {len(scheduler.get_jobs())} jobs")
    print("Jobs:")
    for job in scheduler.get_jobs():
        print(f"  - {job.id}: {job.name} (next: {job.next_run_time})")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        SchedulerManager.shutdown()
