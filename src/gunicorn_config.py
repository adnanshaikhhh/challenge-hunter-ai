"""Gunicorn config for Challenge Hunter AI v2.0.

Starts the APScheduler in each worker so the scanner runs even under
multiple Gunicorn workers.
"""
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger('gunicorn')

bind = "0.0.0.0:" + os.environ.get('PORT', '5000')
workers = int(os.environ.get('GUNICORN_WORKERS', '2'))
worker_class = 'sync'
timeout = 120
keepalive = 5
accesslog = '-'
errorlog = '-'
loglevel = 'info'


def on_starting(server):
    log.info("Gunicorn master starting")


def post_fork(server, worker):
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        # Ensure DB is initialised BEFORE the scheduler can fire any jobs.
        # Workers don't import app.py until first request, so we trigger
        # the DB init explicitly here.
        try:
            from app import _ensure_db
            _ensure_db()
        except Exception as e:
            log.exception(f"DB init failed in post_fork: {e}")
        from scheduler import SchedulerManager
        SchedulerManager.start()
        log.info(f"Scheduler started in worker {worker.pid}")
    except Exception as e:
        log.exception(f"Scheduler start failed in worker {worker.pid}: {e}")

def worker_abort(worker):
    log.warning(f"Worker {worker.pid} aborted (timeout)")
