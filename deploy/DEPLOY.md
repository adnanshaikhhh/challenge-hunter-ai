# ============================================================
# Challenge Hunter AI - Render Deployment Guide
# ============================================================
#
# OPTION A: One-Click Deploy via Render GitHub Integration
# ─────────────────────────────────────────────────────────────
# 1. Go to: https://render.com
# 2. Sign in with GitHub
# 3. Click "New +" → "Blueprint"
# 4. Connect your GitHub repo:
#    https://github.com/adnanshaikhhh/challenge-hunter-ai
# 5. Select the repo — render.yaml is auto-detected
# 6. Click "Apply"
#
# OPTION B: Manual Deploy via CLI
# ─────────────────────────────────────────────────────────────
# 1. Install Render CLI:
#    npm install -g @render/cicd
#
# 2. Login:
#    render login
#
# 3. Deploy:
#    render deploy
#    (from the project directory)
#
# ============================================================
#
# REQUIRED ENVIRONMENT VARIABLES (set in Render dashboard):
# ─────────────────────────────────────────────────────────────
# FLASK_ENV = production
# PYTHON_VERSION = 3.11.0
# TELEGRAM_BOT_TOKEN = your_telegram_bot_token
# TELEGRAM_CHAT_ID = your_telegram_chat_id
# SCAN_INTERVAL_HOURS = 6
# MIN_SCORE_FOR_ALERT = 70
# SECRET_KEY = your-random-secret-key
#
# ============================================================
#
# VERIFY AFTER DEPLOYMENT:
# ─────────────────────────────────────────────────────────────
# curl https://your-service.onrender.com/health
# Expected: {"status":"ok","service":"Challenge Hunter AI",...}
#
# ============================================================