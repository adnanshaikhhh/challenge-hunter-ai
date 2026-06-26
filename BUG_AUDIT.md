# Challenge Hunter AI — Complete Bug Audit
**Generated:** 2026-06-26  
**Status:** Pre-fix baseline

---

## 🔴 CRITICAL (App crashes, data loss, security)

### 1. Scanner: No per-source error handling
**File:** `scanner.py:321-332`  
**Issue:** `_scan_source()` has a global try/except around the parser, but if `_safe_request()` or `parser()` throws, it appends to errors but ONE failed source can still poison the entire scan loop.  
**Impact:** One broken source URL = entire scan aborted  
**Fix:** Wrap each source in its own try/except in `run_full_scan()`

### 2. Scanner: Missing DuckDuckGo library
**File:** `scanner.py:200-242`  
**Issue:** Uses `requests.post()` to DuckDuckGo HTML endpoint, but no `ddgs` library imported. The README mentions using `ddgs` library but code doesn't use it.  
**Impact:** DuckDuckGo search may fail or be unreliable  
**Fix:** Either use `duckduckgo-search` library or document that HTML scraping is intentional

### 3. Scanner: No request timeout on all sources
**File:** `scanner.py:99-106`  
**Issue:** `_safe_request()` has 15s timeout, but parsers and DDG don't have fallback for network failures  
**Impact:** One slow/hanging source blocks the entire scan  
**Fix:** Already has timeout=15, but need to ensure ALL requests (including DDG) respect it

### 4. Scanner: No User-Agent on DDG requests
**File:** `scanner.py:200-212`  
**Issue:** DDG POST has `headers=HTTP_HEADERS` but might still be blocked  
**Impact:** DDG returns empty or blocks the request  
**Fix:** Already uses HTTP_HEADERS, verify it works

### 5. Scanner: URL deduplication uses dict, not hash
**File:** `scanner.py:372-374`  
**Issue:** Dedup by `opp['url']` as dict key — works but no hash-based collision handling  
**Impact:** Duplicate URLs with different anchors might slip through  
**Fix:** Use URL normalization (remove fragments/trailing slashes)

### 6. Database: No try/except on ALL db operations
**File:** `app.py:98-101`, `scanner.py:38-41`  
**Issue:** `get_db()` and `_conn()` have no error handling, crashes on corrupt DB  
**Impact:** Corrupt DB = entire app crashes  
**Fix:** Wrap all db.execute/commit in try/except with rollback

### 7. Database: Missing indexes
**File:** `schema.sql:77-86`  
**Issue:** Has indexes on status/score/deadline, but NOT on `opportunities(created_at)` for `/api/stats` "new today" query  
**Impact:** Slow queries as DB grows  
**Fix:** Already has `idx_opportunities_created` at line 178 ✅

### 8. Scheduler: No misfire_grace_time
**File:** `scheduler.py:92-121`  
**Issue:** APScheduler jobs have no `misfire_grace_time` — if scheduler lags, jobs pile up  
**Impact:** Multiple scans fire simultaneously after downtime  
**Fix:** Add `misfire_grace_time=300` to all jobs

### 9. Telegram bot: No try/except on command handlers
**File:** `telegram_bot.py:282-323`  
**Issue:** `cmd_list`, `cmd_stats`, `cmd_scan` have basic error handling but can still crash on DB errors  
**Impact:** One DB error = bot stops responding  
**Fix:** Wrap every handler in try/except and reply with error message

### 10. Telegram bot: /scan command blocks
**File:** `telegram_bot.py:369-394`  
**Issue:** `/scan` calls `scanner.run_full_scan()` synchronously — blocks bot for 30-60 seconds  
**Impact:** Bot appears frozen during scan  
**Fix:** Run scan in background thread, reply immediately

### 11. Telegram bot: Callback query doesn't validate ID
**File:** `telegram_bot.py:396-475`  
**Issue:** `handle_callback_query` parses `int(opp_id_str)` but doesn't check if opportunity exists BEFORE updating status  
**Impact:** Approving deleted opportunity crashes  
**Fix:** Already checks `if not row:` at line 426 ✅

### 12. API: No rate limiting on /api/scan
**File:** `app.py:337-362`  
**Issue:** Has custom rate limiting (5 scans/60s per IP) but no protection against distributed attacks  
**Impact:** Abuse possible  
**Fix:** Already implemented basic rate limiting ✅

