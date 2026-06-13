-- ============================================================================
-- Challenge Hunter AI v2.0 — Database Schema
-- SQLite Database: opportunities.db
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Opportunities: every hackathon, grant, bounty, competition discovered
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    prize_usd INTEGER DEFAULT 0,
    prize_text TEXT,
    deadline TEXT,
    days_remaining INTEGER,
    rules_summary TEXT,
    ai_policy TEXT DEFAULT 'unclear',
    eligibility TEXT,
    team_size TEXT,
    difficulty TEXT DEFAULT 'medium',
    opportunity_score INTEGER DEFAULT 0,
    win_probability INTEGER DEFAULT 0,
    expected_value REAL DEFAULT 0,
    status TEXT DEFAULT 'pending',
    analysis_json TEXT,
    source TEXT,
    source_url TEXT,
    tags TEXT,
    build_status TEXT DEFAULT 'none',
    github_repo_url TEXT,
    submission_url TEXT,
    submission_confirmed INTEGER DEFAULT 0,
    alert_sent INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- ----------------------------------------------------------------------------
-- Project files: generated artefacts for each approved opportunity
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS project_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id INTEGER REFERENCES opportunities(id),
    filename TEXT,
    content TEXT,
    file_type TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- ----------------------------------------------------------------------------
-- Scan log: every scanner run
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scan_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_time TEXT DEFAULT (datetime('now')),
    sources_scanned INTEGER DEFAULT 0,
    new_found INTEGER DEFAULT 0,
    high_value_found INTEGER DEFAULT 0,
    errors TEXT,
    duration_seconds REAL
);

-- ----------------------------------------------------------------------------
-- Build log: every step of the autonomous builder
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS build_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id INTEGER REFERENCES opportunities(id),
    step TEXT,
    status TEXT,
    output TEXT,
    timestamp TEXT DEFAULT (datetime('now'))
);

-- ----------------------------------------------------------------------------
-- Notifications: outbound alerts and digests
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id INTEGER,
    type TEXT,
    message TEXT,
    sent_at TEXT DEFAULT (datetime('now')),
    delivered INTEGER DEFAULT 0
);

-- ----------------------------------------------------------------------------
-- Indexes
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_opportunities_status ON opportunities(status);
CREATE INDEX IF NOT EXISTS idx_opportunities_score ON opportunities(opportunity_score DESC);
CREATE INDEX IF NOT EXISTS idx_opportunities_deadline ON opportunities(deadline);
CREATE INDEX IF NOT EXISTS idx_opportunities_source ON opportunities(source);
CREATE INDEX IF NOT EXISTS idx_opportunities_ai_policy ON opportunities(ai_policy);
CREATE INDEX IF NOT EXISTS idx_opportunities_build_status ON opportunities(build_status);
CREATE INDEX IF NOT EXISTS idx_project_files_opportunity ON project_files(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_build_log_opportunity ON build_log(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_notifications_opportunity ON notifications(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(type);
