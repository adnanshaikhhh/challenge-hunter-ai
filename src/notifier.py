#!/usr/bin/env python3
"""
Challenge Hunter AI v2.0 — Notification System
Telegram (primary), Discord (secondary), ntfy.sh (tertiary).
All delivery uses free services.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from config import (
    DB_PATH, DISCORD_WEBHOOK_URL, NTFY_TOPIC, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
)


# ----------------------------------------------------------------------------
# Database helpers
# ----------------------------------------------------------------------------

def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def _log_notification(opportunity_id: Optional[int], ntype: str, message: str, delivered: bool) -> None:
    try:
        conn = _conn()
        conn.execute("""
            INSERT INTO notifications (opportunity_id, type, message, delivered, sent_at)
            VALUES (?, ?, ?, ?, ?)
        """, (opportunity_id, ntype, message, 1 if delivered else 0, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️  notification log failed: {e}")


# ----------------------------------------------------------------------------
# Telegram
# ----------------------------------------------------------------------------

def _telegram_enabled() -> bool:
    return bool(TELEGRAM_BOT_TOKEN) and bool(TELEGRAM_CHAT_ID)


def send_telegram(text: str, parse_mode: str = 'HTML') -> bool:
    if not _telegram_enabled():
        print(f"📱 [Telegram disabled] {text[:80]}...")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(
            url,
            json={
                'chat_id': TELEGRAM_CHAT_ID,
                'text': text,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True,
            },
            timeout=15
        )
        if r.status_code == 200:
            return True
        print(f"⚠️  Telegram send failed: {r.status_code} {r.text[:200]}")
        return False
    except Exception as e:
        print(f"⚠️  Telegram exception: {e}")
        return False


# ----------------------------------------------------------------------------
# Discord
# ----------------------------------------------------------------------------

def _discord_enabled() -> bool:
    return bool(DISCORD_WEBHOOK_URL)


def send_discord(text: str) -> bool:
    if not _discord_enabled():
        return False
    try:
        r = requests.post(
            DISCORD_WEBHOOK_URL,
            json={'content': text[:1900]},
            timeout=15
        )
        return r.status_code in (200, 204)
    except Exception as e:
        print(f"⚠️  Discord send failed: {e}")
        return False


# ----------------------------------------------------------------------------
# ntfy.sh
# ----------------------------------------------------------------------------

def _ntfy_enabled() -> bool:
    return bool(NTFY_TOPIC)


def send_ntfy(title: str, body: str) -> bool:
    if not _ntfy_enabled():
        return False
    try:
        r = requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=body.encode('utf-8'),
            headers={'Title': title, 'Priority': 'default'},
            timeout=15
        )
        return r.status_code == 200
    except Exception as e:
        print(f"⚠️  ntfy send failed: {e}")
        return False


# ----------------------------------------------------------------------------
# Multi-channel dispatcher
# ----------------------------------------------------------------------------

def broadcast(text: str, title: Optional[str] = None) -> bool:
    """Send to all enabled channels. Returns True if at least one delivered."""
    delivered = False
    if _telegram_enabled():
        delivered = send_telegram(text) or delivered
    if _discord_enabled():
        delivered = send_discord(text) or delivered
    if _ntfy_enabled():
        delivered = send_ntfy(title or 'Challenge Hunter', text) or delivered
    if not (_telegram_enabled() or _discord_enabled() or _ntfy_enabled()):
        # Still log to the notifications table even without a channel,
        # so users can see recent activity in the UI.
        _log_notification(None, 'broadcast', text, delivered=False)
    return delivered


# ----------------------------------------------------------------------------
# High-level notification builders
# ----------------------------------------------------------------------------

def _fmt_prize(n: int) -> str:
    return f"${n:,}" if n else "TBD"


def _fmt_score(s: int) -> str:
    return f"{s}/100"


def _fmt_days(d: int) -> str:
    if d <= 0:
        return "EXPIRED"
    if d == 1:
        return "1 day"
    return f"{d} days"


def high_value_alert(opp: Dict[str, Any]) -> bool:
    """
    Sent immediately when an opportunity scores >= MIN_SCORE_FOR_ALERT.
    """
    analysis = {}
    try:
        analysis = json.loads(opp.get('analysis_json') or '{}')
    except Exception:
        pass
    rec = analysis.get('recommended_project', {})
    tech = ', '.join(rec.get('tech_stack', {}).get('backend', []) + rec.get('tech_stack', {}).get('frontend', [])) or 'TBD'

    text = (
        "🎯 <b>HIGH VALUE OPPORTUNITY DETECTED</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📛 <b>{opp.get('name', 'Unknown')}</b>\n"
        f"💰 Prize: <b>{_fmt_prize(int(opp.get('prize_usd') or 0))}</b>\n"
        f"📅 {_fmt_days(int(opp.get('days_remaining') or 0))} remaining\n"
        f"🤖 AI Policy: {opp.get('ai_policy', 'unclear')}\n"
        f"⭐ Score: <b>{_fmt_score(int(opp.get('opportunity_score') or 0))}</b>\n"
        f"🏆 Win Prob: {opp.get('win_probability', 0)}%\n"
        f"💵 EV: ${opp.get('expected_value', 0):,.0f}\n"
        f"📍 Source: {opp.get('source', 'unknown')}\n"
        "\n"
        "💡 <b>RECOMMENDED BUILD:</b>\n"
        f"🚀 {rec.get('name', 'AI-powered tool')}\n"
        f"{rec.get('concept', '')}\n"
        "\n"
        f"🛠 Stack: {tech}\n"
        f"⏱ Build time: {rec.get('estimated_build_days', '?')} days\n"
        "\n"
        f"🔗 {opp.get('url', '')}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ /approve_{opp.get('id')}\n"
        f"❌ /reject_{opp.get('id')}\n"
        f"🔕 /ignore_{opp.get('id')}\n"
        f"📊 /analyze_{opp.get('id')}"
    )
    ok = broadcast(text, title=f"🎯 {opp.get('name', 'Opportunity')}")
    _log_notification(opp.get('id'), 'alert', text, ok)
    return ok


def daily_digest() -> bool:
    conn = _conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) AS n FROM opportunities
        WHERE status NOT IN ('rejected','ignored','expired')
    """)
    total = cursor.fetchone()['n']
    cursor.execute("""
        SELECT COUNT(*) AS n FROM opportunities
        WHERE opportunity_score >= 70 AND status NOT IN ('rejected','ignored','expired')
    """)
    high = cursor.fetchone()['n']
    cursor.execute("SELECT COUNT(*) AS n FROM opportunities WHERE status = 'approved'")
    approved = cursor.fetchone()['n']
    cursor.execute("SELECT COALESCE(SUM(prize_usd),0) AS s FROM opportunities WHERE status NOT IN ('rejected','ignored','expired')")
    pool = cursor.fetchone()['s']
    cursor.execute("""
        SELECT * FROM opportunities
        WHERE status NOT IN ('rejected','ignored','expired')
        ORDER BY opportunity_score DESC LIMIT 3
    """)
    top = cursor.fetchall()
    cursor.execute("""
        SELECT COUNT(*) AS n FROM opportunities
        WHERE date(created_at) = date('now')
    """)
    new_today = cursor.fetchone()['n']
    conn.close()

    lines = [
        "🌅 <b>CHALLENGE HUNTER — DAILY DIGEST</b>",
        f"📊 Active: {total} | High Priority: {high} | Approved: {approved}",
        f"💰 Total Prize Pool: ${pool:,}",
        "",
        "<b>TOP 3 TODAY:</b>"
    ]
    for i, o in enumerate(top, 1):
        lines.append(
            f"{i}. {o['name']} — ${o['prize_usd']:,} — "
            f"{o['days_remaining']}d — Score: {o['opportunity_score']}"
        )
    lines.append("")
    lines.append(f"New today: {new_today} opportunities found")
    lines.append("/list to see all pending")
    text = "\n".join(lines)
    ok = broadcast(text, title='Daily Digest')
    _log_notification(None, 'digest', text, ok)
    return ok


