#!/usr/bin/env python3
"""
Challenge Hunter AI v2.0 — Flask Backend
All API endpoints, DB init at module load, Gunicorn-safe.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from flask import (
    Flask, jsonify, render_template, request, send_from_directory
)
from flask_cors import CORS

from auto_builder import run_build_async
from config import (
    APP_NAME, APP_TAGLINE, DEBUG, DB_PATH, HOST, PORT, SCHEMA_PATH, SECRET_KEY, VERSION
)
from generator import ProjectFileGenerator
from notifier import (
    build_complete as notif_build_complete, build_started as notif_build_started,
    daily_digest, high_value_alert, info as notif_info, submitted as notif_submitted
)
from scanner import ScannerEngine
from scorer import (
    calculate_expected_value, calculate_opportunity_score, calculate_win_probability
)


# =============================================================================
# Database bootstrap (runs on import — works under Gunicorn)
# =============================================================================

def _ensure_db() -> None:
    """Create schema and seed if missing. Idempotent. Migrates v2.1 tables."""
    new_db = not os.path.exists(DB_PATH)
    if new_db:
        os.makedirs(os.path.dirname(DB_PATH) or '.', exist_ok=True)
        print(f"📦 Creating new database at {DB_PATH}", flush=True)
    conn = sqlite3.connect(DB_PATH)
    if new_db:
        with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
            conn.executescript(f.read())
        print("   ✅ schema created", flush=True)
    else:
        # Run schema (uses CREATE IF NOT EXISTS — safe)
        if os.path.exists(SCHEMA_PATH):
            with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
                conn.executescript(f.read())
            print("   ✅ schema verified (migrated)", flush=True)

    # Verify core tables exist
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='opportunities'")
    if not cur.fetchone():
        print("   ⚠️  core tables missing, re-running schema", flush=True)
        with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
            conn.executescript(f.read())
    conn.close()

    if new_db:
        # auto-seed
        from seed import seed_database
        try:
            n = seed_database()
            print(f"   ✅ seeded {n} opportunities", flush=True)
        except Exception as e:
            print(f"   ⚠️  seed failed: {e}", flush=True)


_ensure_db()


# =============================================================================
# Flask app
# =============================================================================

app = Flask(
    __name__,
    template_folder='templates',
    static_folder='static'
)
app.config['SECRET_KEY'] = SECRET_KEY
CORS(app)


# =============================================================================
# Database helpers
# =============================================================================

def get_db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def row_to_dict(row) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    d = dict(row)
    for k, v in list(d.items()):
        if isinstance(v, str) and k.endswith('_json'):
            try:
                d[k] = json.loads(v)
            except Exception:
                pass
    return d


# =============================================================================
# Frontend routes
# =============================================================================

@app.route('/')
def index():
    return render_template('index.html',
                           app_name=APP_NAME, version=VERSION, tagline=APP_TAGLINE)


@app.route('/static/<path:path>')
def static_files(path):
    return send_from_directory(app.static_folder, path)


# =============================================================================
# Health & meta
# =============================================================================

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'service': APP_NAME,
        'version': VERSION,
        'time': datetime.now().isoformat()
    })


@app.route('/api/meta')
def meta():
    return jsonify({
        'name': APP_NAME,
        'version': VERSION,
        'tagline': APP_TAGLINE,
        'time': datetime.now().isoformat()
    })


# =============================================================================
# Opportunities
# =============================================================================

@app.route('/api/opportunities', methods=['GET'])
def list_opportunities():
    status = request.args.get('status')
    min_score = request.args.get('min_score', type=int)
    sort_by = request.args.get('sort_by', 'score')
    search = request.args.get('search')
    tag = request.args.get('tag')
    limit = request.args.get('limit', type=int)
    offset = request.args.get('offset', type=int, default=0)

    query = "SELECT * FROM opportunities WHERE 1=1"
    params: List[Any] = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if min_score:
        query += " AND opportunity_score >= ?"
        params.append(min_score)
    if search:
        query += " AND (name LIKE ? OR rules_summary LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s])
    if tag:
        query += " AND tags LIKE ?"
        params.append(f"%{tag}%")

    if sort_by == 'deadline':
        query += " ORDER BY days_remaining ASC"
    elif sort_by == 'prize':
        query += " ORDER BY prize_usd DESC"
    elif sort_by == 'win':
        query += " ORDER BY win_probability DESC"
    elif sort_by == 'ev':
        query += " ORDER BY expected_value DESC"
    else:
        query += " ORDER BY opportunity_score DESC"

    if limit:
        query += f" LIMIT {int(limit)} OFFSET {int(offset)}"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) AS c FROM opportunities WHERE 1=1" +
                   (" AND status=?" if status else ""), params[:1] if status else [])
    total = cursor.fetchone()['c']
    conn.close()
    return jsonify({
        'total': total,
        'count': len(rows),
        'items': [row_to_dict(r) for r in rows]
    })


@app.route('/api/opportunities/<int:opp_id>', methods=['GET'])
def get_opportunity(opp_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM opportunities WHERE id = ?", (opp_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'not found'}), 404
    return jsonify(row_to_dict(row))


def _set_status(opp_id: int, status: str, **extra) -> Dict[str, Any]:
    fields = {'status': status, 'updated_at': datetime.now().isoformat()}
    fields.update(extra)
    cols = ', '.join(f"{k} = ?" for k in fields.keys())
    vals = list(fields.values()) + [opp_id]
    conn = get_db()
    conn.execute(f"UPDATE opportunities SET {cols} WHERE id = ?", vals)
    conn.commit()
    conn.close()
    return fields


@app.route('/api/opportunities/<int:opp_id>/approve', methods=['POST'])
def approve_opportunity(opp_id):
    fields = _set_status(opp_id, 'approved', build_status='in_progress')
    # trigger auto build in background
    run_build_async(opp_id)
    return jsonify({'success': True, 'building': True, **fields})


@app.route('/api/opportunities/<int:opp_id>/build', methods=['POST'])
def build_opportunity(opp_id):
    """
    Trigger the actual AI code-generation step.
    Requires OPENROUTER_API_KEY to be set.
    Runs in a background thread so the API stays responsive.
    """
    import threading
    from code_generator import build_project

    def _bg():
        try:
            result = build_project(opp_id)
            print(f"🔨 Build #{opp_id}: {result.get('success')}, files={result.get('files_generated', 0)}")
        except Exception as e:
            print(f"❌ Build #{opp_id} crashed: {e}")

    t = threading.Thread(target=_bg, daemon=True, name=f"build-{opp_id}")
    t.start()
    return jsonify({
        'success': True,
        'message': f'Build started for opportunity #{opp_id}. Check back in 1-2 minutes.',
        'opportunity_id': opp_id,
        'note': 'Requires OPENROUTER_API_KEY env var to be set.'
    })


@app.route('/api/opportunities/<int:opp_id>/reject', methods=['POST'])
def reject_opportunity(opp_id):
    fields = _set_status(opp_id, 'rejected')
    return jsonify({'success': True, **fields})


@app.route('/api/opportunities/<int:opp_id>/ignore', methods=['POST'])
def ignore_opportunity(opp_id):
    fields = _set_status(opp_id, 'ignored')
    return jsonify({'success': True, **fields})


@app.route('/api/opportunities/<int:opp_id>/rescore', methods=['POST'])
def rescore(opp_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM opportunities WHERE id = ?", (opp_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'not found'}), 404
    opp = dict(row)
    score = calculate_opportunity_score(opp)
    prob = calculate_win_probability(opp)
    ev = calculate_expected_value(int(opp.get('prize_usd') or 0), prob)
    cursor.execute("""
        UPDATE opportunities
        SET opportunity_score = ?, win_probability = ?, expected_value = ?, updated_at = ?
        WHERE id = ?
    """, (score, prob, ev, datetime.now().isoformat(), opp_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'opportunity_score': score, 'win_probability': prob, 'expected_value': ev})


# =============================================================================
# Scanner endpoints
# =============================================================================

def _trigger_scan(scan_id: str):
    engine = ScannerEngine(DB_PATH)
    engine.run_full_scan()


# Rate limiting for /api/scan
import time as _time
_scan_rate_limit = {}  # IP -> [timestamps]
SCAN_RATE_LIMIT_WINDOW = 60  # seconds
SCAN_RATE_LIMIT_MAX = 5  # max scans per window


@app.route('/api/scan', methods=['POST'])
def trigger_scan():
    # Rate limit by IP
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr or 'unknown')
    now = _time.time()
    history = _scan_rate_limit.get(client_ip, [])
    history = [t for t in history if now - t < SCAN_RATE_LIMIT_WINDOW]
    if len(history) >= SCAN_RATE_LIMIT_MAX:
        return jsonify({
            'error': 'rate_limited',
            'message': f'Max {SCAN_RATE_LIMIT_MAX} scans per {SCAN_RATE_LIMIT_WINDOW}s. Slow down.',
            'retry_after': SCAN_RATE_LIMIT_WINDOW
        }), 429
    history.append(now)
    _scan_rate_limit[client_ip] = history
    scan_id = str(uuid.uuid4())[:8]
    t = threading.Thread(target=_trigger_scan, args=(scan_id,), daemon=True)
    t.start()
    return jsonify({'triggered': True, 'scan_id': scan_id})


@app.route('/api/scan/status', methods=['GET'])
def scan_status():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM scan_log ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if not row:
        return jsonify({'status': 'never_run'})
    return jsonify(row_to_dict(row))


# =============================================================================
# Stats / Analytics
# =============================================================================

@app.route('/api/stats', methods=['GET'])
def stats():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) AS c FROM opportunities
        WHERE status NOT IN ('rejected','ignored','expired')
    """)
    total_active = cursor.fetchone()['c']
    cursor.execute("""
        SELECT COUNT(*) AS c FROM opportunities
        WHERE opportunity_score >= 70 AND status NOT IN ('rejected','ignored','expired')
    """)
    high_priority = cursor.fetchone()['c']
    cursor.execute("SELECT COUNT(*) AS c FROM opportunities WHERE status = 'approved'")
    approved = cursor.fetchone()['c']
    cursor.execute("SELECT COUNT(*) AS c FROM opportunities WHERE build_status = 'in_progress'")
    building = cursor.fetchone()['c']
    cursor.execute("SELECT COUNT(*) AS c FROM opportunities WHERE build_status = 'complete' OR submission_confirmed = 1")
    submitted = cursor.fetchone()['c']
    cursor.execute("""
        SELECT AVG(win_probability) AS a FROM opportunities
        WHERE status NOT IN ('rejected','ignored','expired')
    """)
    avg_prob = round(cursor.fetchone()['a'] or 0, 1)
    cursor.execute("""
        SELECT COALESCE(SUM(prize_usd),0) AS s FROM opportunities
        WHERE status NOT IN ('rejected','ignored','expired')
    """)
    total_prize = cursor.fetchone()['s']
    cursor.execute("""
        SELECT COALESCE(SUM(expected_value),0) AS s FROM opportunities
        WHERE status NOT IN ('rejected','ignored','expired')
    """)
    total_ev = cursor.fetchone()['s']
    cursor.execute("SELECT scan_time FROM scan_log ORDER BY id DESC LIMIT 1")
    last_scan = cursor.fetchone()
    conn.close()
    next_scan = None
    if last_scan:
        try:
            t = datetime.fromisoformat(last_scan['scan_time'])
            next_scan = (t + timedelta(hours=int(os.environ.get('SCAN_INTERVAL_HOURS', 4)))).isoformat()
        except Exception:
            pass
    return jsonify({
        'total_active': total_active,
        'high_priority': high_priority,
        'approved': approved,
        'building': building,
        'submitted': submitted,
        'avg_win_probability': avg_prob,
        'total_prize_pool': total_prize,
        'expected_value_total': total_ev,
        'last_scan_time': last_scan['scan_time'] if last_scan else None,
        'next_scan_time': next_scan
    })


