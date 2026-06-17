#!/usr/bin/env python3
"""
Challenge Hunter AI v2.2 — Research Engine
Scrapes past winners, judge preferences, and winning patterns.
Uses unified LLM client (tokenrouter / NVIDIA NIM) for structured insight extraction.
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from config import DB_PATH, HTTP_HEADERS, REQUEST_DELAY_SECONDS
from llm import LLMClient, default_client


# =============================================================================
# Sources for research
# =============================================================================

PAST_WINNERS_SOURCES = [
    # Devpost — has "winners" / past hackathons pages
    ('devpost_winners', 'https://devpost.com/hackathons?status=ended&sort_by=winner_count'),
    ('devpost_winners', 'https://devpost.com/hackathons?status=ended&sort_by=prize_amount'),
    # MLH past seasons
    ('mlh_past', 'https://mlh.io/seasons'),
    # Hackathon.com winners
    ('hackathon_winners', 'https://hackathon.com/winners'),
    # ProductHunt — for non-hackathon prizes
    ('producthunt', 'https://www.producthunt.com/leaderboard'),
]


# =============================================================================
# Helpers
# =============================================================================

def _conn():
    import sqlite3
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def _save_research(data: Dict[str, Any]) -> bool:
    """Persist a research_data row. Returns True if newly inserted."""
    try:
        conn = _conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO research_data (
                source, source_url, title, category, prize_usd,
                winner_name, winner_url, project_description, tech_stack,
                key_features, judge_comments, win_factors
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('source', ''),
            data.get('source_url', ''),
            data.get('title', ''),
            data.get('category', ''),
            int(data.get('prize_usd') or 0),
            data.get('winner_name', ''),
            data.get('winner_url', ''),
            data.get('project_description', ''),
            json.dumps(data.get('tech_stack', [])),
            json.dumps(data.get('key_features', [])),
            data.get('judge_comments', ''),
            json.dumps(data.get('win_factors', [])),
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"⚠️  research save failed: {e}")
        return False


def _fetch(url: str, timeout: int = 20) -> Optional[str]:
    try:
        r = requests.get(url, headers=HTTP_HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  ⚠️  fetch {url}: {e}")
        return None


# =============================================================================
# AI analysis of research data
# =============================================================================

def _ai_extract_insights(text: str, source_name: str) -> List[Dict[str, Any]]:
    """
    Use the LLM to extract structured insights from raw web content.
    Returns a list of research_data records.
    """
    if not text:
        return []

    # Truncate to avoid huge prompts
    text = text[:12000]

    system_prompt = """You are a research analyst extracting structured data from hackathon
winner pages and prize listings. For each opportunity/winner you find, output a JSON object
with these fields:
{
  "title": "competition name",
  "category": "AI | Web3 | Hackathon | Grant | Startup | Other",
  "prize_usd": 10000,
  "winner_name": "winning project name",
  "winner_url": "https://...",
  "project_description": "1-2 sentence description",
  "tech_stack": ["Python", "React", ...],
  "key_features": ["feature 1", "feature 2"],
  "judge_comments": "any judge feedback quotes",
  "win_factors": ["what made this win", "1-2 items"]
}

Output a JSON ARRAY of these objects. If the page has no useful data, output [].
ONLY output valid JSON, no other text."""

    user_prompt = f"""Source: {source_name}

Page content (truncated to first 12000 chars):
{text}

Extract the structured data now as a JSON array."""

    result = default_client.complete(
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ],
        temperature=0.1,
        max_tokens=4000,
        timeout=120
    )
    if not result.get('success'):
        return []

    content = result['content']
    # Try to find JSON array
    json_match = re.search(r'\[.*\]', content, re.DOTALL)
    if not json_match:
        return []
    try:
        data = json.loads(json_match.group(0))
        if not isinstance(data, list):
            return []
        return data
    except Exception as e:
        print(f"  ⚠️  JSON parse failed: {e}")
        return []


# =============================================================================
# Main research runner
# =============================================================================

def run_research_scan(save_to_db: bool = True) -> Dict[str, Any]:
    """
    Crawl past-winner sources, extract insights via AI, save to research_data table.
    """
    start = time.time()
    found = 0
    errors: List[str] = []

    for source_name, url in PAST_WINNERS_SOURCES:
        print(f"🔍 Researching {source_name}: {url}")
        time.sleep(REQUEST_DELAY_SECONDS)
        html = _fetch(url)
        if not html:
            errors.append(f"fetch: {url}")
            continue
        insights = _ai_extract_insights(html, source_name)
        for insight in insights:
            insight['source'] = source_name
            insight['source_url'] = url
            if save_to_db and _save_research(insight):
                found += 1
        print(f"  → {len(insights)} insights extracted")

    return {
        'sources_scanned': len(PAST_WINNERS_SOURCES),
        'insights_saved': found,
        'errors': errors,
        'duration_seconds': round(time.time() - start, 2),
    }


# =============================================================================
# Win pattern mining
# =============================================================================

def mine_win_patterns() -> List[Dict[str, Any]]:
    """
    Analyze research_data + past submissions to find common patterns in winners.
    """
    conn = _conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT category, COUNT(*) as n,
               AVG(prize_usd) as avg_prize,
               key_features
        FROM research_data
        WHERE key_features IS NOT NULL AND key_features != '[]'
        GROUP BY category
        ORDER BY n DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    patterns = []
    for r in rows:
        # Aggregate all features across this category
        all_features = []
        for f_json in [r['key_features'] or '[]']:
            try:
                feats = json.loads(f_json)
                if isinstance(feats, list):
                    all_features.extend(feats)
            except Exception:
                pass

        # Most common features
        from collections import Counter
        common = Counter(all_features).most_common(3)

        patterns.append({
            'category': r['category'] or 'Unknown',
            'count': r['n'],
            'avg_prize': r['avg_prize'] or 0,
            'top_features': [f for f, _ in common],
        })

    return patterns


# =============================================================================
# Public API for app.py
# =============================================================================

def get_research_for_opportunity(opp: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get relevant research data for a specific opportunity.
    Returns matching past winners, common features, and judge tips.
    """
    conn = _conn()
    cursor = conn.cursor()
    # Match by category
    category = opp.get('ai_policy', 'unclear')
    cursor.execute("""
        SELECT * FROM research_data
        WHERE category = ? OR tech_stack LIKE ?
        ORDER BY prize_usd DESC
        LIMIT 5
    """, (category, f'%{opp.get("source", "")}%'))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    # Parse JSON fields
    for r in rows:
        for field in ('tech_stack', 'key_features', 'win_factors'):
            try:
                r[field] = json.loads(r.get(field) or '[]')
            except Exception:
                r[field] = []

    return {
        'past_winners': rows,
        'total_research': len(rows),
        'win_patterns': mine_win_patterns(),
    }


# =============================================================================
# CLI
# =============================================================================

if __name__ == '__main__':
    print("🔬 Running research scan...")
    result = run_research_scan()
    print(json.dumps(result, indent=2))

    print("\n📊 Win patterns by category:")
    for p in mine_win_patterns():
        print(f"  {p['category']:15s} | {p['count']} winners | avg ${p['avg_prize']:,.0f} | top: {p['top_features'][:2]}")
