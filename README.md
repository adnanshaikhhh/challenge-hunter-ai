# ⚡ Challenge Hunter AI v2.0

> **Autonomous opportunity detection and execution platform.**
> Discovers hackathons, grants, and bounties 24/7. Scores them. Notifies you. Builds the winning project and submits it — all on autopilot.

![v2.0](https://img.shields.io/badge/version-2.0.0-6366f1) ![python](https://img.shields.io/badge/python-3.11+-3b82f6) ![license](https://img.shields.io/badge/license-MIT-10b981) ![status](https://img.shields.io/badge/status-running-f59e0b)

---

## ✨ What's new in v2.0

- **5 autonomous layers**: discovery → intelligence → notification → approval → build + submit
- **30+ discovery sources**: Devpost, MLH, HuggingFace, Solana, Replit, Kaggle, GitHub, OpenAI, Anthropic, AWS, GCP, Microsoft, Vercel, Gitcoin, Base, NEAR, YC, ProductHunt, **plus DuckDuckGo search**
- **24/7 scanning** without your laptop: Railway + Render + GitHub Actions + UptimeRobot (all free)
- **Telegram bot** with 18 commands (`/list`, `/scan`, `/approve_3`, `/analyze_5`, `/top5`, `/urgent`, etc.)
- **Multi-channel notifications**: Telegram (primary), Discord webhook, ntfy.sh phone push
- **Autonomous build agent** that creates GitHub repos, writes code, runs tests, audits security, deploys
- **Elite dark dashboard** with glassmorphism, animated gauges, full modals, analytics
- **AI analysis engine** with OpenAI support + deterministic fallback
- **Auto-submit** for known platforms + Hermes session briefs for manual finish

---

## 🚀 Quick start (local)

```bash
git clone https://github.com/YOUR_USERNAME/challenge-hunter-ai.git
cd challenge-hunter-ai/src
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp ../.env.example ../.env                          # fill in Telegram token
python seed.py                                      # initial data
python app.py                                       # http://localhost:5000
```

---

## ☁️ Deploy free to Railway (primary)

1. Push the repo to GitHub.
2. Go to [railway.app](https://railway.app), sign in with GitHub.
3. **New Project** → **Deploy from GitHub repo** → pick this repo.
4. Add environment variables: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, etc.
5. Railway auto-detects the `Procfile` and starts Gunicorn.
6. Once live, visit `https://your-app.up.railway.app/health` — you should see `{"status":"ok"}`.

Database and seed data initialise automatically on first request.

---

## 🌐 Deploy free to Render (fallback)

1. Sign in at [render.com](https://render.com) with GitHub.
2. **New** → **Blueprint** → pick this repo.
3. Render reads `render.yaml` and provisions the service.
4. **Important**: free Render spins down after 15 min of inactivity. Add [UptimeRobot](https://uptimerobot.com) and point it at `https://your-app.onrender.com/health` to keep it awake.

---

## 🤖 Enable 24/7 GitHub Actions scanner

This is the belt-and-braces backup: even if Railway is down, the scanner runs every 6 hours on GitHub's free infrastructure.

1. In your GitHub repo, go to **Settings** → **Secrets and variables** → **Actions**.
2. Add:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `NTFY_TOPIC` (optional)

The workflow at `.github/workflows/scanner.yml` runs every 6 hours, fetches opportunities, and notifies you.

---

## 🛎 UptimeRobot setup (keeps Render alive)

1. Create a free account at [uptimerobot.com](https://uptimerobot.com).
2. **Add New Monitor** → **HTTP(s)**.
3. URL: `https://your-app.onrender.com/health`
4. Interval: 5 minutes.
5. The monitor pings every 5 minutes, keeping Render's free tier awake.

---

## 📱 Telegram bot setup

1. Open Telegram, message [@BotFather](https://t.me/BotFather).
2. `/newbot` → follow prompts → copy the **token**.
3. Message [@userinfobot](https://t.me/userinfobot) to get your **chat ID**.
4. Set both as environment variables in Railway/Render/GitHub.
5. Send `/start` to your bot — it'll reply with the command list.

### Available commands

| Command | What it does |
|---|---|
| `/list` | Top 10 pending by score |
| `/approved` | List approved |
| `/building` | List currently building |
| `/submitted` | List submitted entries |
| `/stats` | Full dashboard stats |
| `/scan` | Trigger manual scan |
| `/digest` | Send daily digest now |
| `/approve_<id>` | Approve + start auto build |
| `/reject_<id>` | Reject |
| `/ignore_<id>` | Ignore |
| `/analyze_<id>` | Send full analysis |
| `/submit_<id>` | Manually trigger submit |
| `/build_status` | All active builds |
| `/top5` | Top 5 by expected value |
| `/urgent` | < 7 days remaining |
| `/new` | Added in last 24 h |

---

## 🧠 How it works

```
┌──────────────────────────────────────────────────────────────────┐
│                       Challenge Hunter v2.0                      │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Layer 1 ─ DISCOVERY       30+ sources + DuckDuckGo queries      │
│     ↓                                                            │
│  Layer 2 ─ INTELLIGENCE    Score • Analyse • Prioritise          │
│     ↓                                                            │
│  Layer 3 ─ NOTIFICATION    Telegram + Discord + ntfy             │
│     ↓                                                            │
│  Layer 4 ─ APPROVAL        /approve_3  OR  click on dashboard    │
│     ↓                                                            │
│  Layer 5 ─ BUILD + SUBMIT  GitHub repo • code • tests • deploy   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the deep dive.

---

## 🧪 Run the test suite

```bash
cd src
python run_tests.py
```

You should see `XX tests passed, 0 failed` before deploying.

---

## 🛠 Stack

- **Backend:** Python 3.11, Flask, APScheduler, SQLite
- **Frontend:** Vanilla JS + Inter + JetBrains Mono, no build step
- **Scraper:** requests + BeautifulSoup + lxml
- **Notifications:** Telegram Bot API, Discord webhooks, ntfy.sh
- **Hosting:** Railway (primary), Render (fallback), GitHub Actions (cron)

All free. No paid services.

---

## 📂 Project structure

```
challenge-hunter-ai/
├── src/
│   ├── app.py             ← Flask backend
│   ├── scanner.py         ← Discovery engine
│   ├── analyzer.py        ← AI analysis (OpenAI + fallback)
│   ├── scorer.py          ← Pure scoring functions
│   ├── notifier.py        ← Telegram + Discord + ntfy
│   ├── generator.py       ← Project file generator
│   ├── auto_builder.py    ← Autonomous build agent
│   ├── scheduler.py       ← APScheduler wrapper
│   ├── config.py          ← All settings
│   ├── schema.sql         ← DB schema
│   ├── seed.py            ← Initial seed data
│   ├── run_tests.py       ← Test suite
│   ├── gunicorn_config.py ← Gunicorn hooks
│   ├── templates/
│   │   └── index.html     ← Dashboard HTML
│   └── static/
│       ├── style.css      ← Elite dark UI
│       └── app.js         ← Frontend logic
├── projects/              ← Auto-generated project folders
├── .github/workflows/
│   ├── scanner.yml        ← 24/7 free scanner
│   └── tests.yml          ← Run tests on push
├── Procfile
├── runtime.txt
├── render.yaml
├── .env.example
├── README.md
├── ARCHITECTURE.md
└── LICENSE
```

---

## 🔒 Security

- No secrets in code — all via env vars.
- No PII logged.
- Rate-limited outbound HTTP.
- Optional `bandit` security scan in CI.
- SQLite by default — switch to Postgres for multi-tenant.

---

## 📄 License

MIT
