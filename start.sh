#!/bin/bash
set -e

# Fix Python module resolution — app.py uses `from scanner import`
# but modules live in src/. Add src/ to PYTHONPATH so relative imports work.
export PYTHONPATH=/app/src:$PYTHONPATH

echo "✅ PYTHONPATH set to: $PYTHONPATH"
echo "🚀 Starting gunicorn..."
exec gunicorn app:app --bind 0.0.0.0:$PORT --workers 2