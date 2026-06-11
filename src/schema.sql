-- Challenge Hunter AI Database Schema
-- SQLite Database: opportunities.db

-- Opportunities table: stores all discovered hackathons, grants, competitions
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

-- Project files table: generated project plans per opportunity
CREATE TABLE IF NOT EXISTS project_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id INTEGER REFERENCES opportunities(id),
    filename TEXT,
    content TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Scan log table: tracks scanner execution history
CREATE TABLE IF NOT EXISTS scan_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_time TEXT DEFAULT (datetime('now')),
    sources_scanned INTEGER,
    new_found INTEGER,
    errors TEXT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_opportunities_status ON opportunities(status);
CREATE INDEX IF NOT EXISTS idx_opportunities_score ON opportunities(opportunity_score DESC);
CREATE INDEX IF NOT EXISTS idx_opportunities_deadline ON opportunities(deadline);
CREATE INDEX IF NOT EXISTS idx_opportunities_source ON opportunities(source);
CREATE INDEX IF NOT EXISTS idx_project_files_opportunity ON project_files(opportunity_id);