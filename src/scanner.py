#!/usr/bin/env python3
"""
Challenge Hunter AI - Scanner Engine
Discovers opportunities from multiple sources, calculates scores,
generates AI analysis, and marks expired opportunities.
"""

import os
import sqlite3
import json
import time
import re
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from apscheduler.schedulers.background import BackgroundScheduler

# =============================================================================
# CONFIGURATION
# =============================================================================

DB_PATH = os.environ.get('DB_PATH', os.path.join(os.path.dirname(__file__), 'opportunities.db'))

# Rate limiting
REQUEST_DELAY = 3  # seconds between HTTP requests
AI_ANALYSIS_DELAY = 3  # seconds between AI analysis calls

# Scanner settings
SCAN_INTERVAL_HOURS = int(os.environ.get('SCAN_INTERVAL_HOURS', 6))
MIN_PRIZE_USD = int(os.environ.get('MIN_PRIZE_USD', 500))
MIN_SCORE_FOR_ALERT = int(os.environ.get('MIN_SCORE_FOR_ALERT', 70))

# User agents
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

# Sources to scrape
SOURCES = [
    'https://devpost.com/hackathons',
    'https://mlh.io/seasons',
    'https://hackerearth.com/challenges',
    'https://lablab.ai/event',
    'https://devfolio.co/hackathons',
    'https://huggingface.co/events',
    'https://kaggle.com/competitions',
    'https://unstop.com',
]

# Search queries for discovery
SEARCH_QUERIES = [
    'AI hackathon 2025 cash prize open registration',
    'vibe coding competition prize 2025',
    'agentic AI builder challenge grant 2025',
    'startup pitch competition AI tools allowed 2025',
    'open source AI grant application 2025',
    'no-code AI competition prize 2025',
    'Solana builder grant 2025',
    'Ethereum developer grant open',
    'Anthropic developer challenge 2025',
    'OpenAI hackathon prize 2025',
]

# =============================================================================
# AI POLICY DETECTION
# =============================================================================

AI_ALLOWED_KEYWORDS = [
    'ai allowed', 'ai tools permitted', 'use any tools',
    'vibe coding', 'agentic', 'llm allowed', 'ai-assisted',
    'generative ai', 'chatgpt allowed', 'copilot allowed',
    'use of ai is allowed', 'artificial intelligence allowed',
    'machine learning allowed', 'no restrictions on tools',
    'any programming tool', 'open source ai', 'llms permitted',
]

AI_BANNED_KEYWORDS = [
    'no ai', 'ai prohibited', 'must be human',
    'no llm', 'manual only', 'no automated',
    'no machine learning', 'no generative ai',
    'human coding only', 'no artificial intelligence',
    'ai tools not allowed', 'no chatgpt',
]

# =============================================================================
# SCORING FUNCTIONS
# =============================================================================

def calculate_opportunity_score(prize_usd, days_remaining, ai_policy, eligibility, difficulty, source):
    """Calculate opportunity score (0-100) per Section 3 formula"""
    score = 50  # Start at 50

    # Prize-based scoring
    if prize_usd > 10000:
        score += 15
    elif prize_usd >= 5000:
        score += 10
    elif prize_usd >= 1000:
        score += 5

    # Deadline-based scoring
    if days_remaining and 14 <= days_remaining <= 45:
        score += 10
    elif days_remaining and 7 <= days_remaining < 14:
        score += 5

    # AI policy scoring
    if ai_policy == 'allowed':
        score += 15
    elif ai_policy == 'unclear':
        score -= 15

    # Eligibility scoring
    if eligibility:
        eligibility_lower = eligibility.lower()
        if 'solo' in eligibility_lower:
            score += 5
        if 'global' in eligibility_lower:
            score += 5
        if 'team only' in eligibility_lower:
            score -= 10

    # Difficulty scoring
    if difficulty == 'easy':
        score += 5
    elif difficulty == 'hard':
        score -= 5

    # Corporate sponsor penalty
    corporate_sponsors = ['google', 'microsoft', 'amazon', 'meta', 'apple', 'nvidia']
    if source:
        source_lower = source.lower()
        if any(sp in source_lower for sp in corporate_sponsors):
            score -= 10

    # Cap between 0 and 100
    return max(0, min(100, score))


def calculate_win_probability(prize_usd, days_remaining, ai_policy, difficulty, eligibility, source):
    """Calculate win probability (0-100) per Section 3 formula"""
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

    # Corporate sponsor penalty
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


# =============================================================================
# AI ANALYSIS GENERATION
# =============================================================================

