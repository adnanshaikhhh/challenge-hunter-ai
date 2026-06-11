#!/usr/bin/env bash
# ============================================================
# Challenge Hunter AI - Railway Deployment Script
# ============================================================
#
# Railway requires ONE-TIME interactive login:
#   1. Install Railway CLI: npm install -g @railway/cli
#   2. Run: railway login --browserless
#      - You will get a code to enter at https://railway.com/activate
#   3. After login, run this script
#
# ============================================================

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "============================================================"
echo "🚂 Challenge Hunter AI — Railway Deployment"
echo "============================================================"
echo ""

# Check if logged in
echo "Checking Railway authentication..."
if ! railway whoami >/dev/null 2>&1; then
    echo "❌ Not logged in to Railway!"
    echo ""
    echo "Run these commands first:"
    echo "  npm install -g @railway/cli"
    echo "  railway login --browserless"
    echo ""
    echo "Then re-run this script."
    exit 1
fi

echo "✅ Authenticated to Railway"
echo ""

# Initialize Railway project (non-interactive)
echo "📦 Creating Railway project..."
railway init --name challenge-hunter-ai 2>/dev/null || echo "  (Project may already exist, continuing...)"

# Link to existing project if already created
echo "🔗 Linking to project..."
cd "$PROJECT_DIR" || exit 1

# Set environment variables
echo "⚙️  Setting environment variables..."
railway variables set FLASK_ENV production 2>/dev/null || true
railway variables set SCAN_INTERVAL_HOURS 6 2>/dev/null || true
railway variables set MIN_SCORE_FOR_ALERT 70 2>/dev/null || true
railway variables set SECRET_KEY "$(openssl rand -hex 32 2>/dev/null || echo 'change-me-in-production')" 2>/dev/null || true

# Note about Telegram (user must set these manually or via dashboard)
echo ""
echo "⚠️  IMPORTANT — Set these in Railway dashboard (https://railway.app):"
echo "   - TELEGRAM_BOT_TOKEN  (from @BotFather on Telegram)"
echo "   - TELEGRAM_CHAT_ID    (your Telegram chat ID)"
echo ""

# Deploy
echo "🚀 Deploying to Railway..."
railway up --select --service challenge-hunter-ai 2>/dev/null || railway up 2>/dev/null || {
    echo "❌ Deployment failed. Try 'railway up' manually from this directory."
    exit 1
}

# Get domain
echo ""
sleep 3
DOMAIN=$(railway domain 2>/dev/null || echo "")
if [ -n "$DOMAIN" ]; then
    echo "============================================================"
    echo "✅ DEPLOYMENT SUCCESSFUL!"
    echo "============================================================"
    echo ""
    echo "🌐 Live URL: https://$DOMAIN"
    echo "❤️  Health:  https://$DOMAIN/health"
    echo ""
    echo "📋 Next steps:"
    echo "   1. Open Railway dashboard: https://railway.app"
    echo "   2. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID"
    echo "   3. Run: python src/seed.py  (seed the database)"
    echo "   4. Visit: https://$DOMAIN"
    echo ""
else
    echo "✅ Deployed! Run 'railway domain' to get your URL."
    echo "   Or visit: https://railway.app"
fi