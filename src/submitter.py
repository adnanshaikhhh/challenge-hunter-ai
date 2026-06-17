#!/usr/bin/env python3
"""
Challenge Hunter AI v2.1 — Submission Automation
Fills out Devpost/MLH submission forms automatically.
Uses Devpost's public API where possible, falls back to form templates.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from config import DB_PATH, PROJECTS_DIR


# =============================================================================
# Devpost submission
# =============================================================================

def submit_to_devpost(opportunity_id: int) -> Dict[str, Any]:
    """
    Prepare a Devpost submission.
    Devpost doesn't have a public submit API, so we generate the full
    submission package and instructions.

    For a real headless submission, you'd use Playwright + the user's
    session cookies. We provide that as a "next-step" via a Playwright script.
    """
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM opportunities WHERE id = ?", (opportunity_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return {'success': False, 'error': 'opportunity_not_found'}
    opp = dict(row)
    conn.close()

    try:
        analysis = json.loads(opp.get('analysis_json') or '{}')
    except Exception:
        analysis = {}
    project = (analysis.get('recommended_project') or {})

    # Build the submission package
    package = {
        'project_name': project.get('name', opp.get('name')),
        'tagline': project.get('tagline', '')[:80],
        'project_description': _build_description(opp, project),
        'tech_stack': list({t for cat in project.get('tech_stack', {}).values() for t in (cat if isinstance(cat, list) else [])}),
        'video_url': '',  # user fills in
        'github_url': opp.get('github_repo_url', ''),
        'demo_url': '',    # user fills in (from deployer)
        'built_with_ai_tools': 'yes' if opp.get('ai_policy') == 'allowed' else 'unsure',
        'tags': _suggest_tags(opp, project),
        'submission_questions': {
            'what_inspired_you': analysis.get('why_this_is_good', ''),
            'what_you_learned': 'Building with AI tools accelerated the process 10x. The key was treating AI as a collaborator, not a replacement for design thinking.',
            'future_plans': project.get('wow_factor', '') + ' We plan to expand with more integrations and a public API.',
        }
    }

    # Save submission record
    _save_submission(opportunity_id, 'devpost', package, status='pending')

    return {
        'success': True,
        'platform': 'devpost',
        'package': package,
        'next_steps': [
            f"1. Open {opp.get('url', 'the Devpost hackathon page')}",
            "2. Click 'Submit Project' on that hackathon",
            "3. Copy each field from the package above",
            f"4. Project name: {package['project_name']}",
            f"5. Tagline: {package['tagline']}",
            f"6. Description: (see package, {len(package['project_description'])} chars)",
            f"7. Video URL: paste your demo video URL from /videos",
            f"8. GitHub URL: {package['github_url'] or '(paste from Build Now result)'}",
            "9. Tags: " + ', '.join(package['tags']),
            "10. Built with AI: " + package['built_with_ai_tools'],
        ],
        'note': 'Devpost has no public submit API. Use the fields above to fill the form manually — takes ~5 minutes.',
    }


def _build_description(opp: Dict[str, Any], project: Dict[str, Any]) -> str:
    """Build a polished Devpost project description."""
    parts = []
    parts.append(f"## {project.get('tagline', '')}\n")
    parts.append(f"### The Problem\n\n{project.get('problem_solved', 'A real workflow gap.')}\n")
    parts.append(f"### Our Solution\n\n{project.get('concept', 'A pragmatic AI-powered tool.')}\n")
    parts.append("### Key Features\n")
    for f in project.get('key_features', []):
        parts.append(f"- {f}")
    parts.append("")
    parts.append("### How We Built It\n\n")
    tech = project.get('tech_stack', {})
    for cat, items in tech.items():
        if items:
            parts.append(f"- **{cat.capitalize()}:** {', '.join(items)}")
    parts.append("")
    parts.append("### What's Next\n\n" + (project.get('wow_factor', '') + " This is just v1."))
    parts.append("")
    parts.append(f"Built in {project.get('estimated_build_days', 7)} days using AI-assisted development.")
    return "\n".join(parts)


def _suggest_tags(opp: Dict[str, Any], project: Dict[str, Any]) -> List[str]:
    """Suggest 3-5 tags for the submission."""
    tags = []
    # From tech stack
    for items in project.get('tech_stack', {}).values():
        if isinstance(items, list):
            tags.extend(items[:2])
    # From source
    source = (opp.get('source') or '').lower()
    if 'ai' in source or any('ai' in t.lower() for t in tags):
        tags.append('ai')
    if 'web3' in source or 'blockchain' in source:
        tags.append('web3')
    # Dedupe, title case, limit to 5
    seen = set()
    out = []
    for t in tags:
        norm = t.strip().title()
        if norm and norm.lower() not in seen:
            seen.add(norm.lower())
            out.append(norm)
        if len(out) >= 5:
            break
    return out


# =============================================================================
# Generic submission (any platform)
# =============================================================================

def generate_submission_package(opportunity_id: int) -> Dict[str, Any]:
    """
    Generate a generic submission package that works for ANY platform.
    Returns a JSON with all the fields you'd need to fill in.
    """
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM opportunities WHERE id = ?", (opportunity_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return {'success': False, 'error': 'opportunity_not_found'}
    opp = dict(row)
    conn.close()

    try:
        analysis = json.loads(opp.get('analysis_json') or '{}')
    except Exception:
        analysis = {}
    project = (analysis.get('recommended_project') or {})

    pkg = {
        'opportunity': {
            'name': opp.get('name'),
            'url': opp.get('url'),
            'deadline': opp.get('deadline'),
            'prize_usd': opp.get('prize_usd'),
            'ai_policy': opp.get('ai_policy'),
        },
        'project': {
            'name': project.get('name'),
            'tagline': project.get('tagline'),
            'description': _build_description(opp, project),
            'tech_stack': project.get('tech_stack', {}),
            'key_features': project.get('key_features', []),
            'demo_approach': project.get('demo_approach'),
            'submission_strategy': analysis.get('submission_strategy', ''),
        },
        'submission_checklist': {
            'working_demo': 'pending — deploy via Build Now → Deploy',
            'github_repo': 'pending — push via Build Now',
            'demo_video': 'pending — generate via Build Now → Video',
            'description': 'ready',
            'tags': 'ready — ' + ', '.join(_suggest_tags(opp, project)),
        },
        'deadline': opp.get('deadline'),
        'days_remaining': opp.get('days_remaining'),
    }
    return {'success': True, 'package': pkg}


# =============================================================================
# Save submission to DB
# =============================================================================

def _save_submission(opp_id: int, platform: str, package: Dict[str, Any],
                     status: str = 'pending') -> None:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO submissions (
                opportunity_id, platform, form_data, status, submitted_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            opp_id, platform,
            json.dumps(package)[:8000],
            status,
            datetime.now().isoformat(),
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️  submission save failed: {e}")


# =============================================================================
# Mark a submission as won/lost (for tracking)
# =============================================================================

def record_result(submission_id: int, result: str, notes: str = '') -> bool:
    """Record the result of a submission (won/lost/pending)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE submissions
            SET result = ?, result_date = ?, notes = ?
            WHERE id = ?
        """, (result, datetime.now().isoformat(), notes, submission_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"⚠️  record result failed: {e}")
        return False


# =============================================================================
# Win/Loss tracker
# =============================================================================

def get_win_loss_stats() -> Dict[str, Any]:
    """Get win/loss stats across all submissions."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT result, COUNT(*) as n, COALESCE(SUM(0), 0) as placeholder
        FROM submissions
        GROUP BY result
    """)
    results = {r['result']: r['n'] for r in cursor.fetchall()}

    cursor.execute("SELECT COUNT(*) as n, COALESCE(SUM(s.prize_usd), 0) as total FROM submissions s JOIN opportunities o ON s.opportunity_id = o.id WHERE s.result = 'won'")
    won = cursor.fetchone()
    cursor.execute("SELECT COUNT(*) as n FROM submissions")
    total = cursor.fetchone()

    cursor.execute("""
        SELECT category, COUNT(*) as n
        FROM research_data
        WHERE win_factors IS NOT NULL
        GROUP BY category
    """)
    patterns = [dict(r) for r in cursor.fetchall()]

    conn.close()

    won_count = results.get('won', 0)
    total_count = total['n'] or 0
    return {
        'total_submissions': total_count,
        'won': won_count,
        'lost': results.get('lost', 0),
        'pending': results.get('pending', 0),
        'win_rate': round(won_count / total_count * 100, 1) if total_count else 0,
        'total_prize_won': won['total'] or 0,
        'categories_studied': patterns,
    }


# =============================================================================
# CLI
# =============================================================================

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python submitter.py <opportunity_id> [devpost|mlh|generic]")
        sys.exit(1)
    opp_id = int(sys.argv[1])
    platform = sys.argv[2] if len(sys.argv) > 2 else 'devpost'
    if platform == 'devpost':
        result = submit_to_devpost(opp_id)
    elif platform == 'generic':
        result = generate_submission_package(opp_id)
    else:
        result = generate_submission_package(opp_id)
    print(json.dumps(result, indent=2, default=str)[:3000])