def generate_analysis(opportunity):
    """Generate the AI analysis JSON template for an opportunity"""
    name = opportunity.get('name', '')
    prize_usd = opportunity.get('prize_usd', 0)
    ai_policy = opportunity.get('ai_policy', 'unclear')
    difficulty = opportunity.get('difficulty', 'medium')
    source = opportunity.get('source', '')
    deadline = opportunity.get('deadline', '')
    eligibility = opportunity.get('eligibility', '')

    project_name = name.replace(' ', '-').replace('  ', '-').lower()[:40]

    # Estimate build days based on difficulty
    build_days_map = {'easy': 5, 'medium': 7, 'hard': 12}
    build_days = build_days_map.get(difficulty, 7)

    # Tech stack based on difficulty
    tech_stacks = {
        'easy': ['Python', 'Flask', 'React', 'SQLite', 'Tailwind CSS'],
        'medium': ['Python', 'FastAPI', 'React', 'PostgreSQL', 'Docker'],
        'hard': ['Python', 'FastAPI', 'React', 'PostgreSQL', 'Docker', 'Kubernetes', 'Redis', 'Celery']
    }

    # Summarize the opportunity
    summaries = {
        'easy': f'A beginner-friendly challenge with a ${prize_usd:,} prize pool. Great opportunity for developers new to competitive building.',
        'medium': f'A competitive opportunity with ${prize_usd:,} at stake. Requires solid planning, execution, and a polished demo to win.',
        'hard': f'A challenging high-stakes competition with ${prize_usd:,} prize. Demands serious technical skill, time commitment, and a standout project.'
    }

    return {
        "summary": summaries.get(difficulty, summaries['medium']),
        "requirements": [
            "Build a fully functional demo or prototype",
            f"Submit before the deadline: {deadline}",
            "Create a 2-3 minute video demo",
            "Write clear, professional README and documentation",
            "Prepare compelling project description and screenshots"
        ],
        "risks": [
            "High competition from experienced developers worldwide",
            "Deadline pressure may lead to code quality issues",
            "Judging criteria may be subjective or unclear",
            "Technical issues could occur during live demo",
            "Prize distribution may be delayed after announcement"
        ],
        "win_probability_reasoning": f"With a {difficulty} difficulty level, ${prize_usd:,} prize, and {ai_policy} AI policy, this opportunity provides a {'strong' if difficulty == 'easy' else 'moderate' if difficulty == 'medium' else 'challenging'} chance at winning. Focus on build quality and demo polish.",
        "build_complexity": difficulty,
        "recommended_project": {
            "name": project_name,
            "concept": f"An AI-powered solution leveraging {source or 'modern AI tools'} to solve a real problem, with a polished demo and professional presentation.",
            "tech_stack": tech_stacks.get(difficulty, tech_stacks['medium']),
            "key_features": [
                "Clean, modern UI/UX with responsive design",
                "Core functionality working end-to-end",
                "Clear documentation with setup instructions",
                "Short demo video (under 3 minutes)",
                "Deployment-ready with clear launch instructions"
            ],
            "demo_approach": "Minute 1: Problem statement and solution overview. Minute 2: Live demo of key features. Minute 3: Technical highlights and future roadmap.",
            "estimated_build_days": build_days
        },
        "submission_strategy": "Focus heavily on the demo video quality and project presentation. Ensure the README is polished and clearly explains the value proposition. Submit early to avoid last-minute technical issues. Have a backup static demo ready in case of live demo problems.",
        "recommended_action": "approve"
    }


# =============================================================================
# AI POLICY DETECTION
# =============================================================================

def detect_ai_policy(text):
    """Detect AI policy from rules text. Returns 'allowed', 'banned', or 'unclear'"""
    if not text:
        return 'unclear'

    text_lower = text.lower()

    # Check for banned first (more specific)
    for keyword in AI_BANNED_KEYWORDS:
        if keyword in text_lower:
            return 'banned'

    # Check for allowed
    for keyword in AI_ALLOWED_KEYWORDS:
        if keyword in text_lower:
            return 'allowed'

    return 'unclear'


def detect_ai_policy_from_html(soup):
    """Try to detect AI policy from HTML page content"""
    # Look for common patterns in text
    page_text = soup.get_text()

    # Also search in specific elements like rules, faq, etc.
    rules_headers = soup.find_all(['h2', 'h3', 'h4'], text=re.compile(r'rules?|guidelines?|eligibility', re.I))
    for header in rules_headers:
        parent = header.find_parent(['div', 'section', 'article'])
        if parent:
            text = parent.get_text()
            policy = detect_ai_policy(text)
            if policy != 'unclear':
                return policy

    return detect_ai_policy(page_text)


# =============================================================================
# DEADLINE PARSING
# =============================================================================

