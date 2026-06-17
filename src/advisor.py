#!/usr/bin/env python3
"""
Challenge Hunter AI v2.2 — Smart Recommendations
Uses the LLM to give personalized advice on:
  - Which opportunity to pursue first
  - How to maximize your win rate
  - Calendar/timeline planning
  - Skill/time estimation
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List

from config import DB_PATH
from llm import default_client


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def get_recommendations(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Get top opportunities to pursue, ranked by composite score:
      opportunity_score * 0.5 + win_probability * 0.3 + urgency * 0.2

    urgency = max(0, 30 - days_remaining) / 30  (closer deadline = higher urgency)
    """
    conn = _conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            id, name, prize_usd, days_remaining, opportunity_score, win_probability,
            expected_value, ai_policy, source, url
        FROM opportunities
        WHERE status = 'pending'
          AND ai_policy IN ('allowed', 'unclear')
          AND days_remaining > 0
        ORDER BY opportunity_score DESC
        LIMIT 50
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    # Score each
    for r in rows:
        days = r.get('days_remaining') or 30
        urgency = max(0, 30 - days) / 30
        r['composite_score'] = round(
            (r.get('opportunity_score') or 0) * 0.5
            + (r.get('win_probability') or 0) * 0.3
            + urgency * 100 * 0.2,
            1
        )
        r['priority'] = (
            'CRITICAL' if days <= 3 and r['opportunity_score'] >= 70
            else 'HIGH' if r['opportunity_score'] >= 70
            else 'MEDIUM'
        )
        r['days_remaining'] = days

    rows.sort(key=lambda r: r['composite_score'], reverse=True)
    return rows[:limit]


def get_calendar(days_ahead: int = 60) -> List[Dict[str, Any]]:
    """Get opportunities grouped by deadline, sorted chronologically."""
    conn = _conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, prize_usd, days_remaining, deadline, opportunity_score,
               ai_policy, status
        FROM opportunities
        WHERE status = 'pending'
          AND days_remaining <= ?
          AND days_remaining > 0
        ORDER BY days_remaining ASC
    """, (days_ahead,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    # Group by urgency
    buckets = {'this_week': [], 'next_week': [], 'this_month': [], 'later': []}
    for r in rows:
        d = r.get('days_remaining') or 0
        if d <= 7:
            buckets['this_week'].append(r)
        elif d <= 14:
            buckets['next_week'].append(r)
        elif d <= 30:
            buckets['this_month'].append(r)
        else:
            buckets['later'].append(r)
    return buckets


def get_ai_advisor() -> Dict[str, Any]:
    """
    Use the LLM to give personalized advice based on the current
    opportunity pool + (if available) past win/loss data.
    """
    recs = get_recommendations(10)
    if not recs:
        return {
            'success': True,
            'advice': 'No opportunities to advise on right now. Run a scan to discover more.',
            'top_pick': None,
        }

    # Get past win/loss data
    conn = _conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT result, COUNT(*) as n FROM submissions
        WHERE result IS NOT NULL GROUP BY result
    """)
    win_loss = {r['result']: r['n'] for r in cursor.fetchall()}
    cursor.execute("""
        SELECT COUNT(*) as n, COALESCE(SUM(o.prize_usd), 0) as total
        FROM submissions s JOIN opportunities o ON s.opportunity_id = o.id
        WHERE s.result = 'won'
    """)
    won = dict(cursor.fetchone() or {})
    conn.close()

    past_stats = ''
    if win_loss:
        past_stats = f"\nUser history: {win_loss.get('won', 0)} won, {win_loss.get('lost', 0)} lost, ${won.get('total', 0):,.0f} earned."

    opp_summary = '\n'.join(
        f"#{r['id']} {r['name'][:50]} | ${r['prize_usd']:,} | {r['days_remaining']}d | score {r['opportunity_score']} | win {r['win_probability']}%"
        for r in recs[:8]
    )

    system = """You are a personal hackathon coach. Given the user's pending
opportunities and history, give a 3-paragraph tactical recommendation:
  1. Which ONE to build first (and why in 1 sentence)
  2. Top 3 wins to maximize chances
  3. Calendar suggestion (what to build when)

Be specific, opinionated, no fluff. 200 words max."""

    user_prompt = f"""Top pending opportunities (ranked by composite score):
{opp_summary}
{past_stats}

Give your recommendation."""

    result = default_client.complete(
        messages=[{'role': 'system', 'content': system},
                  {'role': 'user', 'content': user_prompt}],
        temperature=0.4,
        max_tokens=400,
        timeout=60
    )
    if not result.get('success'):
        return {
            'success': True,
            'advice': f"Top pick: #{recs[0]['id']} {recs[0]['name']} (${recs[0]['prize_usd']:,}, {recs[0]['days_remaining']}d left). "
                       f"Build this first — highest score ({recs[0]['opportunity_score']}) and best EV (${recs[0]['expected_value']:,.0f}).",
            'top_pick': recs[0],
            'note': 'AI advisor unavailable, showing fallback recommendation',
        }
    return {
        'success': True,
        'advice': result['content'].strip(),
        'top_pick': recs[0],
    }


