#!/usr/bin/env python3
"""
Challenge Hunter AI v2.0 — Database Seeder
Inserts initial seed data and computes deterministic scores / probabilities.
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta

DB_PATH = os.environ.get(
    'DB_PATH',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'opportunities.db')
)
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql')

# ----------------------------------------------------------------------------
# Scoring helpers (deterministic, no I/O)
# ----------------------------------------------------------------------------

def calculate_score(prize, days, ai_policy, difficulty, eligibility, team_size):
    score = 50
    if prize > 50000:    score += 25
    elif prize > 10000:  score += 20
    elif prize > 5000:   score += 15
    elif prize > 2000:   score += 10
    elif prize > 500:    score += 5

    if 14 <= days <= 45:     score += 12
    elif 7 <= days < 14:     score += 6
    elif days > 45:          score += 4
    elif 0 < days < 7:       score -= 5

    if ai_policy == 'allowed':       score += 20
    elif ai_policy == 'unclear':     score -= 15
    elif ai_policy == 'restricted':  score -= 20
    elif ai_policy == 'banned':      score -= 40

    if eligibility and 'global' in eligibility.lower(): score += 5
    if team_size and 'solo' in team_size.lower():       score += 8

    if difficulty == 'easy':     score += 5
    elif difficulty == 'hard':   score -= 5

    return max(0, min(100, score))


def calculate_win_probability(prize, days, ai_policy, difficulty):
    prob = 30
    if prize > 5000:     prob += 10
    if days > 14:        prob += 10
    if ai_policy == 'allowed': prob += 20
    if difficulty == 'easy':   prob += 15
    elif difficulty == 'hard': prob -= 15
    if prize > 50000:    prob -= 10
    return max(5, min(95, prob))


def calculate_expected_value(prize, win_prob):
    return round(prize * (win_prob / 100.0), 2)


# ----------------------------------------------------------------------------
# AI analysis template (deterministic, no network call)
# ----------------------------------------------------------------------------

def generate_analysis(name, prize, ai_policy, difficulty, source, days):
    project_name = name.split()[0].lower() + '-companion'
    return {
        "summary": f"{name} offers ${prize:,} for solo developers using AI tools. The deadline is {days} days away, leaving enough runway to ship a polished demo.",
        "why_this_is_good": f"AI policy is {ai_policy}, the prize-to-effort ratio is strong, and {source} attracts well-funded, high-signal judges.",
        "requirements": [
            "Build a working demo and submit a 2-3 minute walkthrough video.",
            "Document setup, architecture, and future roadmap in the README.",
            "Publish code publicly (GitHub) and deploy a live demo URL."
        ],
        "risks": [
            "Tight deadline — mitigate by shipping a vertical slice first.",
            "Judge subjectivity — mitigate by emphasising metrics and visuals."
        ],
        "win_probability_reasoning": f"Probability of {calculate_win_probability(prize, days, ai_policy, difficulty)}% reflects the {difficulty} difficulty and ${prize:,} prize class.",
        "build_complexity": difficulty,
        "time_to_build_estimate": f"{5 if difficulty == 'easy' else 10 if difficulty == 'hard' else 7} days working solo with AI tools.",
        "recommended_project": {
            "name": project_name,
            "tagline": "AI-powered productivity companion built in a weekend.",
            "concept": "A pragmatic tool that solves a real workflow gap with a delightful interface, leveraging LLMs as the engine.",
            "problem_solved": "Slow, manual workflows that burn time and break flow.",
            "tech_stack": {
                "frontend": ["React", "TailwindCSS"],
                "backend": ["Python", "FastAPI"],
                "database": ["SQLite"],
                "ai": ["OpenAI API", "LangChain"],
                "deployment": ["Railway", "Vercel"]
            },
            "key_features": [
                "One-tap core flow — judges will demo this within 5 seconds.",
                "Persistent memory — surprising recall across sessions.",
                "Beautiful shareable output — wins screenshots and word-of-mouth."
            ],
            "demo_approach": "1) Show the empty state. 2) Run the headline action. 3) Display the saved result. 4) Show share export. 5) End on the metrics dashboard.",
            "wow_factor": "A live, real-time visualization that reacts to user input — the screenshot judges remember.",
            "estimated_build_days": 5 if difficulty == 'easy' else 7
        },
        "submission_strategy": "Lead with the demo video. Make the GitHub README scannable. Submit 24 hours early to avoid platform issues.",
        "judge_appeal": f"{source} judges reward execution speed, polish, and clear metrics — design for those.",
        "alternative_projects": [
            {"name": "lite", "concept": "Stripped-down CLI version of the same idea.", "build_days": 2},
            {"name": "pro", "concept": "Full SaaS with billing and team workspaces.", "build_days": 10}
        ],
        "recommended_action": "approve",
        "action_reasoning": "High score, AI-friendly rules, healthy deadline — clear green light."
    }


# ----------------------------------------------------------------------------
# Seed data
# ----------------------------------------------------------------------------

def seed_records():
    today = datetime.now()
    return [
        {
            'name': 'Devpost AI Innovation Challenge 2025',
            'url': 'https://devpost.com/hackathons',
            'prize_usd': 10000,
            'prize_text': '$10,000 grand prize',
            'days': 30,
            'ai_policy': 'allowed',
            'difficulty': 'medium',
            'source': 'Devpost',
            'source_url': 'https://devpost.com/hackathons',
            'eligibility': 'Global, solo or team',
            'team_size': 'solo or team',
            'rules_summary': 'Build an innovative project using AI tools. Any stack. Submit a working demo and 2-minute video.',
            'tags': 'ai,devpost,hackathon,global'
        },
        {
            'name': 'Hugging Face Open Source AI Grant',
            'url': 'https://huggingface.co/grants',
            'prize_usd': 5000,
            'prize_text': '$5,000 grant',
            'days': 21,
            'ai_policy': 'allowed',
            'difficulty': 'easy',
            'source': 'HuggingFace',
            'source_url': 'https://huggingface.co/grants',
            'eligibility': 'Global, solo',
            'team_size': 'solo',
            'rules_summary': 'Open-source AI project using Hugging Face tools. Code must be public.',
            'tags': 'ai,grants,open-source,oss'
        },
        {
            'name': 'Solana Summer Builder Grant 2025',
            'url': 'https://solana.com/grants',
            'prize_usd': 25000,
            'prize_text': '$25,000 grant (tiered up to $50K)',
            'days': 45,
            'ai_policy': 'allowed',
            'difficulty': 'hard',
            'source': 'Solana',
            'source_url': 'https://solana.com/grants',
            'eligibility': 'Global, solo or team',
            'team_size': 'solo or team',
            'rules_summary': 'Build on Solana. Working product required. Multiple grant tiers.',
            'tags': 'web3,solana,grants,blockchain'
        },
        {
            'name': 'Anthropic API Developer Challenge 2025',
            'url': 'https://www.anthropic.com/news',
            'prize_usd': 15000,
            'prize_text': '$15,000 in API credits + cash',
            'days': 35,
            'ai_policy': 'allowed',
            'difficulty': 'medium',
            'source': 'Anthropic',
            'source_url': 'https://www.anthropic.com/news',
            'eligibility': 'Global, solo',
            'team_size': 'solo',
            'rules_summary': 'Use the Anthropic API to ship a useful, well-documented AI app.',
            'tags': 'ai,anthropic,claude,api'
        },
        {
            'name': 'Replit Bounty Sprint',
            'url': 'https://replit.com/bounties',
            'prize_usd': 2500,
            'prize_text': '$2,500 bounty',
            'days': 10,
            'ai_policy': 'allowed',
            'difficulty': 'easy',
            'source': 'Replit',
            'source_url': 'https://replit.com/bounties',
            'eligibility': 'Global, solo',
            'team_size': 'solo',
            'rules_summary': 'Solve a featured Replit bounty. Code must run on Replit.',
            'tags': 'bounty,replit,easy,quick'
        }
    ]


def ensure_schema(conn):
    if not os.path.exists(SCHEMA_PATH):
        raise FileNotFoundError(f"schema.sql not found at {SCHEMA_PATH}")
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())


def init_db():
    """Create database and schema if missing. Idempotent."""
    new_db = not os.path.exists(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    if new_db:
        ensure_schema(conn)
    return conn, new_db


def seed_database():
    conn, new_db = init_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM opportunities")
    existing = cursor.fetchone()[0]
    if existing > 0 and not new_db:
        print(f"⚠️  Database already has {existing} records. Skipping seed.")
        conn.close()
        return existing

    today = datetime.now()
    inserted = 0
    for r in seed_records():
        deadline = (today + timedelta(days=r['days'])).strftime('%Y-%m-%d')
        score = calculate_score(
            r['prize_usd'], r['days'], r['ai_policy'],
            r['difficulty'], r['eligibility'], r['team_size']
        )
        prob = calculate_win_probability(
            r['prize_usd'], r['days'], r['ai_policy'], r['difficulty']
        )
        ev = calculate_expected_value(r['prize_usd'], prob)
        analysis = generate_analysis(
            r['name'], r['prize_usd'], r['ai_policy'],
            r['difficulty'], r['source'], r['days']
        )

        try:
            cursor.execute("""
                INSERT INTO opportunities (
                    name, url, prize_usd, prize_text, deadline, days_remaining,
                    rules_summary, ai_policy, eligibility, team_size, difficulty,
                    opportunity_score, win_probability, expected_value,
                    status, analysis_json, source, source_url, tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                r['name'], r['url'], r['prize_usd'], r['prize_text'],
                deadline, r['days'],
                r['rules_summary'], r['ai_policy'], r['eligibility'],
                r['team_size'], r['difficulty'],
                score, prob, ev,
                'pending', json.dumps(analysis),
                r['source'], r['source_url'], r['tags']
            ))
            inserted += 1
            print(f"  ✅ {r['name']} (score {score}, ev ${ev:,.0f})")
        except sqlite3.IntegrityError:
            print(f"  ⚠️  Skipped (duplicate): {r['name']}")

    cursor.execute("""
        INSERT INTO scan_log (scan_time, sources_scanned, new_found, errors)
        VALUES (?, ?, ?, ?)
    """, (datetime.now().isoformat(), 0, inserted, None))

    conn.commit()
    conn.close()
    print(f"\n🎉 Seeded {inserted} opportunities.")
    return inserted


if __name__ == '__main__':
    print("=" * 60)
    print("🎯 Challenge Hunter AI v2.0 — Seeder")
    print("=" * 60)
    n = seed_database()
    print(f"\n📊 Total in DB: {n}")
