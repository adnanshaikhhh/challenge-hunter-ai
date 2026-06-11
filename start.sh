#!/bin/bash
set -e

# Fix Python module resolution — app.py does `from scanner import ...`
# but modules live in src/. PYTHONPATH=/app/src allows Python to find them
# regardless of the current working directory.
export PYTHONPATH=/app/src:$PYTHONPATH

# Initialize SQLite database schema on first run
# Railway ephemeral — DB recreated on each redeploy (acceptable for hobby)
DB_PATH="${DB_PATH:-/app/opportunities.db}"
mkdir -p "$(dirname "$DB_PATH")"

if [ ! -f "$DB_PATH" ]; then
    echo "📦 First run — initializing database..."
    sqlite3 "$DB_PATH" < /app/src/schema.sql
    echo "✅ Database schema created at $DB_PATH"
else
    echo "✅ Database exists at $DB_PATH"
fi

echo "🚀 Starting gunicorn from $(pwd)..."
echo "✅ PYTHONPATH=$PYTHONPATH"
exec gunicorn app:app --bind 0.0.0.0:$PORT --workers 2