def get_daily_standup() -> Dict[str, Any]:
    """
    Morning brief: what's expiring soon, what's new, what to work on.
    """
    conn = _conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, prize_usd, days_remaining, opportunity_score
        FROM opportunities
        WHERE status = 'pending' AND days_remaining <= 7 AND days_remaining > 0
        ORDER BY days_remaining ASC
    """)
    urgent = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT id, name, prize_usd, opportunity_score, created_at
        FROM opportunities
        WHERE created_at > datetime('now', '-1 day')
        ORDER BY created_at DESC
        LIMIT 5
    """)
    new = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT COUNT(*) as n FROM opportunities WHERE status = 'pending'
    """)
    pending_total = cursor.fetchone()['n']

    cursor.execute("""
        SELECT COALESCE(SUM(expected_value), 0) as ev,
               COALESCE(SUM(prize_usd), 0) as pool
        FROM opportunities WHERE status = 'pending'
    """)
    totals = dict(cursor.fetchone() or {})
    conn.close()

    return {
        'urgent': urgent,
        'new_today': new,
        'pending_total': pending_total,
        'total_prize_pool': totals.get('pool', 0),
        'total_expected_value': totals.get('ev', 0),
        'date': datetime.now().isoformat(),
    }


def get_stats_summary() -> Dict[str, Any]:
    """Aggregate stats for the dashboard summary card."""
    conn = _conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            COUNT(*) as pending,
            COALESCE(SUM(prize_usd), 0) as pool,
            COALESCE(SUM(expected_value), 0) as ev,
            AVG(opportunity_score) as avg_score
        FROM opportunities WHERE status = 'pending'
    """)
    pending = dict(cursor.fetchone() or {})
    cursor.execute("SELECT COUNT(*) as n FROM opportunities WHERE build_status = 'complete'")
    completed = cursor.fetchone()['n']
    cursor.execute("SELECT COUNT(*) as n, COALESCE(SUM(prize_usd), 0) as won FROM opportunities o JOIN submissions s ON s.opportunity_id = o.id WHERE s.result = 'won'")
    won = dict(cursor.fetchone() or {})
    conn.close()
    return {
        'pending': pending,
        'completed': completed,
        'won': won,
        'win_rate': round(won['n'] / max(1, completed) * 100, 1),
    }


if __name__ == '__main__':
    print("Top 5 recommendations:")
    for r in get_recommendations(5):
        print(f"  #{r['id']} {r['name'][:50]} | composite={r['composite_score']} | {r['priority']}")
    print("\nDaily standup:")
    s = get_daily_standup()
    print(f"  Urgent: {len(s['urgent'])} opps < 7d")
    print(f"  New today: {len(s['new_today'])}")
    print(f"  Total pool: ${s['total_prize_pool']:,.0f}, EV: ${s['total_expected_value']:,.0f}")