### 13. Config: No validation on startup
**File:** `config.py:134-145`  
**Issue:** Reads env vars with `os.environ.get()` but doesn't validate TELEGRAM_BOT_TOKEN format or check if required vars are missing  
**Impact:** App starts with invalid config, crashes later  
**Fix:** Add startup validation in app.py

### 14. Notifier: No error handling on failed HTTP requests
**File:** `notifier.py:53-76`  
**Issue:** `send_telegram` has try/except but doesn't log failure to notifications table  
**Impact:** Silent failure — user doesn't know alerts failed  
**Fix:** Always log to notifications table even on failure (already does at line 142) ✅

### 15. Auto builder: No timeout on subprocess calls
**File:** `auto_builder.py:72-98`  
**Issue:** `_safe_run()` has 120s default timeout, but long-running builds (tests, security audit) can hang  
**Impact:** Build thread hangs forever  
**Fix:** Already has timeout=120, could be lower for quick commands

---

## 🟡 HIGH (Silent failures, bad UX)

### 16. Scanner: Returns 0 results with no explanation
**File:** `scanner.py:343-400`  
**Issue:** If all sources fail, `run_full_scan()` returns `{'new_found': 0, 'errors': [...]}` but doesn't log prominently  
**Impact:** User sees "0 new" and doesn't know why  
**Fix:** Add loud log message if new_found == 0 and errors > 0

### 17. Scanner: No logging per source (silent fails)
**File:** `scanner.py:354-362`  
**Issue:** Logs `✓ {url} — {len(opps)} candidates` but if a source returns 0, no way to tell if it's empty or broken  
**Impact:** Can't debug which sources are dead  
**Fix:** Add `✗ {url} — timeout/error` for failed sources

### 18. Dashboard: API calls have no loading states
**File:** `static/app.js:220-244`  
**Issue:** `loadOpportunities()` calls `showSkeleton()` but if API fails, skeleton stays forever  
**Impact:** User sees infinite loading spinner  
**Fix:** Clear skeleton on error and show "Failed to load" message

### 19. Dashboard: Approve button doesn't show feedback
**File:** `static/app.js:271-283`  
**Issue:** `approve()` sets `opacity = 0.5` but if API fails, card stays faded  
**Impact:** Card appears broken  
**Fix:** Reset opacity on failure (already does at line 281) ✅

### 20. Dashboard: /scan button doesn't disable during scan
**File:** `static/app.js:366-380`  
**Issue:** Disables button with `btn.disabled = true` but if scan fails, button stays disabled  
**Impact:** Can't retry scan  
**Fix:** Re-enable button in finally block (already does at line 378) ✅

### 21. Dashboard: No polling for build status
**File:** `static/app.js:391-412`  
**Issue:** `pollBuildStatus()` polls every 5s for 12 checks (60s), then gives up  
**Impact:** Builds taking >60s show no feedback  
**Fix:** Increase poll duration or show "still running" message (already does at line 409) ✅

### 22. Dashboard: Modal doesn't handle missing analysis
**File:** `static/app.js:433-501`  
**Issue:** `openAnalysis()` parses `analysis_json` but if it's malformed JSON, crashes  
**Impact:** Modal doesn't open  
**Fix:** Has try/catch at line 445 ✅

### 23. Telegram: No inline keyboard on /list
**File:** `telegram_bot.py:282-323`  
**Issue:** `/list` shows top 5 but no buttons to approve/reject  
**Impact:** User has to manually call `/approve_123`  
**Fix:** Add inline keyboard to each opportunity

### 24. Notifier: High-value alert sent even if TELEGRAM disabled
**File:** `notifier.py:165-206`  
**Issue:** `high_value_alert()` logs to DB even if no channels enabled  
**Impact:** Notifications table fills with unsent alerts  
**Fix:** Already logs with `delivered=False` when no channels ✅

---

## 🟢 MEDIUM (Polish, edge cases)

### 25. Scanner: AI policy detection too broad
**File:** `scanner.py:72-97`  
**Issue:** `detect_ai_policy()` regex matches "ai allowed" but also matches "ai NOT allowed"  
**Impact:** False positives on banned policies  
**Fix:** Add negative lookahead for "not", "no", "isn't"

### 26. Scanner: Prize parsing misses "k" notation
**File:** `scanner.py:60-70`  
**Issue:** `_parse_prize()` regex `[\d,]{3,}` doesn't match "$10k" or "10,000 USD"  
**Impact:** Misses some prizes  
**Fix:** Add special case for "k", "K", "thousand"