def parse_deadline(text):
    """Try to parse deadline from text. Returns ISO date string or None."""
    if not text:
        return None

    # Try common formats
    date_patterns = [
        r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',
        r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',
        r'(\w+)\s+(\d{1,2}),?\s+(\d{4})',
        r'(\d{1,2})\s+(\w+)\s+(\d{4})',
    ]

    for pattern in date_patterns:
        match = re.search(pattern, text, re.I)
        if match:
            try:
                # Try to create a date
                if match.group(3):  # Year is group 3
                    return f"{match.group(3)}-{match.group(1).zfill(2)}-{match.group(2).zfill(2)}"
            except (ValueError, IndexError):
                pass

    # Try relative dates like "in 30 days"
    relative_match = re.search(r'in\s+(\d+)\s+days?', text, re.I)
    if relative_match:
        days = int(relative_match.group(1))
        future = datetime.now() + timedelta(days=days)
        return future.strftime('%Y-%m-%d')

    return None


def extract_prize(text):
    """Extract prize amount from text. Returns integer USD."""
    if not text:
        return 0

    # Look for dollar amounts
    prize_patterns = [
        r'\$[\d,]+',  # $10,000
        r'USD\s*[\d,]+',
        r'[\d,]+[\s-]?USD',
        r'prize[d\s]+of\s+[\d,]+',
        r'[\d,]+[\s-]?dollars?',
    ]

    for pattern in prize_patterns:
        match = re.search(pattern, text, re.I)
        if match:
            amount_str = re.sub(r'[^\d]', '', match.group())
            try:
                return int(amount_str)
            except ValueError:
                pass

    return 0


# =============================================================================
# WEB SCRAPING HELPERS
# =============================================================================

