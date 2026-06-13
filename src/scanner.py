#!/usr/bin/env python3
"""
Challenge Hunter AI v2.0 — Discovery Engine
Scans 30+ sources, classifies AI policy, scores, and persists to DB.
"""

from __future__ import annotations

import json
import os
import random
import re
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, parse_qs, unquote

import requests
from bs4 import BeautifulSoup

from analyzer import analyze
from config import (
    AI_ALLOWED_KEYWORDS, AI_BANNED_KEYWORDS, ALL_SOURCES, DB_PATH,
    DUCKDUCKGO_QUERIES, EXPIRY_THRESHOLD_HOURS, HTTP_HEADERS,
    MIN_PRIZE_USD, REQUEST_DELAY_SECONDS, USER_AGENT
)
from scorer import (
    calculate_expected_value, calculate_opportunity_score, calculate_win_probability
)


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def _now() -> str:
    return datetime.now().isoformat()


def _days_until(deadline_str: str) -> int:
    if not deadline_str:
        return 0
    for fmt in ('%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%b %d, %Y'):
        try:
            d = datetime.strptime(deadline_str, fmt)
            return max(0, (d - datetime.now()).days)
        except ValueError:
            continue
    return 0


def _parse_prize(text: str) -> int:
    if not text:
        return 0
    nums = re.findall(r'[\$€£]?\s*([\d,]{3,})', text)
    if not nums:
        return 0
    try:
        return max(int(n.replace(',', '')) for n in nums)
    except ValueError:
        return 0


def detect_ai_policy(text: str) -> str:
    if not text:
        return 'unclear'
    t = text.lower()
    if any(kw in t for kw in AI_BANNED_KEYWORDS):
        return 'banned'
    if any(kw in t for kw in AI_ALLOWED_KEYWORDS):
        return 'allowed'
    return 'unclear'


