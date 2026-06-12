#!/usr/bin/env python3
"""
Challenge Hunter AI - Flask Backend
All API endpoints for opportunity management, scanning, and Telegram integration.
"""

import os
import sqlite3
import json
import time
from datetime import datetime, timedelta
from functools import wraps
import re

from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS

# Import our modules
from scanner import ScannerEngine
from generator import ProjectFileGenerator
from telegram_bot import TelegramBotHandler

# =============================================================================
# CONFIGURATION
# =============================================================================

DB_PATH = os.environ.get('DB_PATH', os.path.join(os.path.dirname(__file__), 'opportunities.db'))
PORT = int(os.environ.get('PORT', 5000))
DEBUG = os.environ.get('FLASK_ENV', 'production') == 'development'

# =============================================================================
# DATABASE INITIALIZATION (runs on module load - works with Gunicorn)
# =============================================================================

def init_database():
    """Initialize database with schema and seed data if not exists. Called on module load."""
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    
    # Check if database exists
    db_exists = os.path.exists(DB_PATH)
    
    if not db_exists:
        print(f"📦 Database not found at {DB_PATH}")
        print("   Initializing new database...")
        
        # Create database and schema
        conn = sqlite3.connect(DB_PATH)
        
        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
            conn.executescript(schema_sql)
            print("   ✅ Schema created")
        else:
            # Fallback: create tables manually
            _create_schema_manually(conn)
            print("   ✅ Schema created (manual)")
        
        conn.commit()
        conn.close()
        
        # Seed initial data
        _seed_initial_data()
        print("   ✅ Seed data inserted")
        print("   ✅ Database initialization complete")
    else:
        print(f"📊 Database found at {DB_PATH}")

