# Gunicorn configuration for Challenge Hunter AI
# This file is loaded by gunicorn via: gunicorn -c gunicorn_config.py app:app

import os
import logging

# Server socket
bind = "0.0.0.0:" + os.environ.get('PORT', '5000')
workers = int(os.environ.get('GUNICORN_WORKERS', '2'))
worker_class = 'sync'
timeout = 120
keepalive = 5

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Gunicorn hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    print("🎯 Gunicorn starting...")

def post_fork(server, worker):
    """Called after a worker has been forked."""
    # Start the scanner scheduler in each worker process
    # Import here to ensure app module is fully loaded
    try:
        from app import DB_PATH
        from scanner import ScannerEngine
        
        scanner = ScannerEngine(DB_PATH)
        scanner.start_scheduler()
        print(f"📅 Scanner scheduler started in worker {worker.pid}")
    except Exception as e:
        print(f"⚠️  Scanner scheduler failed to start in worker {worker.pid}: {e}")

def worker_abort(worker):
    """Called when a worker times out."""
    print(f"⚠️  Worker {worker.pid} was aborted (timeout)")