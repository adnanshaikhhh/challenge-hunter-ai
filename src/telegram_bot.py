#!/usr/bin/env python3
"""
Challenge Hunter AI - Telegram Bot Handler
Handles Telegram notifications and commands for high-value opportunities.
"""

import os
import json
import logging
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# =============================================================================
# CONFIGURATION
# =============================================================================

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Database path
DB_PATH = os.environ.get('DB_PATH', os.path.join(os.path.dirname(__file__), 'opportunities.db'))

# =============================================================================
# DATABASE HELPERS
# =============================================================================

def get_db_connection():
    """Get database connection"""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row):
    """Convert sqlite3.Row to dictionary"""
    if row is None:
        return None
    return dict(row)


# =============================================================================
# TELEGRAM BOT HANDLER CLASS
# =============================================================================

class TelegramBotHandler:
    """Handles Telegram bot operations for Challenge Hunter AI"""

    def __init__(self, token=None, chat_id=None):
        self.bot_token = token or TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or TELEGRAM_CHAT_ID
        self.enabled = bool(self.bot_token and self.chat_id)

        if not self.enabled:
            logger.warning("Telegram bot not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
        else:
            logger.info("Telegram bot initialized")

    def build_opportunity_message(self, opp):
        """Build formatted message for an opportunity"""
        name = opp.get('name', 'Unknown')
        prize = opp.get('prize_usd', 0)
        deadline = opp.get('deadline', 'TBD')
        days = opp.get('days_remaining', '?')
        ai_policy = opp.get('ai_policy', 'unclear')
        score = opp.get('opportunity_score', 0)
        win_prob = opp.get('win_probability', 0)
        source = opp.get('source', 'Unknown')
        url = opp.get('url', '')

        # Get recommended project from analysis
        analysis = opp.get('analysis_json', {})
        if isinstance(analysis, str):
            try:
                import json
                analysis = json.loads(analysis)
            except Exception:
                analysis = {}

        recommended_project = analysis.get('recommended_project', {})
        project_name = recommended_project.get('name', 'See details')
        project_concept = recommended_project.get('concept', '')

        # AI policy emoji
        ai_emoji = {
            'allowed': '✅',
            'banned': '🚫',
            'unclear': '⚠️'
        }.get(ai_policy, '⚠️')

        message = f"""━━━━━━━━━━━━━━━━━━━━━━
🎯 NEW HIGH VALUE OPPORTUNITY
━━━━━━━━━━━━━━━━━━━━━━
📛 {name}
💰 Prize: ${prize:,}
📅 Deadline: {deadline} ({days} days left)
🤖 AI Policy: {ai_emoji} {ai_policy.upper()}
⭐ Score: {score}/100
🏆 Win Probability: {win_prob}%
📍 Source: {source}

💡 Recommended Build:
{project_name}
{project_concept}

🔗 {url}
━━━━━━━━━━━━━━━━━━━━━━"""

        return message

    def build_inline_keyboard(self, opportunity_id):
        """Build inline keyboard with approve/reject/ignore buttons"""
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_{opportunity_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_{opportunity_id}"),
            ],
            [
                InlineKeyboardButton("🔕 Ignore", callback_data=f"ignore_{opportunity_id}"),
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def send_high_value_alert(self, opp):
        """Send high value opportunity alert to Telegram"""
        if not self.enabled:
            logger.warning("Telegram not enabled, skipping alert")
            return False

        try:
            from telegram import Bot
            bot = Bot(token=self.bot_token)

            message = self.build_opportunity_message(opp)
            keyboard = self.build_inline_keyboard(opp.get('id', 0))

            await bot.send_message(
                chat_id=self.chat_id,
                text=message,
                reply_markup=keyboard,
                parse_mode='HTML'
            )

            logger.info(f"Sent high value alert for opportunity {opp.get('id')}")
            return True

        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    def send_high_value_alert_sync(self, opp):
        """Synchronous wrapper for send_high_value_alert"""
        if not self.enabled:
            return False

        try:
            from telegram import Bot
            import asyncio

            bot = Bot(token=self.bot_token)

            # Create new event loop for sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                message = self.build_opportunity_message(opp)
                keyboard = self.build_inline_keyboard(opp.get('id', 0))

                loop.run_until_complete(
                    bot.send_message(
                        chat_id=self.chat_id,
                        text=message,
                        reply_markup=keyboard,
                        parse_mode='HTML'
                    )
                )
                return True
            finally:
                loop.close()

        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    def send_approval_notification(self, opp):
        """Send notification when opportunity is approved"""
        if not self.enabled:
            return False

        try:
            from telegram import Bot
            import asyncio

            bot = Bot(token=self.bot_token)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                name = opp.get('name', 'Unknown')
                prize = opp.get('prize_usd', 0)

                message = f"""✅ ✅ ✅ APPROVED ✅ ✅ ✅

📛 {name}
💰 Prize: ${prize:,}

📄 Project files generated and ready!
Check the dashboard to download your project plan.

Good luck with your build! 🚀"""

                loop.run_until_complete(
                    bot.send_message(
                        chat_id=self.chat_id,
                        text=message,
                        parse_mode='HTML'
                    )
                )
                return True
            finally:
                loop.close()

        except Exception as e:
            logger.error(f"Failed to send approval notification: {e}")
            return False


# =============================================================================
# TELEGRAM COMMANDS HANDLER
# =============================================================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    message = """🎯 Welcome to Challenge Hunter AI!

I'll help you discover and track AI-friendly hackathons, grants, and competitions.

Commands:
/list - Show top 5 opportunities by score
/stats - Show dashboard statistics
/scan - Trigger a manual scan now
/help - Show all commands

I also send alerts when high-value opportunities are found! 🔔"""

    await update.message.reply_text(message, parse_mode='HTML')


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    message = """🎯 Challenge Hunter AI - Help

Available Commands:
/start - Start the bot
/list - Show top 5 opportunities by score
/stats - Show dashboard statistics
/scan - Trigger a manual scan
/help - Show this help message

Actions:
Click ✅ Approve on any opportunity to generate project files
Click ❌ Reject to remove from your list
Click 🔕 Ignore to hide it

Alerts:
When I find opportunities with score >= 70, I'll send you an alert with details!
"""

    await update.message.reply_text(message, parse_mode='HTML')


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /list command - show top 5 opportunities"""
    import sqlite3

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM opportunities
            WHERE status = 'pending'
            ORDER BY opportunity_score DESC
            LIMIT 5
        """)

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            await update.message.reply_text("No opportunities found. Try /scan to discover new ones!")
            return

        response = "🏆 Top 5 Opportunities:\n\n"

        for i, row in enumerate(rows, 1):
            opp = dict(row)
            name = opp['name'][:50] + '...' if len(opp['name']) > 50 else opp['name']
            prize = opp['prize_usd']
            score = opp['opportunity_score']
            days = opp['days_remaining'] or '?'

            response += f"{i}. {name}\n"
            response += f"   💰 ${prize:,} | ⭐ {score}/100 | ⏰ {days} days\n"
            response += f"   🔗 {opp['url']}\n\n"

        await update.message.reply_text(response, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Error in /list command: {e}")
        await update.message.reply_text("Error fetching opportunities. Please try again.")


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command - show dashboard statistics"""
    import sqlite3

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get stats
        cursor.execute("""
            SELECT
                COUNT(*) as total_active,
                SUM(CASE WHEN opportunity_score >= 70 THEN 1 ELSE 0 END) as high_priority,
                AVG(win_probability) as avg_win_prob,
                SUM(prize_usd) as total_prize
            FROM opportunities
            WHERE status NOT IN ('rejected', 'ignored', 'expired')
        """)

        row = cursor.fetchone()
        conn.close()

        total = row['total_active'] or 0
        high = row['high_priority'] or 0
        avg_win = round(row['avg_win_prob'] or 0, 1)
        total_prize = row['total_prize'] or 0

        message = f"""📊 Challenge Hunter AI - Statistics

🎯 Total Active: {total}
🔥 High Priority (⭐70+): {high}
🏆 Average Win Probability: {avg_win}%
💰 Total Prize Pool: ${total_prize:,}

Scan regularly to keep these numbers up!"""

        await update.message.reply_text(message, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Error in /stats command: {e}")
        await update.message.reply_text("Error fetching statistics. Please try again.")


async def cmd_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /scan command - trigger manual scan"""
    await update.message.reply_text("🔍 Starting scan... This will take a few minutes.")

    try:
        from scanner import ScannerEngine
        scanner = ScannerEngine(DB_PATH)
        result = scanner.run_full_scan()

        new_found = result.get('new_found', 0)
        errors = result.get('errors', [])

        response = f"""✅ Scan Complete!

📡 Sources scanned: {result.get('sources_scanned', 0)}
🆕 New opportunities found: {new_found}"""

        if errors:
            response += f"\n⚠️ Errors: {len(errors)}"

        await update.message.reply_text(response, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Scan error: {e}")
        await update.message.reply_text(f"❌ Scan failed: {str(e)}")


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks (approve/reject/ignore)"""
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data:
        return

    parts = data.split('_', 1)
    if len(parts) != 2:
        return

    action, opp_id_str = parts

    try:
        opp_id = int(opp_id_str)
    except ValueError:
        await query.edit_message_text("❌ Invalid opportunity ID")
        return

    import sqlite3

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get opportunity
        cursor.execute("SELECT * FROM opportunities WHERE id = ?", (opp_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            await query.edit_message_text("❌ Opportunity not found")
            return

        opp = dict(row) if row else {}

        # Process action
        if action == 'approve':
            cursor.execute("""
                UPDATE opportunities SET status = 'approved', updated_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), opp_id))
            conn.commit()
            conn.close()

            # Generate project files
            from generator import ProjectFileGenerator
            generator = ProjectFileGenerator(DB_PATH)
            files = generator.generate_all(opp_id, opp)

            await query.edit_message_text(
                f"✅ APPROVED!\n\n📄 {files} project files generated!\n\nCheck the dashboard to view your project plan.",
                parse_mode='HTML'
            )

        elif action == 'reject':
            cursor.execute("""
                UPDATE opportunities SET status = 'rejected', updated_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), opp_id))
            conn.commit()
            conn.close()

            await query.edit_message_text("❌ Opportunity rejected")

        elif action == 'ignore':
            cursor.execute("""
                UPDATE opportunities SET status = 'ignored', updated_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), opp_id))
            conn.commit()
            conn.close()

            await query.edit_message_text("🔕 Opportunity ignored")

    except Exception as e:
        logger.error(f"Callback error: {e}")
        await query.edit_message_text(f"❌ Error: {str(e)}")


# =============================================================================
# MAIN - START POLLING
# =============================================================================

def start_polling():
    """Start the Telegram bot with polling"""
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set. Bot will not start.")
        print("   Add TELEGRAM_BOT_TOKEN to your .env file.")
        return

    print("📱 Starting Telegram bot polling...")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("list", cmd_list))
    application.add_handler(CommandHandler("stats", cmd_stats))
    application.add_handler(CommandHandler("scan", cmd_scan))
    application.add_handler(CallbackQueryHandler(handle_callback_query))

    print("📱 Telegram bot is polling for commands...")
    print("   Send /start to your bot on Telegram to begin!")

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    start_polling()