def build_started(opp: Dict[str, Any]) -> bool:
    text = (
        "🔨 <b>BUILD STARTED</b>\n"
        f"📛 {opp.get('name')}\n"
        f"🚀 Project: {opp.get('project_name', 'TBD')}\n"
        f"⏱ Est. completion: {opp.get('build_days', '?')} days\n"
        f"📁 Repo: {opp.get('github_repo_url', 'pending')}\n"
        "I'll update you at each milestone."
    )
    ok = broadcast(text, title='🔨 Build started')
    _log_notification(opp.get('id'), 'build_complete', text, ok)
    return ok


def build_complete(opp: Dict[str, Any]) -> bool:
    text = (
        "✅ <b>BUILD COMPLETE</b>\n"
        f"📛 {opp.get('name')}\n"
        f"🚀 {opp.get('project_name', 'TBD')}\n"
        f"📁 GitHub: {opp.get('github_repo_url', 'pending')}\n"
        f"🌐 Demo: {opp.get('demo_url', 'pending')}\n"
        "📋 Submission: Ready\n"
        f"🏆 Submit now? /submit_{opp.get('id')}"
    )
    ok = broadcast(text, title='✅ Build complete')
    _log_notification(opp.get('id'), 'build_complete', text, ok)
    return ok


def submitted(opp: Dict[str, Any]) -> bool:
    text = (
        "🎉 <b>SUBMITTED!</b>\n"
        f"📛 {opp.get('name')}\n"
        "✅ Submission confirmed\n"
        f"📅 Deadline was: {opp.get('deadline', 'TBD')}\n"
        f"🏆 Win probability: {opp.get('win_probability', 0)}%\n"
        "Good luck! Results expected soon."
    )
    ok = broadcast(text, title='🎉 Submitted')
    _log_notification(opp.get('id'), 'submitted', text, ok)
    return ok


def error(message: str) -> bool:
    text = f"⚠️ <b>ERROR</b>\n{message}"
    ok = broadcast(text, title='⚠️ Error')
    _log_notification(None, 'error', text, ok)
    return ok


def info(message: str) -> bool:
    text = f"ℹ️ {message}"
    ok = broadcast(text, title='Info')
    _log_notification(None, 'info', text, ok)
    return ok


if __name__ == '__main__':
    print(f"Telegram enabled: {_telegram_enabled()}")
    print(f"Discord enabled:  {_discord_enabled()}")
    print(f"ntfy enabled:     {_ntfy_enabled()}")
    if _telegram_enabled():
        info("✅ Notifier self-test from Challenge Hunter v2.0")
