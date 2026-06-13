# Architecture — Challenge Hunter AI v2.0

## Mission

Replace the "I should check Devpost today" workflow with a 24/7 machine that:
1. finds every hackathon, grant, and bounty before you do,
2. ranks them by ROI,
3. pings you only when something's worth your time,
4. builds the project when you tap "approve",
5. submits it (or hands you a polished brief) before the deadline.

---

## The 5 layers

### Layer 1 — Discovery
- 30+ curated sources (Devpost, MLH, HuggingFace, Solana, Replit, Kaggle, GitHub, OpenAI, Anthropic, AWS, GCP, MS, Vercel, Gitcoin, Base, NEAR, YC, ProductHunt, more).
- 10 DuckDuckGo search queries designed to surface new opportunities.
- All requests wrapped in `try/except`, sleep 2s between calls, `time.sleep(REQUEST_DELAY_SECONDS)` is centralised in `config.py`.
- A scan creates a `scan_log` row with sources visited, new opportunities, errors, duration.

### Layer 2 — Intelligence
- **Scoring** (`scorer.py`): deterministic, 0–100, based on prize tier, deadline sweet spot, AI policy, eligibility, difficulty, team size.
- **AI analysis** (`analyzer.py`):
  - If `OPENAI_API_KEY` is set, calls OpenAI with a strict JSON schema.
  - Otherwise, deterministic template that produces a well-formed analysis.
  - Sleep 3s between calls (configurable).
- **Expected value** = `prize × win_probability / 100`.

### Layer 3 — Notification
- Multi-channel dispatch (`notifier.py`):
  1. **Telegram** — primary. Free, instant, on phone.
  2. **Discord webhook** — secondary. Free, instant, in your server.
  3. **ntfy.sh** — tertiary. Free push notifications to phone.
- Three schedules:
  - Immediate alert when score ≥ `MIN_SCORE_FOR_ALERT` (default 70).
  - Daily digest at 9 AM UTC.
  - Weekly summary on Monday.

### Layer 4 — Approval workflow
- Two entry points: web dashboard (POST `/api/opportunities/<id>/approve`) or Telegram (`/approve_<id>`).
- On approval:
  1. Status set to `approved`, `build_status = in_progress`.
  2. Telegram notified: "🔨 Build started".
  3. `auto_builder.run_build_async` spawns a background thread.

### Layer 5 — Autonomous build + submit
- `auto_builder.py` orchestrates 7 phases:
  1. **Setup** — log to `build_log`, notify Telegram.
  2. **Generate files** — `ProjectFileGenerator.generate_all` writes README, architecture, plan, demo script, source skeleton, Dockerfile, GitHub Action.
  3. **Create GitHub repo** — `POST /user/repos` with GITHUB_TOKEN. Best-effort.
  4. **Hermes brief** — `projects/hermes_session_<id>.txt` for an external Hermes session to finish manually.
  5. **Tests** — `pytest` in the project dir. Capped at 60s.
  6. **Security audit** — `bandit` on the project. Capped at 60s.
  7. **Mark complete** — `build_status = complete`, Telegram notified.
- Auto-submit is intentionally a stub. The platform doesn't allow unattended submissions reliably, so we generate a polished package and a Hermes brief instead.

---

## Data model

```
opportunities
├─ id, name, url, prize_usd, prize_text
├─ deadline, days_remaining
├─ rules_summary, ai_policy, eligibility, team_size, difficulty
├─ opportunity_score, win_probability, expected_value
├─ status (pending | approved | rejected | ignored | expired | building | submitted)
├─ analysis_json (full AI analysis)
├─ source, source_url, tags
├─ build_status (none | in_progress | complete | submitted | failed)
├─ github_repo_url, submission_url, submission_confirmed
└─ alert_sent, created_at, updated_at

project_files
├─ opportunity_id, filename, content, file_type, created_at

scan_log
├─ scan_time, sources_scanned, new_found, high_value_found, errors, duration_seconds

build_log
├─ opportunity_id, step, status, output, timestamp

notifications
├─ opportunity_id, type, message, sent_at, delivered
```

All in SQLite, single file at `DB_PATH`.

---

## Scheduler lifecycle

- `app.py` imports `scheduler.py`.
- `gunicorn_config.py` `post_fork` hook starts the scheduler in each Gunicorn worker.
- Jobs:
  - `full_scan` — every `SCAN_INTERVAL_HOURS` (default 4), also runs once at startup.
  - `daily_digest` — 9 AM UTC.
  - `weekly_summary` — Monday 10 AM UTC.
  - `health_ping` — every 14 min (keeps Render alive).

---

## Deployment matrix

| Platform | Role | Cost |
|---|---|---|
| Railway | Primary API + scheduler | Free (500h/month) |
| Render | Fallback API | Free (with UptimeRobot) |
| GitHub Actions | 24/7 scanner cron | Free (2000 min/month) |
| UptimeRobot | Keep Render alive | Free (50 monitors) |
| Telegram | Notifications | Free |
| Discord | Notifications | Free |
| ntfy.sh | Phone push | Free |

**Total: $0/month.**

---

## Extension points

- **New source**: add to `config.ALL_SOURCES` and (optionally) a parser in `scanner.PARSERS`.
- **New scoring factor**: extend `scorer.calculate_opportunity_score` and add a test.
- **New notification channel**: add to `notifier.py`, follow the `send_X` pattern.
- **New build phase**: add to `auto_builder._runner`, log to `build_log`.
- **New API endpoint**: add to `app.py`, follow the existing JSON patterns.

---

## Why this design?

- **No build step** on the frontend = one less thing to break.
- **Pure scoring functions** = trivial to unit-test and tweak.
- **Background threads** for builds/scans = non-blocking API.
- **DB created at module load** = zero-config deployment.
- **Multi-channel notifications** = at least one always reaches you.
- **24/7 GitHub Actions fallback** = nothing stops the scanner.