@app.route('/api/analytics', methods=['GET'])
def analytics():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT strftime('%Y-%W', created_at) AS week, COUNT(*) AS n, AVG(opportunity_score) AS avg_score
        FROM opportunities
        GROUP BY week
        ORDER BY week DESC
        LIMIT 12
    """)
    by_week = [dict(r) for r in cursor.fetchall()]
    cursor.execute("""
        SELECT source, COUNT(*) AS n, COALESCE(SUM(prize_usd),0) AS pool
        FROM opportunities
        WHERE source IS NOT NULL AND source != ''
        GROUP BY source
        ORDER BY n DESC
    """)
    by_source = [dict(r) for r in cursor.fetchall()]
    cursor.execute("""
        SELECT opportunity_score, win_probability, prize_usd, name
        FROM opportunities
        WHERE status NOT IN ('rejected','ignored','expired')
    """)
    scatter = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({
        'by_week': by_week,
        'by_source': by_source,
        'scatter': scatter
    })


# =============================================================================
# Project files
# =============================================================================

@app.route('/api/projects/<int:opp_id>/files', methods=['GET'])
def project_files(opp_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, filename, file_type, created_at FROM project_files
        WHERE opportunity_id = ?
        ORDER BY created_at
    """, (opp_id,))
    rows = cursor.fetchall()
    conn.close()
    return jsonify([row_to_dict(r) for r in rows])