def _safe_request(url: str, timeout: int = 15) -> Optional[str]:
    try:
        r = requests.get(url, headers=HTTP_HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  ⚠️  fetch {url}: {e}")
        return None


# ----------------------------------------------------------------------------
# Source-specific parsers (best-effort, all wrapped in try/except)
# ----------------------------------------------------------------------------

def _generic_listing_parser(html: str, base_url: str, source: str) -> List[Dict[str, Any]]:
    """Pull links + headlines from a generic listing page."""
    if not html:
        return []
    soup = BeautifulSoup(html, 'lxml')
    results: List[Dict[str, Any]] = []
    seen = set()
    # Look for anchors with prize / hackathon / grant signals
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.startswith('/'):
            parsed = urlparse(base_url)
            href = f"{parsed.scheme}://{parsed.netloc}{href}"
        if not href.startswith('http'):
            continue
        if href in seen:
            continue
        text = a.get_text(' ', strip=True)
        if not text or len(text) < 6 or len(text) > 200:
            continue
        low = text.lower()
        if not any(kw in low for kw in (
            'hackathon', 'grant', 'bounty', 'challenge', 'prize', 'competition',
            'award', 'cup', 'summit', 'contest', 'fund'
        )):
            continue
        seen.add(href)
        results.append({
            'name': text[:140],
            'url': href,
            'prize_text': '',
            'deadline': None,
            'rules_summary': text,
            'ai_policy': detect_ai_policy(text),
            'source': source,
            'source_url': base_url,
        })
        if len(results) >= 20:
            break
    return results


def _devpost(html: str) -> List[Dict[str, Any]]:
    return _generic_listing_parser(html, 'https://devpost.com/hackathons', 'Devpost')


def _mlh(html: str) -> List[Dict[str, Any]]:
    return _generic_listing_parser(html, 'https://mlh.io/seasons', 'MLH')


def _huggingface(html: str) -> List[Dict[str, Any]]:
    return _generic_listing_parser(html, 'https://huggingface.co/events', 'HuggingFace')


def _solana(html: str) -> List[Dict[str, Any]]:
    return _generic_listing_parser(html, 'https://solana.com/grants', 'Solana')


def _replit(html: str) -> List[Dict[str, Any]]:
    return _generic_listing_parser(html, 'https://replit.com/bounties', 'Replit')


def _kaggle(html: str) -> List[Dict[str, Any]]:
    return _generic_listing_parser(html, 'https://kaggle.com/competitions', 'Kaggle')


PARSERS = {
    'devpost.com': _devpost,
    'mlh.io': _mlh,
    'huggingface.co': _huggingface,
    'solana.com': _solana,
    'replit.com': _replit,
    'kaggle.com': _kaggle,
}


def _parser_for(url: str):
    for needle, fn in PARSERS.items():
        if needle in url:
            return fn
    return lambda html: _generic_listing_parser(html, url, urlparse(url).netloc)


# ----------------------------------------------------------------------------
# DuckDuckGo HTML search
# ----------------------------------------------------------------------------

def _ddg_search(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    url = 'https://html.duckduckgo.com/html/'
    try:
        r = requests.post(
            url,
            data={'q': query, 'kl': 'us-en'},
            headers=HTTP_HEADERS,
            timeout=15
        )
        r.raise_for_status()
    except Exception as e:
        print(f"  ⚠️  DDG search failed: {e}")
        return []

    soup = BeautifulSoup(r.text, 'lxml')
    out: List[Dict[str, Any]] = []
    for result in soup.select('.result')[:limit]:
        a = result.select_one('a.result__a')
        snippet_el = result.select_one('.result__snippet')
        if not a or not a.get('href'):
            continue
        raw_href = a['href']
        # DDG wraps in //duckduckgo.com/l/?uddg=<encoded>
        actual_url = raw_href
        if 'uddg=' in raw_href:
            try:
                qs = parse_qs(urlparse(raw_href).query)
                actual_url = unquote(qs.get('uddg', [raw_href])[0])
            except Exception:
                actual_url = raw_href
        title = a.get_text(strip=True)
        snippet = snippet_el.get_text(' ', strip=True) if snippet_el else ''
        out.append({
            'name': title[:140],
            'url': actual_url,
            'prize_text': '',
            'deadline': None,
            'rules_summary': snippet,
            'ai_policy': detect_ai_policy(snippet + ' ' + title),
            'source': 'DuckDuckGo',
            'source_url': url,
        })
    return out


# ----------------------------------------------------------------------------
# Persistence
# ----------------------------------------------------------------------------

def _record_exists(cursor, url: str) -> bool:
    cursor.execute("SELECT 1 FROM opportunities WHERE url = ?", (url,))
    return cursor.fetchone() is not None


def _insert_or_skip(cursor, opp: Dict[str, Any]) -> bool:
    """
    Score, analyse, persist. Return True if newly inserted.
    """
    if _record_exists(cursor, opp['url']):
        return False
    prize = _parse_prize(opp.get('prize_text', '') + ' ' + opp.get('rules_summary', ''))
    if prize < MIN_PRIZE_USD and not opp.get('prize_text'):
        # Heuristic: if no prize at all and the source isn't a bounty, allow small
        prize = max(prize, 500)
    days = _days_until(opp.get('deadline') or '')
    enriched = dict(opp)
    enriched['prize_usd'] = prize
    enriched['days_remaining'] = days
    score = calculate_opportunity_score(enriched)
    prob = calculate_win_probability(enriched)
    ev = calculate_expected_value(prize, prob)
    analysis = analyze(enriched, use_llm=bool(os.environ.get('OPENAI_API_KEY')))

    cursor.execute("""
        INSERT OR IGNORE INTO opportunities (
            name, url, prize_usd, prize_text, deadline, days_remaining,
            rules_summary, ai_policy, eligibility, team_size, difficulty,
            opportunity_score, win_probability, expected_value,
            status, analysis_json, source, source_url, tags
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        opp['name'], opp['url'], prize, opp.get('prize_text', ''),
        opp.get('deadline'), days,
        opp.get('rules_summary', ''), opp.get('ai_policy', 'unclear'),
        opp.get('eligibility', 'Global'), opp.get('team_size', 'solo'),
        opp.get('difficulty', 'medium'),
        score, prob, ev,
        'pending', json.dumps(analysis),
        opp.get('source', ''), opp.get('source_url', ''),
        opp.get('tags', '')
    ))
    return cursor.rowcount > 0


def _log_scan(cursor, sources: int, new_found: int, high_value: int, errors: List[str], duration: float):
    cursor.execute("""
        INSERT INTO scan_log (scan_time, sources_scanned, new_found, high_value_found, errors, duration_seconds)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (_now(), sources, new_found, high_value, json.dumps(errors), duration))


def expire_stale(cursor):
    """Mark pending opportunities with no activity in 72h as expired."""
    threshold = (datetime.now() - timedelta(hours=EXPIRY_THRESHOLD_HOURS)).isoformat()
    cursor.execute("""
        UPDATE opportunities
        SET status = 'expired', updated_at = ?
        WHERE status = 'pending' AND updated_at < ?
    """, (_now(), threshold))


# ----------------------------------------------------------------------------
# Public: run a full scan
# ----------------------------------------------------------------------------

class ScannerEngine:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DB_PATH
        self.errors: List[str] = []

    # ----------------------------------------------------------------
    def _scan_source(self, url: str) -> List[Dict[str, Any]]:
        time.sleep(REQUEST_DELAY_SECONDS)
        html = _safe_request(url)
        if not html:
            self.errors.append(f"fetch failed: {url}")
            return []
        parser = _parser_for(url)
        try:
            return parser(html)
        except Exception as e:
            self.errors.append(f"parse failed: {url}: {e}")
            return []

    # ----------------------------------------------------------------
    def _scan_ddg(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for q in DUCKDUCKGO_QUERIES:
            time.sleep(REQUEST_DELAY_SECONDS)
            out.extend(_ddg_search(q))
        return out

    # ----------------------------------------------------------------
    def run_full_scan(self) -> Dict[str, Any]:
        start = time.time()
        conn = _conn()
        cursor = conn.cursor()
        new_found = 0
        high_value = 0
        sources_scanned = 0

        print(f"🔍 Starting full scan at {_now()}")
        all_opps: List[Dict[str, Any]] = []

        for url in ALL_SOURCES:
            try:
                sources_scanned += 1
                opps = self._scan_source(url)
                all_opps.extend(opps)
                print(f"  ✓ {url} — {len(opps)} candidates")
            except Exception as e:
                self.errors.append(f"{url}: {e}")

        # DuckDuckGo discovery
        try:
            ddg_opps = self._scan_ddg()
            all_opps.extend(ddg_opps)
            print(f"  ✓ DuckDuckGo — {len(ddg_opps)} candidates")
        except Exception as e:
            self.errors.append(f"ddg: {e}")

        # Deduplicate by url
        dedup: Dict[str, Dict[str, Any]] = {}
        for o in all_opps:
            dedup[o['url']] = o

        for opp in dedup.values():
            try:
                if _insert_or_skip(cursor, opp):
                    new_found += 1
                    if calculate_opportunity_score(opp) >= 70:
                        high_value += 1
            except Exception as e:
                self.errors.append(f"insert: {opp.get('url')}: {e}")

        expire_stale(cursor)
        duration = time.time() - start
        _log_scan(cursor, sources_scanned, new_found, high_value, self.errors, duration)
        conn.commit()
        conn.close()

        result = {
            'sources_scanned': sources_scanned,
            'new_found': new_found,
            'high_value_found': high_value,
            'errors': self.errors,
            'duration_seconds': round(duration, 2),
            'scan_time': _now()
        }
        print(f"✅ Scan complete: {new_found} new, {high_value} high-value, {len(self.errors)} errors in {duration:.1f}s")
        return result


# ----------------------------------------------------------------------------
# CLI entry
# ----------------------------------------------------------------------------

if __name__ == '__main__':
    github_actions = '--github-actions' in sys.argv
    if github_actions:
        print("🤖 Running in GitHub Actions mode")
    engine = ScannerEngine()
    result = engine.run_full_scan()
    print(json.dumps(result, indent=2))
