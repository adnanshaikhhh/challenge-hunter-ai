#!/usr/bin/env python3
"""
Challenge Hunter AI v2.0 — Centralised configuration
Every tunable lives here. No magic numbers in module bodies.
"""

import os
from pathlib import Path

# ----------------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
PROJECTS_DIR = BASE_DIR.parent / 'projects'
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = os.environ.get('DB_PATH', str(BASE_DIR / 'opportunities.db'))
SCHEMA_PATH = str(BASE_DIR / 'schema.sql')

# ----------------------------------------------------------------------------
# Server
# ----------------------------------------------------------------------------

PORT = int(os.environ.get('PORT', 5000))
DEBUG = os.environ.get('FLASK_ENV', 'production') == 'development'
SECRET_KEY = os.environ.get('SECRET_KEY', 'change-this-in-prod-please-32chars-min')
HOST = '0.0.0.0'

# ----------------------------------------------------------------------------
# Scanner
# ----------------------------------------------------------------------------

SCAN_INTERVAL_HOURS = int(os.environ.get('SCAN_INTERVAL_HOURS', 4))
MIN_PRIZE_USD = int(os.environ.get('MIN_PRIZE_USD', 500))
MIN_SCORE_FOR_ALERT = int(os.environ.get('MIN_SCORE_FOR_ALERT', 70))
REQUEST_DELAY_SECONDS = 2           # sleep between external HTTP calls
AI_ANALYSIS_DELAY_SECONDS = 3       # sleep between AI analysis calls
EXPIRY_THRESHOLD_HOURS = 72         # mark pending as expired after this

ENABLE_GITHUB_ACTIONS_SCAN = os.environ.get('ENABLE_GITHUB_ACTIONS_SCAN', 'true').lower() == 'true'

# ----------------------------------------------------------------------------
# AI policy detection
# ----------------------------------------------------------------------------

AI_ALLOWED_KEYWORDS = [
    'ai allowed', 'ai tools permitted', 'use any tools', 'vibe coding',
    'agentic', 'llm allowed', 'ai-assisted', 'generative ai', 'chatgpt',
    'copilot', 'claude', 'automation allowed', 'ai-powered', 'use ai freely',
    'no restrictions on tools', 'any programming tool', 'open source ai',
    'llms permitted', 'machine learning allowed'
]

AI_BANNED_KEYWORDS = [
    'no ai', 'ai prohibited', 'must be human-written', 'no llm', 'manual only',
    'no automated', 'no machine learning', 'no generative ai',
    'human coding only', 'no artificial intelligence', 'ai tools not allowed',
    'no chatgpt', 'human-only', 'no ai tools'
]

# ----------------------------------------------------------------------------
# Discovery sources
# ----------------------------------------------------------------------------

HACKATHON_SOURCES = [
    'https://devpost.com/hackathons?challenge_type=all&sort_by=deadline',
    'https://mlh.io/seasons',
    'https://hackerearth.com/challenges/',
    'https://lablab.ai/event',
    'https://devfolio.co/hackathons',
    'https://unstop.com/hackathons',
    'https://challengerocket.com/',
]

AI_ECOSYSTEM_SOURCES = [
    'https://huggingface.co/events',
    'https://kaggle.com/competitions',
    'https://openai.com/blog',
    'https://www.anthropic.com/news',
]

BUILDER_PLATFORM_SOURCES = [
    'https://replit.com/bounties',
    'https://github.com/explore',
]

BIG_TECH_GRANT_SOURCES = [
    'https://aws.amazon.com/startups/',
    'https://cloud.google.com/startup',
    'https://www.microsoft.com/en-us/startups',
    'https://vercel.com/blog',
]

WEB3_SOURCES = [
    'https://solana.com/grants',
    'https://ethereum.org/en/community/grants/',
    'https://gitcoin.co/hackathon/list',
    'https://base.org/grants',
]

STARTUP_GRANT_SOURCES = [
    'https://pioneer.app',
    'https://www.ycombinator.com/blog',
    'https://producthunt.com/discussions',
]

ALL_SOURCES = (
    HACKATHON_SOURCES
    + AI_ECOSYSTEM_SOURCES
    + BUILDER_PLATFORM_SOURCES
    + BIG_TECH_GRANT_SOURCES
    + WEB3_SOURCES
    + STARTUP_GRANT_SOURCES
)

DUCKDUCKGO_QUERIES = [
    'AI hackathon 2025 cash prize open registration',
    'vibe coding competition prize 2025',
    'agentic AI builder challenge grant 2025',
    'startup pitch competition AI tools allowed 2025',
    'open source AI grant 2025 apply',
    'no-code AI competition 2025 solo',
    'Solana builder grant 2025 open',
    'hackathon prize 2025 AI allowed submit',
    'innovation challenge 2025 cash prize',
    'developer grant program 2025 open applications',
]

# ----------------------------------------------------------------------------
# Notifications
# ----------------------------------------------------------------------------

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL', '')
NTFY_TOPIC = os.environ.get('NTFY_TOPIC', '')

# ----------------------------------------------------------------------------
# GitHub (for auto repo creation)
# ----------------------------------------------------------------------------

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
GITHUB_USERNAME = os.environ.get('GITHUB_USERNAME', '')

# ----------------------------------------------------------------------------
# Scheduler
# ----------------------------------------------------------------------------

DAILY_DIGEST_HOUR_UTC = 9
WEEKLY_SUMMARY_DAY = 0  # Monday (0=Mon in cron)

# ----------------------------------------------------------------------------
# HTTP user agent
# ----------------------------------------------------------------------------

USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)

HTTP_HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

# ----------------------------------------------------------------------------
# Version
# ----------------------------------------------------------------------------

VERSION = '2.0.0'
APP_NAME = 'Challenge Hunter AI'
APP_TAGLINE = 'Autonomous opportunity detection and execution platform'