@app.route('/api/projects/<int:opp_id>/file/<filename>', methods=['GET'])
def project_file(opp_id, filename):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT content FROM project_files
        WHERE opportunity_id = ? AND filename = ?
    """, (opp_id, filename))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'not found'}), 404
    return row['content'], 200, {'Content-Type': 'text/plain; charset=utf-8'}


@app.route('/api/projects/<int:opp_id>/generate', methods=['POST'])
def project_generate(opp_id):
    gen = ProjectFileGenerator()
    count = gen.generate_all(opp_id)
    return jsonify({'success': True, 'files_generated': count})


# =============================================================================
# Build status
# =============================================================================

@app.route('/api/build/status', methods=['GET'])
def build_status():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, build_status, github_repo_url, updated_at
        FROM opportunities
        WHERE build_status != 'none'
        ORDER BY updated_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return jsonify([row_to_dict(r) for r in rows])


@app.route('/api/build/<int:opp_id>/log', methods=['GET'])
def build_log(opp_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT step, status, output, timestamp FROM build_log
        WHERE opportunity_id = ?
        ORDER BY id ASC
    """, (opp_id,))
    rows = cursor.fetchall()
    conn.close()
    return jsonify([row_to_dict(r) for r in rows])


# =============================================================================
# Notifications
# =============================================================================

