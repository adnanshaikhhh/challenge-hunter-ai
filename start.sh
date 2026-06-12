#!/bin/bash
set -e

# Fix Python module resolution — app.py does `from scanner import ...`
# but modules live in src/. PYTHONPATH=/app/src allows Python to find them
# regardless of the current working directory.
export PYTHONPATH=/app/src:$PYTHONPATH

# Database path - must match what app.py uses (derived from __file__ at /app/src/app.py)
# Note: app.py auto-initializes DB at module load time if it doesn't exist
DB_PATH="${DB_PATH:-/app/opportunities.db}"

echo "🚀 Starting gunicorn from $(pwd)..."
echo "✅ PYTHONPATH=$PYTHONPATH"
echo "✅ DB_PATH=$DB_PATH"
exec gunicorn app:app --bind 0.0.0.0:$PORT --workers 2