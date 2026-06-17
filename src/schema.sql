-- ============================================================================
-- Challenge Hunter AI v2.1 — Complete Database Schema
-- ============================================================================

-- ============================================================================
-- v2.0 CORE TABLES (must be defined first — other tables reference them)
-- ============================================================================

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

CREATE TABLE IF NOT EXISTS project_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id INTEGER REFERENCES opportunities(id),
    filename TEXT,
    content TEXT,
    file_type TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS scan_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_time TEXT DEFAULT (datetime('now')),
    sources_scanned INTEGER DEFAULT 0,
    new_found INTEGER DEFAULT 0,
    high_value_found INTEGER DEFAULT 0,
    errors TEXT,
    duration_seconds REAL
);

CREATE TABLE IF NOT EXISTS build_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id INTEGER REFERENCES opportunities(id),
    step TEXT,
    status TEXT,
    output TEXT,
    timestamp TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id INTEGER,
    type TEXT,
    message TEXT,
    sent_at TEXT DEFAULT (datetime('now')),
    delivered INTEGER DEFAULT 0
);

-- Core indexes
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

-- ============================================================================
-- v2.1 NEW TABLES
-- ============================================================================

-- Research: scraped prior winners, judge preferences, winning patterns
CREATE TABLE IF NOT EXISTS research_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT,
    source_url TEXT,
    title TEXT,
    category TEXT,
    prize_usd INTEGER,
    winner_name TEXT,
    winner_url TEXT,
    project_description TEXT,
    tech_stack TEXT,
    key_features TEXT,
    judge_comments TEXT,
    win_factors TEXT,
    scraped_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_research_source ON research_data(source);
CREATE INDEX IF NOT EXISTS idx_research_category ON research_data(category);

-- Deployments: track each deployment per opportunity
CREATE TABLE IF NOT EXISTS deployments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id INTEGER REFERENCES opportunities(id),
    platform TEXT,
    service_id TEXT,
    deploy_url TEXT,
    status TEXT DEFAULT 'pending',
    build_log TEXT,
    deployed_at TEXT,
    last_check TEXT,
    response_time_ms INTEGER
);

CREATE INDEX IF NOT EXISTS idx_deployments_opp ON deployments(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_deployments_status ON deployments(status);

-- Videos: demo videos generated for each opportunity
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id INTEGER REFERENCES opportunities(id),
    title TEXT,
    script TEXT,
    duration_seconds INTEGER,
    file_path TEXT,
    status TEXT DEFAULT 'pending',
    voice TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_videos_opp ON videos(opportunity_id);

-- Submissions: track each platform submission
CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id INTEGER REFERENCES opportunities(id),
    platform TEXT,
    submission_url TEXT,
    confirmation_code TEXT,
    status TEXT DEFAULT 'pending',
    form_data TEXT,
    submitted_at TEXT,
    result TEXT,
    result_date TEXT,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_submissions_opp ON submissions(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_submissions_status ON submissions(status);
CREATE INDEX IF NOT EXISTS idx_submissions_result ON submissions(result);

-- Win patterns: ML learning from past wins
CREATE TABLE IF NOT EXISTS win_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern TEXT,
    frequency INTEGER DEFAULT 0,
    win_rate REAL DEFAULT 0,
    avg_prize REAL,
    examples TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);

-- ============================================================================
-- Analytics indexes
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_opportunities_created ON opportunities(created_at);
CREATE INDEX IF NOT EXISTS idx_opportunities_prize ON opportunities(prize_usd);