@app.route('/api/notifications/recent', methods=['GET'])
def recent_notifications():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, opportunity_id, type, message, sent_at, delivered
        FROM notifications
        ORDER BY id DESC LIMIT 20
    """)
    rows = cursor.fetchall()
    conn.close()
    return jsonify([row_to_dict(r) for r in rows])


@app.route('/api/digest', methods=['POST'])
def send_digest():
    ok = daily_digest()
    return jsonify({
        'success': ok,
        'delivered': ok,
        'telegram_enabled': bool(os.environ.get('TELEGRAM_BOT_TOKEN')),
        'message': 'Digest logged to notifications table. Configure TELEGRAM_BOT_TOKEN to deliver to Telegram.'
    })


# =============================================================================
# Settings (read-only stub for now)
# =============================================================================

@app.route('/api/settings', methods=['GET'])
def get_settings():
    return jsonify({
        'scan_interval_hours': int(os.environ.get('SCAN_INTERVAL_HOURS', 4)),
        'min_prize_usd': int(os.environ.get('MIN_PRIZE_USD', 500)),
        'min_score_for_alert': int(os.environ.get('MIN_SCORE_FOR_ALERT', 70)),
        'telegram_enabled': bool(os.environ.get('TELEGRAM_BOT_TOKEN')),
        'discord_enabled': bool(os.environ.get('DISCORD_WEBHOOK_URL')),
        'ntfy_enabled': bool(os.environ.get('NTFY_TOPIC')),
        'github_enabled': bool(os.environ.get('GITHUB_TOKEN')),
        'railway_enabled': bool(os.environ.get('RAILWAY_TOKEN')),
        'vercel_enabled': bool(os.environ.get('VERCEL_TOKEN')),
        'openrouter_enabled': bool(os.environ.get('OPENROUTER_API_KEY')),
    })


# =============================================================================
# v2.1: Research Engine endpoints
# =============================================================================

@app.route('/api/research/scan', methods=['POST'])
def research_scan():
    """Trigger a research scan to learn from past winners."""
    import threading
    from research import run_research_scan

    def _bg():
        result = run_research_scan()
        print(f"🔬 Research scan: {result.get('insights_saved', 0)} insights, {result.get('duration_seconds', 0)}s")

    t = threading.Thread(target=_bg, daemon=True)
    t.start()
    return jsonify({'triggered': True, 'message': 'Research scan running in background.'})


@app.route('/api/research/data', methods=['GET'])
def research_data():
    """Get stored research data (past winners, judge tips)."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM research_data ORDER BY prize_usd DESC LIMIT 50")
    rows = [row_to_dict(r) for r in cursor.fetchall()]
    conn.close()
    # Parse JSON fields
    for r in rows:
        for field in ('tech_stack', 'key_features', 'win_factors'):
            try: r[field] = json.loads(r.get(field) or '[]')
            except: r[field] = []
    return jsonify({'total': len(rows), 'items': rows})


@app.route('/api/research/patterns', methods=['GET'])
def research_patterns():
    """Get aggregated win patterns by category."""
    from research import mine_win_patterns
    return jsonify({'patterns': mine_win_patterns()})


