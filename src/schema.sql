-- ============================================================================
-- Challenge Hunter AI v2.1 — Extended Schema
-- Adds: research data, deployments, videos, submissions, outcomes
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Research: scraped prior winners, judge preferences, winning patterns
-- ----------------------------------------------------------------------------
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
    tech_stack TEXT,                    -- JSON
    key_features TEXT,                  -- JSON array
    judge_comments TEXT,
    win_factors TEXT,                   -- JSON: what made it win
    scraped_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_research_source ON research_data(source);
CREATE INDEX IF NOT EXISTS idx_research_category ON research_data(category);

-- ----------------------------------------------------------------------------
-- Deployments: track each deployment per opportunity
-- ----------------------------------------------------------------------------
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

-- ----------------------------------------------------------------------------
-- Videos: demo videos generated for each opportunity
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id INTEGER REFERENCES opportunities(id),
    title TEXT,
    script TEXT,                        -- generated voiceover script
    duration_seconds INTEGER,
    file_path TEXT,
    status TEXT DEFAULT 'pending',
    voice TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_videos_opp ON videos(opportunity_id);

-- ----------------------------------------------------------------------------
-- Submissions: track each platform submission
-- ----------------------------------------------------------------------------
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

-- ----------------------------------------------------------------------------
-- Win patterns: ML learning from past wins
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS win_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern TEXT,                       -- e.g. "AI + Web3 + solo + < 7d deadline"
    frequency INTEGER DEFAULT 0,
    win_rate REAL DEFAULT 0,             -- 0.0 - 1.0
    avg_prize REAL,
    examples TEXT,                      -- JSON array of opp IDs
    updated_at TEXT DEFAULT (datetime('now'))
);

-- ----------------------------------------------------------------------------
-- Extend opportunities table with new fields
-- ----------------------------------------------------------------------------
-- Add demo_video_id, deployment_id if they don't exist
-- SQLite doesn't support IF NOT EXISTS for ALTER TABLE ADD COLUMN, so
-- we use a try/catch via Python migration. The columns are added below
-- for documentation; the actual ALTER is done in app.py's _ensure_db().

-- opportunities new columns:
--   win_probability_modeled REAL         (model-predicted, learned from past data)
--   research_completeness INTEGER       (0-100, how much research we have)
--   estimated_build_minutes INTEGER     (time-to-build estimate)

-- ============================================================================
-- Indexes for analytics
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_opportunities_created ON opportunities(created_at);
CREATE INDEX IF NOT EXISTS idx_opportunities_prize ON opportunities(prize_usd);