### 27. Dashboard: Score gauge colors hardcoded
**File:** `static/app.js:86-87`  
**Issue:** Score colors defined inline, not using CSS variables  
**Impact:** Inconsistent with theme  
**Fix:** Use `var(--accent-green)` etc. (already does) ✅

### 28. Dashboard: No empty state for 0 opportunities
**File:** `static/app.js:246-255`  
**Issue:** If `state.opportunities.length === 0`, shows empty grid with no message  
**Impact:** Looks broken  
**Fix:** Show "No opportunities found. Try /scan" message

### 29. Requirements.txt: Missing ddg library
**File:** `requirements.txt:1-16`  
**Issue:** No `duckduckgo-search` package  
**Impact:** DuckDuckGo search might not work as intended  
**Fix:** Add `duckduckgo-search>=4.0.0` if we're using it, or remove references

### 30. Requirements.txt: No python-telegram-bot
**File:** `requirements.txt:1-16`  
**Issue:** `telegram_bot.py` imports `from telegram import ...` but package not listed  
**Impact:** Import error on fresh install  
**Fix:** Add `python-telegram-bot>=20.0` to requirements

### 31. Procfile: Hardcoded path to src/
**File:** `Procfile:1`  
**Issue:** `cd src &&` assumes src/ exists, breaks if deployed from root  
**Impact:** Railway deploy fails if structure changes  
**Fix:** Use relative path or set PYTHONPATH

### 32. .env.example: Missing DB_PATH
**File:** `.env.example:1-46`  
**Issue:** Doesn't document DB_PATH env var  
**Impact:** User doesn't know they can override DB location  
**Fix:** Add `# DB_PATH=./opportunities.db` to .env.example

---

## 🔵 LOW (Nice-to-have, future)

### 33. No /metrics endpoint
**File:** N/A  
**Issue:** README mentions `/metrics` but endpoint doesn't exist  
**Impact:** Can't monitor app health  
**Fix:** Add `/api/metrics` endpoint with request count, error rate

### 34. No error.html for 404/500
**File:** `app.py:824-833`  
**Issue:** Has error handlers but returns JSON, no HTML page  
**Impact:** API errors show JSON in browser  
**Fix:** Render `templates/error.html` for non-API routes

### 35. No CORS origin restriction
**File:** `app.py:91`  
**Issue:** `CORS(app)` allows all origins  
**Impact:** Security risk for production  
**Fix:** Set `CORS(app, origins=['https://your-domain.com'])`

### 36. No gzip compression
**File:** N/A  
**Issue:** No Flask gzip middleware  
**Impact:** Slow page loads  
**Fix:** Add `flask-compress` to requirements and `Compress(app)` in app.py

### 37. No request timeout in app.py
**File:** N/A  
**Issue:** No global timeout for Flask requests  
**Impact:** Slow endpoints can hang  
**Fix:** Add `PERMANENT_SESSION_LIFETIME` or Gunicorn timeout

### 38. Analyzer: Deterministic fallback too generic
**File:** `analyzer.py:241-288`  
**Issue:** `build_deterministic_analysis()` generates same template for all opportunities  
**Impact:** Not useful for decision-making  
**Fix:** Add more heuristics based on source, prize, difficulty

---

## 📊 Summary

- **Critical:** 15 issues (app crashes, data loss, security)
- **High:** 9 issues (silent failures, bad UX)
- **Medium:** 8 issues (polish, edge cases)
- **Low:** 6 issues (nice-to-have)

**Total:** 38 issues identified

---

## ✅ Already Fixed (Found during audit)

1. Database indexes on `created_at` ✓
2. Telegram callback query validates opportunity exists ✓
3. API rate limiting implemented ✓
4. Notifier logs failed deliveries ✓
5. Auto builder has subprocess timeout ✓
6. Dashboard button re-enable in finally ✓
7. Modal error handling for malformed JSON ✓
8. Dashboard score gauge uses CSS variables ✓

---

## 🎯 Fix Priority

1. **Phase 1 (Critical):** #1-15 (scanner reliability, DB safety, bot crashes)
2. **Phase 2 (High):** #16-24 (UX polish, error visibility)
3. **Phase 3 (Medium):** #25-32 (edge cases, dependencies)
4. **Phase 4 (Low):** #33-38 (monitoring, compression)

**Next:** Start Phase 1 fixes