def _create_schema_manually(conn):
    """Create schema tables manually if schema.sql not found"""
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            prize_usd INTEGER DEFAULT 0,
            deadline TEXT,
            days_remaining INTEGER,
            rules_summary TEXT,
            ai_policy TEXT DEFAULT 'unclear',
            eligibility TEXT,
            difficulty TEXT DEFAULT 'medium',
            opportunity_score INTEGER DEFAULT 0,
            win_probability INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            analysis_json TEXT,
            source TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        
        CREATE TABLE IF NOT EXISTS project_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opportunity_id INTEGER REFERENCES opportunities(id),
            filename TEXT,
            content TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        
        CREATE TABLE IF NOT EXISTS scan_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_time TEXT DEFAULT (datetime('now')),
            sources_scanned INTEGER,
            new_found INTEGER,
            errors TEXT
        );
        
        CREATE INDEX IF NOT EXISTS idx_opportunities_status ON opportunities(status);
        CREATE INDEX IF NOT EXISTS idx_opportunities_score ON opportunities(opportunity_score DESC);
        CREATE INDEX IF NOT EXISTS idx_opportunities_deadline ON opportunities(deadline);
        CREATE INDEX IF NOT EXISTS idx_opportunities_source ON opportunities(source);
        CREATE INDEX IF NOT EXISTS idx_project_files_opportunity ON project_files(opportunity_id);
    """)

def _seed_initial_data():
    """Insert seed data if database is empty"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if already seeded
    cursor.execute("SELECT COUNT(*) FROM opportunities")
    count = cursor.fetchone()[0]
    if count > 0:
        conn.close()
        return
    
    today = datetime.now()
    deadline_30 = (today + timedelta(days=30)).strftime('%Y-%m-%d')
    deadline_21 = (today + timedelta(days=21)).strftime('%Y-%m-%d')
    deadline_45 = (today + timedelta(days=45)).strftime('%Y-%m-%d')
    
    seed_records = [
        {
            'name': 'Devpost AI Innovation Challenge 2025',
            'url': 'https://devpost.com/hackathons',
            'prize_usd': 10000,
            'deadline': deadline_30,
            'ai_policy': 'allowed',
            'difficulty': 'medium',
            'source': 'Devpost',
            'eligibility': 'Global, solo or team',
            'rules_summary': 'Build innovative projects using AI tools. Any tech stack allowed. Submit a working demo and 2-minute video.',
        },
        {
            'name': 'Hugging Face Open Source AI Grant',
            'url': 'https://huggingface.co/grants',
            'prize_usd': 5000,
            'deadline': deadline_21,
            'ai_policy': 'allowed',
            'difficulty': 'easy',
            'source': 'HuggingFace',
            'eligibility': 'Global, solo',
            'rules_summary': 'Create open source AI projects using Hugging Face tools. Must be fully open source with code public.',
        },
        {
            'name': 'Solana Summer Builder Grant 2025',
            'url': 'https://solana.com/grants',
            'prize_usd': 25000,
            'deadline': deadline_45,
            'ai_policy': 'allowed',
            'difficulty': 'hard',
            'source': 'Solana',
            'eligibility': 'Global, solo or team',
            'rules_summary': 'Build on Solana blockchain. Must submit working product. Multiple grant tiers available up to $50K.',
        },
    ]
    
    def calc_score(prize_usd, days_rem, ai_pol, elig, diff, src):
        score = 50
        if prize_usd > 10000: score += 15
        elif prize_usd >= 5000: score += 10
        elif prize_usd >= 1000: score += 5
        if days_rem and 14 <= days_rem <= 45: score += 10
        elif days_rem and 7 <= days_rem < 14: score += 5
        if ai_pol == 'allowed': score += 15
        elif ai_pol == 'unclear': score -= 15
        if elig:
            if 'solo' in elig.lower(): score += 5
            if 'global' in elig.lower(): score += 5
            if 'team only' in elig.lower(): score -= 10
        if diff == 'easy': score += 5
        elif diff == 'hard': score -= 5
        corp = ['google', 'microsoft', 'amazon', 'meta', 'apple', 'nvidia']
        if src and any(s in src.lower() for s in corp): score -= 10
        return max(0, min(100, score))
    
    def calc_prob(prize_usd, days_rem, ai_pol, diff, elig, src):
        prob = 30
        if prize_usd > 5000: prob += 10
        if days_rem and days_rem > 14: prob += 10
        if ai_pol == 'allowed': prob += 15
        corp = ['google', 'microsoft', 'amazon', 'meta', 'apple', 'nvidia']
        if src and any(s in src.lower() for s in corp): prob -= 20
        if diff == 'easy': prob += 10
        elif diff == 'hard': prob -= 10
        if elig and 'solo' not in elig.lower(): prob -= 10
        return max(0, min(100, prob))
    
    for record in seed_records:
        deadline_dt = datetime.strptime(record['deadline'], '%Y-%m-%d')
        days_rem = (deadline_dt - today).days
        score = calc_score(record['prize_usd'], days_rem, record['ai_policy'], record['eligibility'], record['difficulty'], record['source'])
        prob = calc_prob(record['prize_usd'], days_rem, record['ai_policy'], record['difficulty'], record['eligibility'], record['source'])
        
        analysis = {
            "summary": f"A {record['difficulty']} opportunity with ${record['prize_usd']} prize.",
            "requirements": ["Build a functional demo", "Submit before deadline", "Prepare video demo", "Write README"],
            "risks": ["High competition", "Deadline pressure"],
            "win_probability_reasoning": f"Based on {record['difficulty']} difficulty, ${record['prize_usd']} prize.",
            "build_complexity": record['difficulty'],
            "recommended_project": {"name": record['name'][:30].replace(' ', '-').lower(), "tech_stack": ["Python", "Flask", "React"]},
            "submission_strategy": "Focus on demo quality and documentation.",
            "recommended_action": "approve"
        }
        
        try:
            cursor.execute("""
                INSERT INTO opportunities (
                    name, url, prize_usd, deadline, days_remaining,
                    rules_summary, ai_policy, eligibility, difficulty,
                    opportunity_score, win_probability, status, analysis_json, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record['name'], record['url'], record['prize_usd'], record['deadline'], days_rem,
                record.get('rules_summary', ''), record['ai_policy'], record['eligibility'],
                record['difficulty'], score, prob, 'pending', json.dumps(analysis), record['source']
            ))
        except sqlite3.IntegrityError:
            pass
    
    # Log the seed
    cursor.execute("INSERT INTO scan_log (scan_time, sources_scanned, new_found, errors) VALUES (?, ?, ?, ?)",
                   (datetime.now().isoformat(), 0, len(seed_records), None))
    
    conn.commit()
    conn.close()

# Initialize database on module load (before Flask app creation)
init_database()

# =============================================================================
# FLASK APP SETUP
# =============================================================================

app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'challenge-hunter-secret-key-change-in-production')
CORS(app)

# =============================================================================
# DATABASE HELPERS
# =============================================================================

def get_db_connection():
    """Get a database connection with row factory for dict-like access"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row):
    """Convert sqlite3.Row to dictionary"""
    if row is None:
        return None
    return dict(row)


def calculate_days_remaining(deadline_str):
    """Calculate days remaining from deadline string"""
    if not deadline_str:
        return None
    try:
        deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
        delta = deadline - datetime.now()
        return max(0, delta.days)
    except ValueError:
        return None


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.route('/')
def index():
    """Serve the main dashboard HTML"""
    return render_template('index.html')


@app.route('/health')
def health():
    """Health check endpoint for hosting platform"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'service': 'Challenge Hunter AI'
    })


@app.route('/api/opportunities', methods=['GET'])
def get_opportunities():
    """
    GET /api/opportunities
    Query params:
      - status: filter by status (pending, approved, rejected, ignored, expired)
      - min_score: minimum opportunity score
      - sort_by: score | deadline | prize (default: score)
    Returns JSON array of matching opportunities
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Build query
    query = "SELECT * FROM opportunities WHERE 1=1"
    params = []

    # Filter by status
    status = request.args.get('status')
    if status:
        query += " AND status = ?"
        params.append(status)

    # Filter by minimum score
    min_score = request.args.get('min_score', type=int)
    if min_score:
        query += " AND opportunity_score >= ?"
        params.append(min_score)

    # Sorting
    sort_by = request.args.get('sort_by', 'score')
    if sort_by == 'deadline':
        query += " ORDER BY days_remaining ASC"
    elif sort_by == 'prize':
        query += " ORDER BY prize_usd DESC"
    else:
        query += " ORDER BY opportunity_score DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    # Convert to list of dicts and add computed days_remaining
    opportunities = []
    for row in rows:
        opp = row_to_dict(row)
        if opp.get('deadline'):
            opp['days_remaining'] = calculate_days_remaining(opp['deadline'])
        # Parse analysis_json if string
        if opp.get('analysis_json') and isinstance(opp['analysis_json'], str):
            try:
                opp['analysis_json'] = json.loads(opp['analysis_json'])
            except json.JSONDecodeError:
                pass
        opportunities.append(opp)

    return jsonify(opportunities)


@app.route('/api/opportunities/<int:opportunity_id>', methods=['GET'])
def get_opportunity(opportunity_id):
    """
    GET /api/opportunities/<id>
    Returns full opportunity details with parsed analysis_json
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM opportunities WHERE id = ?", (opportunity_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({'error': 'Opportunity not found'}), 404

    opp = row_to_dict(row)
    if opp.get('deadline'):
        opp['days_remaining'] = calculate_days_remaining(opp['deadline'])

    # Parse analysis_json
    if opp.get('analysis_json') and isinstance(opp['analysis_json'], str):
        try:
            opp['analysis_json'] = json.loads(opp['analysis_json'])
        except json.JSONDecodeError:
            opp['analysis_json'] = None

    return jsonify(opp)


@app.route('/api/opportunities/<int:opportunity_id>/approve', methods=['POST'])
def approve_opportunity(opportunity_id):
    """
    POST /api/opportunities/<id>/approve
    Sets status to 'approved', generates project files, sends Telegram notification
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get opportunity
    cursor.execute("SELECT * FROM opportunities WHERE id = ?", (opportunity_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return jsonify({'error': 'Opportunity not found'}), 404

    opp = row_to_dict(row)

    # Update status
    cursor.execute("""
        UPDATE opportunities
        SET status = 'approved', updated_at = ?
        WHERE id = ?
    """, (datetime.now().isoformat(), opportunity_id))
    conn.commit()

    # Generate project files
    generator = ProjectFileGenerator(DB_PATH)
    files_created = generator.generate_all(opportunity_id, opp)
    print(f"📄 Generated {files_created} project files for opportunity {opportunity_id}")

    # Send Telegram notification
    try:
        telegram = TelegramBotHandler()
        telegram.send_approval_notification(opp)
        print(f"📱 Telegram notification sent for opportunity {opportunity_id}")
    except Exception as e:
        print(f"⚠️  Telegram notification failed: {e}")

    conn.close()

    return jsonify({
        'success': True,
        'message': f'Opportunity approved. {files_created} project files generated.',
        'files_created': files_created
    })


@app.route('/api/opportunities/<int:opportunity_id>/reject', methods=['POST'])
def reject_opportunity(opportunity_id):
    """
    POST /api/opportunities/<id>/reject
    Sets status to 'rejected'
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE opportunities
        SET status = 'rejected', updated_at = ?
        WHERE id = ?
    """, (datetime.now().isoformat(), opportunity_id))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Opportunity rejected'})


@app.route('/api/opportunities/<int:opportunity_id>/ignore', methods=['POST'])
def ignore_opportunity(opportunity_id):
    """
    POST /api/opportunities/<id>/ignore
    Sets status to 'ignored'
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE opportunities
        SET status = 'ignored', updated_at = ?
        WHERE id = ?
    """, (datetime.now().isoformat(), opportunity_id))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Opportunity ignored'})


@app.route('/api/scan', methods=['POST'])
def trigger_scan():
    """
    POST /api/scan
    Triggers the scanner engine manually
    Returns count of new opportunities found
    """
    try:
        scanner = ScannerEngine(DB_PATH)
        result = scanner.run_full_scan()
        return jsonify({
            'success': True,
            'new_found': result.get('new_found', 0),
            'sources_scanned': result.get('sources_scanned', 0),
            'errors': result.get('errors', [])
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """
    GET /api/stats
    Returns dashboard statistics
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Total active (not rejected/ignored/expired)
    cursor.execute("""
        SELECT COUNT(*) as count FROM opportunities
        WHERE status NOT IN ('rejected', 'ignored', 'expired')
    """)
    total_active = cursor.fetchone()['count']

    # High priority (score >= 70)
    cursor.execute("""
        SELECT COUNT(*) as count FROM opportunities
        WHERE opportunity_score >= 70 AND status NOT IN ('rejected', 'ignored', 'expired')
    """)
    high_priority = cursor.fetchone()['count']

    # Average win probability
    cursor.execute("""
        SELECT AVG(win_probability) as avg FROM opportunities
        WHERE status NOT IN ('rejected', 'ignored', 'expired')
    """)
    avg_win_prob = cursor.fetchone()['avg'] or 0

    # Total prize pool (sum of all active opportunities)
    cursor.execute("""
        SELECT SUM(prize_usd) as total FROM opportunities
        WHERE status NOT IN ('rejected', 'ignored', 'expired')
    """)
    total_prize = cursor.fetchone()['total'] or 0

    # Last scan time
    cursor.execute("""
        SELECT scan_time FROM scan_log
        ORDER BY scan_time DESC LIMIT 1
    """)
    last_scan_row = cursor.fetchone()
    last_scan_time = last_scan_row['scan_time'] if last_scan_row else None

    conn.close()

    return jsonify({
        'total_active': total_active,
        'high_priority': high_priority,
        'avg_win_probability': round(avg_win_prob, 1),
        'total_prize_pool': total_prize,
        'last_scan_time': last_scan_time
    })


@app.route('/api/projects/<int:opportunity_id>/files', methods=['GET'])
def get_project_files(opportunity_id):
    """
    GET /api/projects/<opportunity_id>/files
    Returns list of generated filenames for that opportunity
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, filename, created_at FROM project_files
        WHERE opportunity_id = ?
        ORDER BY created_at
    """, (opportunity_id,))

    rows = cursor.fetchall()
    conn.close()

    files = [row_to_dict(row) for row in rows]
    return jsonify(files)


@app.route('/api/projects/<int:opportunity_id>/file/<filename>', methods=['GET'])
def get_project_file(opportunity_id, filename):
    """
    GET /api/projects/<opportunity_id>/file/<filename>
    Returns file content as plain text
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT content FROM project_files
        WHERE opportunity_id = ? AND filename = ?
    """, (opportunity_id, filename))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({'error': 'File not found'}), 404

    return row['content'], 200, {'Content-Type': 'text/plain; charset=utf-8'}


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("🎯 Challenge Hunter AI - Backend Server")
    print("=" * 60)
    print(f"📊 Database: {DB_PATH}")
    print(f"🌐 Port: {PORT}")
    print(f"🔧 Debug: {DEBUG}")
    print()

    # Start scanner scheduler (runs every 6 hours)
    try:
        scanner = ScannerEngine(DB_PATH)
        scanner.start_scheduler()
        print("📅 Scanner scheduler started (runs every 6 hours)")
    except Exception as e:
        print(f"⚠️  Scanner scheduler failed to start: {e}")

    # Start Flask server
    print()
    print("🚀 Server running at http://localhost:5000")
    print("📱 Telegram bot polling (if configured)")
    print()
    print("Press Ctrl+C to stop")
    print()

    app.run(
        host='0.0.0.0',
        port=PORT,
        debug=DEBUG,
        use_reloader=False  # Prevent double scheduler in debug mode
    )