@app.route('/api/research/for/<int:opp_id>', methods=['GET'])
def research_for_opp(opp_id):
    """Get research relevant to a specific opportunity."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM opportunities WHERE id = ?", (opp_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'not found'}), 404
    from research import get_research_for_opportunity
    return jsonify(get_research_for_opportunity(row_to_dict(row)))


# =============================================================================
# v2.1: Auto-Deploy endpoints
# =============================================================================

@app.route('/api/deploy/<int:opp_id>', methods=['POST'])
def deploy_opportunity(opp_id):
    """Deploy the generated project to Railway/Vercel/GitHub."""
    import threading
    from deployer import deploy_project

    def _bg():
        result = deploy_project(opp_id)
        print(f"🚀 Deploy #{opp_id}: {result.get('platform', '?')} - {result.get('success')}")

    t = threading.Thread(target=_bg, daemon=True)
    t.start()
    return jsonify({
        'triggered': True,
        'message': f'Deployment started for #{opp_id}. Check back in 1-2 minutes.',
    })


@app.route('/api/deployments', methods=['GET'])
def list_deployments():
    """List all deployments."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM deployments ORDER BY id DESC LIMIT 50")
    rows = [row_to_dict(r) for r in cursor.fetchall()]
    conn.close()
    for r in rows:
        try: r['build_log'] = json.loads(r.get('build_log') or '{}')
        except: r['build_log'] = {}
    return jsonify({'items': rows})


# =============================================================================
# v2.1: Demo Video endpoints
# =============================================================================

@app.route('/api/video/<int:opp_id>/generate', methods=['POST'])
def video_generate(opp_id):
    """Generate a demo video for an opportunity."""
    import threading
    from video_gen import generate_demo_video

    def _bg():
        result = generate_demo_video(opp_id)
        print(f"🎬 Video #{opp_id}: success={result.get('success')}, file={result.get('file_path', '?')[:60]}")

    t = threading.Thread(target=_bg, daemon=True)
    t.start()
    return jsonify({
        'triggered': True,
        'message': f'Video generation started for #{opp_id}. Takes 1-2 minutes.',
    })


@app.route('/api/videos', methods=['GET'])
def list_videos():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM videos ORDER BY id DESC LIMIT 50")
    rows = [row_to_dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({'items': rows})


# =============================================================================
# v2.1: Submission endpoints
# =============================================================================

@app.route('/api/submit/<int:opp_id>/devpost', methods=['POST'])
def submit_devpost(opp_id):
    """Generate a Devpost submission package."""
    from submitter import submit_to_devpost
    return jsonify(submit_to_devpost(opp_id))


@app.route('/api/submit/<int:opp_id>/package', methods=['GET'])
def submit_package(opp_id):
    """Get a generic submission package (any platform)."""
    from submitter import generate_submission_package
    return jsonify(generate_submission_package(opp_id))


@app.route('/api/submissions', methods=['GET'])
def list_submissions():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM submissions ORDER BY id DESC LIMIT 50")
    rows = [row_to_dict(r) for r in cursor.fetchall()]
    conn.close()
    for r in rows:
        try: r['form_data'] = json.loads(r.get('form_data') or '{}')
        except: r['form_data'] = {}
    return jsonify({'items': rows})


@app.route('/api/submissions/<int:sub_id>/result', methods=['POST'])
def submit_result(sub_id):
    """Record a win/loss result for a submission."""
    data = request.get_json(silent=True) or {}
    result = data.get('result', 'pending')
    notes = data.get('notes', '')
    from submitter import record_result
    ok = record_result(sub_id, result, notes)
    return jsonify({'success': ok})


@app.route('/api/stats/wins', methods=['GET'])
def win_stats():
    from submitter import get_win_loss_stats
    return jsonify(get_win_loss_stats())


# =============================================================================
# Error handlers
# =============================================================================

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'not found'}), 404
    return render_template('index.html', app_name=APP_NAME, version=VERSION, tagline=APP_TAGLINE), 200


@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'internal server error'}), 500


# =============================================================================
# Gunicorn hook — start scheduler in each worker
# =============================================================================

def _start_scheduler():
    try:
        from scheduler import SchedulerManager
        SchedulerManager.start()
    except Exception as e:
        print(f"⚠️  scheduler start failed: {e}")


_start_scheduler()


# =============================================================================
# Dev server
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print(f"🎯 {APP_NAME} v{VERSION}")
    print("=" * 60)
    print(f"📊 Database: {DB_PATH}")
    print(f"🌐 Port: {PORT}")
    print(f"🔧 Debug: {DEBUG}")
    app.run(host=HOST, port=PORT, debug=DEBUG, use_reloader=False)
