# 🎯 Challenge Hunter AI

> Autonomous opportunity-hunting platform for AI-friendly
> hackathons, grants, and builder competitions worldwide.

## Live Demo

**[🚀 Railway Deployment](https://challenge-hunter-ai.up.railway.app)**

## Features

- **Autonomous Discovery** — Scans 8+ platforms for new AI-friendly opportunities
- **AI-Powered Scoring** — Calculates opportunity score (0-100) and win probability using formula-based analysis
- **Telegram Alerts** — Instant notifications when high-value opportunities (score ≥ 70) are found
- **Project Generator** — One-click approval generates 5 project files: README, architecture, task list, demo plan, and submission checklist
- **Full Web Dashboard** — Dark-themed, glassmorphism UI with filter/sort/search, live stats, and analysis modal
- **Scheduled Scanning** — Automatic scans every 6 hours via APScheduler background worker
- **Demo Mode** — Pre-seeded with 3 realistic opportunities for immediate testing

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/adnanshaikhhh/challenge-hunter-ai.git
cd challenge-hunter-ai

# 2. Install Python dependencies
pip install -r src/requirements.txt

# 3. Set up environment
cp src/.env.example src/.env
# Edit src/.env with your TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID

# 4. Create and seed database
python src/seed.py

# 5. Run the app
python src/app.py

# 6. Open in browser
open http://localhost:5000
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Flask 2.3+ with flask-cors |
| Database | SQLite (opportunities.db) |
| Scheduler | APScheduler (BackgroundScheduler, 6h interval) |
| Telegram | python-telegram-bot v20+ |
| Web Scraping | requests + BeautifulSoup4 |
| HTTP Client | requests + lxml parser |
| Frontend | Vanilla HTML/CSS/JS (no build tools) |
| Deployment | Railway / Render |

## Architecture

```
challenge-hunter-ai/
├── src/
│   ├── app.py           # Flask backend, all API endpoints
│   ├── scanner.py       # Discovery engine, scoring, AI analysis
│   ├── telegram_bot.py  # Telegram bot handler + commands
│   ├── generator.py     # Project file generator (5 files)
│   ├── seed.py          # Database seeder with 3 starter opportunities
│   ├── schema.sql       # SQLite schema (3 tables)
│   ├── requirements.txt # All Python dependencies
│   ├── templates/
│   │   └── index.html   # Full dashboard UI (1526 lines)
│   └── opportunities.db # SQLite database (created at runtime)
├── docs/
│   └── RECOVERY.md      # Project status and architecture docs
├── deploy/
│   ├── render.yaml      # Render deployment configuration
│   ├── Procfile         # Railway/Render start command
│   └── runtime.txt      # Python version (3.11.0)
└── github/
    └── (git repository initialized here)
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | — | From @BotFather on Telegram |
| `TELEGRAM_CHAT_ID` | Yes | — | Your personal Telegram chat ID |
| `SCAN_INTERVAL_HOURS` | No | 6 | Hours between automatic scans |
| `MIN_PRIZE_USD` | No | 500 | Minimum prize to track |
| `MIN_SCORE_FOR_ALERT` | No | 70 | Score threshold for Telegram alert |
| `FLASK_ENV` | No | production | `production` or `development` |
| `SECRET_KEY` | No | (unsafe default) | Change to random string in production |
| `PORT` | No | 5000 | Server port |
| `DB_PATH` | No | (local) | Path to SQLite database |

## Deploy to Railway

Railway is the recommended platform (free tier available):

```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login
railway login

# 3. Initialize project
cd challenge-hunter-ai
railway init

# 4. Link to existing folder
railway up --select

# 5. Add environment variables
railway variables set TELEGRAM_BOT_TOKEN=your_token
railway variables set TELEGRAM_CHAT_ID=your_chat_id

# 6. Deploy
railway up

# 7. Get public URL
railway domain
```

## Deploy to Render (Alternative)

```bash
# Connect GitHub repo to Render.com
# Use render.yaml from deploy/ folder
# Or use these settings:
#   Build Command: pip install -r src/requirements.txt
#   Start Command: gunicorn src.app:app --bind 0.0.0.0:$PORT --workers 2
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Serve dashboard UI |
| GET | `/health` | Health check |
| GET | `/api/opportunities` | List opportunities (filter: status, min_score, sort_by) |
| GET | `/api/opportunities/<id>` | Get full opportunity details |
| POST | `/api/opportunities/<id>/approve` | Approve + generate project files |
| POST | `/api/opportunities/<id>/reject` | Reject opportunity |
| POST | `/api/opportunities/<id>/ignore` | Ignore opportunity |
| POST | `/api/scan` | Trigger manual scan |
| GET | `/api/stats` | Dashboard statistics |
| GET | `/api/projects/<id>/files` | List generated files |
| GET | `/api/projects/<id>/file/<filename>` | Get file content |

## Telegram Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/list` | Top 5 opportunities by score |
| `/stats` | Dashboard statistics |
| `/scan` | Trigger manual scan |
| `/help` | All commands |

Inline buttons on alerts: ✅ Approve | ❌ Reject | 🔕 Ignore

## Scoring System

**Opportunity Score (0-100):**
- Base: 50
- Prize > $10K → +15 | $5K-10K → +10 | $1K-5K → +5
- Deadline 14-45 days → +10 | 7-13 days → +5
- AI policy allowed → +15 | unclear → -15
- Solo allowed → +5 | Global → +5
- Team-only → -10 | Corporate sponsor → -10

**Win Probability (0-100):**
- Base: 30
- Prize > $5K → +10 | Days remaining > 14 → +10
- AI policy allowed → +15 | Difficulty easy → +10 | hard → -10
- Corporate sponsor → -20 | Team-only → -10

## Database Schema

```sql
opportunities   -- Discovered hackathons/grants/competitions
project_files    -- Generated project plans per approved opportunity
scan_log         -- Scanner execution history
```

## License

MIT License — use freely for your submissions.