def fetch_page(url, timeout=15):
    """Fetch a URL and return BeautifulSoup object. Returns None on failure."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'lxml')
    except Exception as e:
        print(f"  ⚠️  Failed to fetch {url}: {e}")
        return None


def extract_opportunities_from_source(url, source_name):
    """Extract opportunities from a source URL. Returns list of opportunity dicts."""
    opportunities = []
    soup = fetch_page(url)

    if not soup:
        return opportunities

    time.sleep(REQUEST_DELAY)

    # Generic extraction - look for common patterns
    # This can be enhanced per source

    # Look for hackathon/event cards
    cards = soup.select('.challenge-card, .hackathon-card, .event-card, .challenge-item, [data-cy*="challenge"]')

    for card in cards:
        try:
            # Extract basic info
            name_elem = card.select_one('h2, h3, .title, .name, a')
            url_elem = card.select_one('a')
            prize_elem = card.select_one('.prize, .reward, .award')
            deadline_elem = card.select_one('.deadline, .date, .submission-date')

            if not name_elem:
                continue

            name = name_elem.get_text(strip=True)
            opp_url = url_elem.get('href', '') if url_elem else ''
            if opp_url and not opp_url.startswith('http'):
                opp_url = url

            prize = extract_prize(prize_elem.get_text() if prize_elem else '')
            deadline = parse_deadline(deadline_elem.get_text() if deadline_elem else '')

            # Calculate days remaining
            days_remaining = None
            if deadline:
                try:
                    deadline_dt = datetime.strptime(deadline, '%Y-%m-%d')
                    days_remaining = max(0, (deadline_dt - datetime.now()).days)
                except ValueError:
                    pass

            opp = {
                'name': name,
                'url': opp_url,
                'prize_usd': prize,
                'deadline': deadline,
                'days_remaining': days_remaining,
                'source': source_name,
                'ai_policy': 'unclear',
                'difficulty': 'medium',
                'eligibility': 'Global',
            }

            opportunities.append(opp)
        except Exception as e:
            print(f"  ⚠️  Error parsing card: {e}")
            continue

    return opportunities


# =============================================================================
# SCANNER ENGINE CLASS
# =============================================================================

class ScannerEngine:
    """Main scanner engine for discovering and processing opportunities"""

    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.scheduler = None
        self.errors = []

    def get_db_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)

    def is_url_in_db(self, url):
        """Check if URL already exists in database"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM opportunities WHERE url = ?", (url,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists

    def insert_opportunity(self, opp):
        """Insert a new opportunity into the database"""
        # Skip if already exists
        if self.is_url_in_db(opp.get('url', '')):
            return False

        # Calculate scores
        score = calculate_opportunity_score(
            opp.get('prize_usd', 0),
            opp.get('days_remaining'),
            opp.get('ai_policy', 'unclear'),
            opp.get('eligibility', ''),
            opp.get('difficulty', 'medium'),
            opp.get('source', '')
        )

        win_prob = calculate_win_probability(
            opp.get('prize_usd', 0),
            opp.get('days_remaining'),
            opp.get('ai_policy', 'unclear'),
            opp.get('difficulty', 'medium'),
            opp.get('eligibility', ''),
            opp.get('source', '')
        )

        # Generate analysis
        analysis = generate_analysis(opp)
        analysis_json = json.dumps(analysis)

        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO opportunities (
                    name, url, prize_usd, deadline, days_remaining,
                    rules_summary, ai_policy, eligibility, difficulty,
                    opportunity_score, win_probability, status,
                    analysis_json, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                opp.get('name', ''),
                opp.get('url', ''),
                opp.get('prize_usd', 0),
                opp.get('deadline'),
                opp.get('days_remaining'),
                opp.get('rules_summary', ''),
                opp.get('ai_policy', 'unclear'),
                opp.get('eligibility', ''),
                opp.get('difficulty', 'medium'),
                score,
                win_prob,
                'pending',
                analysis_json,
                opp.get('source', '')
            ))
            conn.commit()
            new_id = cursor.lastrowid
            conn.close()

            print(f"  ✅ New opportunity: {opp.get('name')} (score: {score})")

            # If high value, try to send alert
            if score >= MIN_SCORE_FOR_ALERT:
                try:
                    from telegram_bot import TelegramBotHandler
                    bot = TelegramBotHandler()
                    opp_with_score = dict(opp)
                    opp_with_score['opportunity_score'] = score
                    opp_with_score['win_probability'] = win_prob
                    opp_with_score['analysis_json'] = analysis
                    bot.send_high_value_alert(opp_with_score)
                except Exception as e:
                    print(f"  ⚠️  Telegram alert failed: {e}")

            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False
        except Exception as e:
            print(f"  ⚠️  Database insert error: {e}")
            conn.close()
            return False

    def mark_expired(self):
        """Mark opportunities as expired if not updated in 48 hours"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        cutoff = datetime.now() - timedelta(hours=48)
        cursor.execute("""
            UPDATE opportunities
            SET status = 'expired', updated_at = ?
            WHERE status = 'pending'
            AND updated_at < ?
        """, (datetime.now().isoformat(), cutoff.isoformat()))

        count = cursor.rowcount
        conn.commit()
        conn.close()

        if count > 0:
            print(f"  ⏰ Marked {count} opportunities as expired")

    def scan_sources(self):
        """Scan all configured sources for new opportunities"""
        total_new = 0

        for source_url in SOURCES:
            source_name = source_url.split('//')[1].split('/')[0]
            print(f"\n  🔍 Scanning {source_name}...")

            try:
                opportunities = extract_opportunities_from_source(source_url, source_name)
                for opp in opportunities:
                    if self.insert_opportunity(opp):
                        total_new += 1
            except Exception as e:
                error_msg = f"Error scanning {source_name}: {e}"
                print(f"  ⚠️  {error_msg}")
                self.errors.append(error_msg)

            time.sleep(REQUEST_DELAY)

        return total_new

    def run_full_scan(self):
        """Run a complete scan cycle"""
        print("=" * 60)
        print("🎯 Challenge Hunter AI - Scanner Starting")
        print(f"   Started at: {datetime.now().isoformat()}")
        print("=" * 60)

        self.errors = []
        sources_scanned = len(SOURCES)
        new_found = self.scan_sources()
        self.mark_expired()

        # Log scan
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO scan_log (scan_time, sources_scanned, new_found, errors)
            VALUES (?, ?, ?, ?)
        """, (datetime.now().isoformat(), sources_scanned, new_found, json.dumps(self.errors) if self.errors else None))
        conn.commit()
        conn.close()

        result = {
            'sources_scanned': sources_scanned,
            'new_found': new_found,
            'errors': self.errors
        }

        print("\n" + "=" * 60)
        print(f"✅ Scan complete: {new_found} new opportunities found")
        print("=" * 60)

        return result

    def start_scheduler(self):
        """Start the background scheduler for periodic scanning"""
        if self.scheduler and self.scheduler.running:
            return

        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(
            self.run_full_scan,
            'interval',
            hours=SCAN_INTERVAL_HOURS,
            id='challenge_hunter_scan',
            name='Challenge Hunter AI Scanner',
            replace_existing=True
        )
        self.scheduler.start()
        print(f"📅 Scanner scheduler running every {SCAN_INTERVAL_HOURS} hours")

    def stop_scheduler(self):
        """Stop the background scheduler"""
        if self.scheduler:
            self.scheduler.shutdown()
            self.scheduler = None


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("Starting Challenge Hunter AI Scanner...")
    scanner = ScannerEngine()
    result = scanner.run_full_scan()
    print(f"\nScan Results: {result}")