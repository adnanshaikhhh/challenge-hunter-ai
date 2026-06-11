#!/usr/bin/env python3
"""
Challenge Hunter AI - Database Seeder
Inserts initial seed data into opportunities.db
Run this once after schema.sql to populate with starter opportunities.
"""

import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), 'opportunities.db')


def calculate_score(prize_usd, deadline_days, ai_policy, eligibility, difficulty, source):
    """Calculate opportunity score using Section 3 formula"""
    score = 50  # Start at 50

    # Prize-based scoring
    if prize_usd > 10000:
        score += 15
    elif prize_usd >= 5000:
        score += 10
    elif prize_usd >= 1000:
        score += 5

    # Deadline-based scoring
    if deadline_days and 14 <= deadline_days <= 45:
        score += 10
    elif deadline_days and 7 <= deadline_days < 14:
        score += 5

    # AI policy scoring
    if ai_policy == 'allowed':
        score += 15
    elif ai_policy == 'unclear':
        score -= 15

    # Eligibility scoring
    if eligibility:
        if 'solo' in eligibility.lower():
            score += 5
        if 'global' in eligibility.lower():
            score += 5
        if 'team only' in eligibility.lower() or 'team only' in eligibility.lower():
            score -= 10

    # Difficulty scoring
    if difficulty == 'easy':
        score += 5
    elif difficulty == 'hard':
        score -= 5

    # Large corporate sponsor penalty
    corporate_sponsors = ['google', 'microsoft', 'amazon', 'meta', 'apple', 'nvidia']
    if source:
        source_lower = source.lower()
        if any(sp in source_lower for sp in corporate_sponsors):
            score -= 10

    # Cap between 0 and 100
    return max(0, min(100, score))


def calculate_win_probability(prize_usd, days_remaining, ai_policy, difficulty, eligibility, source):
    """Calculate win probability using Section 3 formula"""
    prob = 30  # Start at 30

    # Prize-based
    if prize_usd > 5000:
        prob += 10

    # Days remaining
    if days_remaining and days_remaining > 14:
        prob += 10

    # AI policy
    if ai_policy == 'allowed':
        prob += 15

    # Large corporate sponsor penalty
    corporate_sponsors = ['google', 'microsoft', 'amazon', 'meta', 'apple', 'nvidia']
    if source:
        source_lower = source.lower()
        if any(sp in source_lower for sp in corporate_sponsors):
            prob -= 20

    # Difficulty
    if difficulty == 'easy':
        prob += 10
    elif difficulty == 'hard':
        prob -= 10

    # Team-only penalty
    if eligibility and 'solo' not in eligibility.lower():
        prob -= 10

    # Cap between 0 and 100
    return max(0, min(100, prob))


def generate_analysis_json(name, prize_usd, ai_policy, difficulty, source, deadline_days):
    """Generate the AI analysis JSON template for Section 6"""
    project_name = name.replace(' ', '-').lower()[:30]
    build_days = 5 if difficulty == 'easy' else (10 if difficulty == 'hard' else 7)

    tech_stacks = {
        'easy': ['Python', 'Flask', 'React', 'SQLite'],
        'medium': ['Python', 'FastAPI', 'React', 'PostgreSQL', 'Docker'],
        'hard': ['Python', 'FastAPI', 'React', 'PostgreSQL', 'Docker', 'Kubernetes', 'Redis']
    }

    summary_map = {
        'easy': f'A beginner-friendly opportunity with a {prize_usd} prize. Perfect for getting started with competitive development.',
        'medium': f'A competitive opportunity with {prize_usd} at stake. Requires solid planning and execution.',
        'hard': f'A challenging high-stakes competition with {prize_usd} prize. Demands serious commitment and technical depth.'
    }

    return {
        "summary": summary_map.get(difficulty, summary_map['medium']),
        "requirements": [
            f"Build a functional demo or prototype",
            f"Submit before {deadline_days} days deadline" if deadline_days else "Submit before deadline",
            "Prepare 2-3 minute video demo",
            "Write clear README and documentation",
            "Create compelling slide deck or landing page"
        ],
        "risks": [
            "High competition from experienced developers",
            "Deadline pressure may affect code quality",
            "Judging criteria may be subjective",
            "Technical issues during live demo"
        ],
        "win_probability_reasoning": f"Based on {difficulty} difficulty, {prize_usd} prize, and {ai_policy} AI policy, this opportunity offers a competitive chance at winning.",
        "build_complexity": difficulty,
        "recommended_project": {
            "name": project_name,
            "concept": f"An AI-powered solution that addresses a real problem in {source or 'the target domain'}",
            "tech_stack": tech_stacks.get(difficulty, tech_stacks['medium']),
            "key_features": [
                "Clean, professional UI/UX",
                "Functional core feature working end-to-end",
                "Clear documentation and setup guide",
                "Short demo video showcasing key functionality"
            ],
            "demo_approach": f"Live 2-3 minute demo showing: (1) The problem being solved, (2) Key features in action, (3) Technical highlights, (4) Future roadmap",
            "estimated_build_days": build_days
        },
        "submission_strategy": "Focus on making the demo video polished and professional. Have a working live demo ready. Prepare backup screenshots. Write compelling project description.",
        "recommended_action": "approve"
    }


def seed_database():
    """Insert seed data into the database"""
    # Ensure database exists
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        print("   Please run schema.sql first: sqlite3 opportunities.db < schema.sql")
        return False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if already seeded
    cursor.execute("SELECT COUNT(*) FROM opportunities")
    count = cursor.fetchone()[0]
    if count > 0:
        print(f"⚠️  Database already has {count} records. Skipping seed.")
        print("   To re-seed, delete opportunities.db and run again.")
        conn.close()
        return True

    # Calculate dates
    today = datetime.now()
    deadline_30 = (today + timedelta(days=30)).strftime('%Y-%m-%d')
    deadline_21 = (today + timedelta(days=21)).strftime('%Y-%m-%d')
    deadline_45 = (today + timedelta(days=45)).strftime('%Y-%m-%d')

    # Seed records
    seed_records = [
        {
            'name': 'Devpost AI Innovation Challenge 2025',
            'url': 'https://devpost.com/hackathons',
            'prize_usd': 10000,
            'deadline': deadline_30,
            'ai_policy': 'allowed',
            'difficulty': 'medium',
            'source': 'Devpost',
            'eligibility': 'Global, solo or team',
            'rules_summary': 'Build innovative projects using AI tools. Any tech stack allowed. Submit a working demo and 2-minute video.',
        },
        {
            'name': 'Hugging Face Open Source AI Grant',
            'url': 'https://huggingface.co/grants',
            'prize_usd': 5000,
            'deadline': deadline_21,
            'ai_policy': 'allowed',
            'difficulty': 'easy',
            'source': 'HuggingFace',
            'eligibility': 'Global, solo',
            'rules_summary': 'Create open source AI projects using Hugging Face tools. Must be fully open source with code public.',
        },
        {
            'name': 'Solana Summer Builder Grant 2025',
            'url': 'https://solana.com/grants',
            'prize_usd': 25000,
            'deadline': deadline_45,
            'ai_policy': 'allowed',
            'difficulty': 'hard',
            'source': 'Solana',
            'eligibility': 'Global, solo or team',
            'rules_summary': 'Build on Solana blockchain. Must submit working product. Multiple grant tiers available up to $50K.',
        },
    ]

    inserted = 0
    for record in seed_records:
        # Calculate days remaining
        deadline_dt = datetime.strptime(record['deadline'], '%Y-%m-%d')
        days_remaining = (deadline_dt - today).days

        # Calculate scores
        score = calculate_score(
            record['prize_usd'],
            days_remaining,
            record['ai_policy'],
            record['eligibility'],
            record['difficulty'],
            record['source']
        )

        win_prob = calculate_win_probability(
            record['prize_usd'],
            days_remaining,
            record['ai_policy'],
            record['difficulty'],
            record['eligibility'],
            record['source']
        )

        # Generate analysis JSON
        analysis = generate_analysis_json(
            record['name'],
            record['prize_usd'],
            record['ai_policy'],
            record['difficulty'],
            record['source'],
            days_remaining
        )

        import json
        analysis_json = json.dumps(analysis)

        try:
            cursor.execute("""
                INSERT INTO opportunities (
                    name, url, prize_usd, deadline, days_remaining,
                    rules_summary, ai_policy, eligibility, difficulty,
                    opportunity_score, win_probability, status,
                    analysis_json, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record['name'],
                record['url'],
                record['prize_usd'],
                record['deadline'],
                days_remaining,
                record.get('rules_summary', ''),
                record['ai_policy'],
                record['eligibility'],
                record['difficulty'],
                score,
                win_prob,
                'pending',
                analysis_json,
                record['source']
            ))
            inserted += 1
            print(f"  ✅ Inserted: {record['name']}")
        except sqlite3.IntegrityError as e:
            print(f"  ⚠️  Skipped (already exists): {record['name']}")

    conn.commit()

    # Log the seed action
    cursor.execute("""
        INSERT INTO scan_log (scan_time, sources_scanned, new_found, errors)
        VALUES (?, ?, ?, ?)
    """, (datetime.now().isoformat(), 0, inserted, None))

    conn.commit()
    conn.close()

    print(f"\n🎉 Seeding complete! Inserted {inserted} opportunities.")
    print(f"📊 Total records in database: {count + inserted}")
    return True


if __name__ == '__main__':
    print("=" * 60)
    print("🎯 Challenge Hunter AI - Database Seeder")
    print("=" * 60)
    print()

    success = seed_database()

    if success:
        print()
        print("🚀 Ready to run the app: python app.py")
        print("🌐 Then open: http://localhost:5000")
    else:
        print()
        print("❌ Seeding failed. Please check the error above.")
        exit(1)