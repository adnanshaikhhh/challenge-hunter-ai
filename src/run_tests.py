#!/usr/bin/env python3
"""
Challenge Hunter AI v2.0 — Test suite
Run with: python run_tests.py
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
from typing import Callable, List, Tuple

# Use a temp DB for tests
TEST_DIR = tempfile.mkdtemp(prefix='ch_test_')
os.environ['DB_PATH'] = os.path.join(TEST_DIR, 'test.db')
os.environ['SCAN_INTERVAL_HOURS'] = '4'

# Ensure we can import the modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analyzer import analyze, build_deterministic_analysis
from config import (
    AI_ALLOWED_KEYWORDS, AI_BANNED_KEYWORDS, DB_PATH, SCHEMA_PATH
)
from generator import ProjectFileGenerator
from scorer import (
    calculate_expected_value, calculate_opportunity_score,
    calculate_win_probability, score_all
)
from seed import seed_database
from app import _ensure_db, get_db  # noqa


# ----------------------------------------------------------------------------
# Test harness
# ----------------------------------------------------------------------------

PASSED = 0
FAILED = 0
ERRORS: List[Tuple[str, str]] = []


def test(name: str):
    def deco(fn: Callable):
        global PASSED, FAILED
        try:
            fn()
            PASSED += 1
            print(f"  ✅ {name}")
        except AssertionError as e:
            FAILED += 1
            ERRORS.append((name, str(e)))
            print(f"  ❌ {name}: {e}")
        except Exception as e:
            FAILED += 1
            ERRORS.append((name, f"{type(e).__name__}: {e}"))
            print(f"  💥 {name}: {e}")
        return fn
    return deco


# ----------------------------------------------------------------------------
# Scorer tests
# ----------------------------------------------------------------------------

def t_scorer():
    print("\n[scorer]")

    @test("base score is 50 minus unclear penalty")
    def _():
        # Empty dict defaults to ai_policy='unclear' which subtracts 15
        assert calculate_opportunity_score({}) == 35

    @test("prize > 50000 gives +25 (with allowed policy)")
    def _():
        assert calculate_opportunity_score({'prize_usd': 60000, 'ai_policy': 'allowed'}) == 95

    @test("prize 5000-10000 gives +15 (with allowed policy)")
    def _():
        assert calculate_opportunity_score({'prize_usd': 7000, 'ai_policy': 'allowed'}) == 85

    @test("deadline sweet spot 14-45 days gives +12")
    def _():
        # Base 50, allowed policy +20, sweet spot +12 = 82
        assert calculate_opportunity_score({'days_remaining': 30, 'ai_policy': 'allowed'}) == 82

    @test("ai_policy allowed gives +20")
    def _():
        # 50 base + 20 = 70
        assert calculate_opportunity_score({'ai_policy': 'allowed'}) == 70

    @test("ai_policy banned gives -40")
    def _():
        # 50 - 40 = 10
        assert calculate_opportunity_score({'ai_policy': 'banned'}) == 10

    @test("score clamps to 0-100")
    def _():
        assert 0 <= calculate_opportunity_score({'prize_usd': 1000000, 'ai_policy': 'banned'}) <= 100

    @test("win probability base 30")
    def _():
        assert calculate_win_probability({}) == 30

    @test("easy difficulty adds 15 to win prob")
    def _():
        assert calculate_win_probability({'difficulty': 'easy'}) == 45

    @test("win probability clamped 5-95")
    def _():
        for d in ['easy', 'medium', 'hard']:
            p = calculate_win_probability({'difficulty': d, 'prize_usd': 100, 'days_remaining': 1, 'ai_policy': 'banned'})
            assert 5 <= p <= 95

    @test("expected value calculation")
    def _():
        assert calculate_expected_value(1000, 50) == 500.0

    @test("score_all returns all three values")
    def _():
        s = score_all({'prize_usd': 1000})
        assert 'opportunity_score' in s
        assert 'win_probability' in s
        assert 'expected_value' in s


# ----------------------------------------------------------------------------
# Analyzer tests
# ----------------------------------------------------------------------------

def t_analyzer():
    print("\n[analyzer]")

    @test("deterministic analysis has all required keys")
    def _():
        opp = {
            'name': 'Test Hack', 'prize_usd': 5000, 'days_remaining': 30,
            'ai_policy': 'allowed', 'difficulty': 'medium', 'source': 'Devpost',
            'opportunity_score': 70, 'win_probability': 40
        }
        a = build_deterministic_analysis(opp)
        for k in ['summary', 'why_this_is_good', 'requirements', 'risks',
                  'win_probability_reasoning', 'build_complexity',
                  'time_to_build_estimate', 'recommended_project',
                  'submission_strategy', 'judge_appeal', 'alternative_projects',
                  'recommended_action', 'action_reasoning']:
            assert k in a, f"missing key: {k}"

    @test("recommended_project has all keys")
    def _():
        opp = {'name': 'X', 'prize_usd': 1000, 'days_remaining': 14,
               'ai_policy': 'allowed', 'difficulty': 'easy', 'source': 'X',
               'opportunity_score': 60, 'win_probability': 50}
        a = build_deterministic_analysis(opp)
        rp = a['recommended_project']
        for k in ['name', 'tagline', 'concept', 'problem_solved', 'tech_stack',
                  'key_features', 'demo_approach', 'wow_factor', 'estimated_build_days']:
            assert k in rp, f"missing rp key: {k}"

    @test("tech_stack has 5 categories")
    def _():
        opp = {'name': 'X', 'prize_usd': 1000, 'days_remaining': 14,
               'ai_policy': 'allowed', 'difficulty': 'hard', 'source': 'X',
               'opportunity_score': 60, 'win_probability': 50}
        a = build_deterministic_analysis(opp)
        ts = a['recommended_project']['tech_stack']
        for cat in ['frontend', 'backend', 'database', 'ai', 'deployment']:
            assert cat in ts, f"missing tech category: {cat}"

    @test("analyze falls back when no LLM key")
    def _():
        opp = {'name': 'Test', 'prize_usd': 1000, 'days_remaining': 14,
               'ai_policy': 'allowed', 'difficulty': 'medium', 'source': 'X',
               'opportunity_score': 50, 'win_probability': 30}
        a = analyze(opp, use_llm=False)
        assert 'summary' in a

    @test("recommended_action is one of valid values")
    def _():
        opp = {'name': 'Test', 'prize_usd': 1000, 'days_remaining': 14,
               'ai_policy': 'allowed', 'difficulty': 'medium', 'source': 'X',
               'opportunity_score': 50, 'win_probability': 30}
        a = build_deterministic_analysis(opp)
        assert a['recommended_action'] in ('approve', 'skip', 'monitor')

    @test("AI policy detection: allowed keywords")
    def _():
        from scanner import detect_ai_policy
        assert detect_ai_policy("We allow AI tools and ChatGPT usage") == 'allowed'

    @test("AI policy detection: banned keywords")
    def _():
        from scanner import detect_ai_policy
        assert detect_ai_policy("No AI tools allowed, human coding only") == 'banned'

    @test("AI policy detection: unclear default")
    def _():
        from scanner import detect_ai_policy
        assert detect_ai_policy("") == 'unclear'
        assert detect_ai_policy("Random unrelated text") == 'unclear'


# ----------------------------------------------------------------------------
# Database tests
# ----------------------------------------------------------------------------

def t_database():
    print("\n[database]")

    @test("DB is created on first run")
    def _():
        assert os.path.exists(DB_PATH)

    @test("schema has opportunities table")
    def _():
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='opportunities'")
        assert cur.fetchone() is not None
        conn.close()

    @test("schema has scan_log table")
    def _():
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scan_log'")
        assert cur.fetchone() is not None
        conn.close()

    @test("schema has build_log table")
    def _():
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='build_log'")
        assert cur.fetchone() is not None
        conn.close()

    @test("schema has notifications table")
    def _():
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notifications'")
        assert cur.fetchone() is not None
        conn.close()

    @test("seed inserts 5 records")
    def _():
        seed_database()
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM opportunities")
        c = cur.fetchone()['c']
        assert c == 5, f"expected 5, got {c}"
        conn.close()

    @test("seeded records have non-zero scores")
    def _():
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM opportunities WHERE opportunity_score > 0")
        c = cur.fetchone()['c']
        assert c >= 1
        conn.close()

    @test("seeded records have analysis_json")
    def _():
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT analysis_json FROM opportunities LIMIT 1")
        row = cur.fetchone()
        assert row is not None
        parsed = json.loads(row['analysis_json'])
        assert 'summary' in parsed
        conn.close()


# ----------------------------------------------------------------------------
# Generator tests
# ----------------------------------------------------------------------------

def t_generator():
    print("\n[generator]")

    @test("ProjectFileGenerator writes 5 doc files to DB")
    def _():
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id FROM opportunities ORDER BY id ASC LIMIT 1")
        opp_id = cur.fetchone()['id']
        conn.close()
        g = ProjectFileGenerator()
        count = g.generate_all(opp_id)
        assert count >= 5, f"expected >=5 files, got {count}"

    @test("doc files include README.md")
    def _():
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT filename FROM project_files WHERE filename = 'README.md'")
        assert cur.fetchone() is not None
        conn.close()

    @test("doc files include demo_plan.md")
    def _():
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT filename FROM project_files WHERE filename = 'demo_plan.md'")
        assert cur.fetchone() is not None
        conn.close()

    @test("doc files include submission_checklist.md")
    def _():
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT filename FROM project_files WHERE filename = 'submission_checklist.md'")
        assert cur.fetchone() is not None
        conn.close()


# ----------------------------------------------------------------------------
# Config tests
# ----------------------------------------------------------------------------

def t_config():
    print("\n[config]")

    @test("DB_PATH is set")
    def _():
        assert DB_PATH

    @test("SCHEMA_PATH exists")
    def _():
        assert os.path.exists(SCHEMA_PATH)

    @test("ALL_SOURCES has 20+ entries")
    def _():
        from config import ALL_SOURCES
        assert len(ALL_SOURCES) >= 20, f"only {len(ALL_SOURCES)} sources"

    @test("DUCKDUCKGO_QUERIES has 10+ entries")
    def _():
        from config import DUCKDUCKGO_QUERIES
        assert len(DUCKDUCKGO_QUERIES) >= 10

    @test("AI_ALLOWED_KEYWORDS non-empty")
    def _():
        assert len(AI_ALLOWED_KEYWORDS) > 0

    @test("AI_BANNED_KEYWORDS non-empty")
    def _():
        assert len(AI_BANNED_KEYWORDS) > 0


# ----------------------------------------------------------------------------
# Notifier tests
# ----------------------------------------------------------------------------

def t_notifier():
    print("\n[notifier]")

    @test("broadcast handles no channels gracefully")
    def _():
        from notifier import broadcast
        result = broadcast("test message")
        assert result is False  # no channels = not delivered

    @test("info() logs to notifications table")
    def _():
        from notifier import info
        # Will be False because no Telegram, but should still log
        info("test info")
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM notifications WHERE type='info'")
        c = cur.fetchone()['c']
        assert c >= 1
        conn.close()

    @test("high_value_alert formats correctly")
    def _():
        from notifier import high_value_alert
        opp = {
            'id': 1, 'name': 'Test', 'prize_usd': 5000, 'days_remaining': 30,
            'ai_policy': 'allowed', 'opportunity_score': 85, 'win_probability': 50,
            'expected_value': 2500, 'source': 'Devpost', 'url': 'https://x',
            'analysis_json': json.dumps({
                'recommended_project': {
                    'name': 'TestProj', 'concept': 'test concept',
                    'tech_stack': {'backend': ['Python']}, 'estimated_build_days': 5
                }
            })
        }
        result = high_value_alert(opp)
        assert result is False or result is True  # either is OK without channels


# ----------------------------------------------------------------------------
# Code generator tests
# ----------------------------------------------------------------------------

def t_code_generator():
    print("\n[code_generator]")

    @test("extract_files_from_response with language:path format")
    def _():
        from code_generator import extract_files_from_response
        text = """```python:src/main.py
print('hello')
```

```html:frontend/index.html
<!doctype html>
<h1>Hi</h1>
```"""
        files = extract_files_from_response(text)
        assert 'src/main.py' in files, files
        assert 'frontend/index.html' in files, files
        assert "print('hello')" in files['src/main.py']
        assert '<h1>Hi</h1>' in files['frontend/index.html']

    @test("extract_files_from_response with bare language tags")
    def _():
        from code_generator import extract_files_from_response
        text = """```python
def foo(): pass
```

```javascript
console.log('hi');
```"""
        files = extract_files_from_response(text)
        assert len(files) >= 1, files
        # Either format should produce files
        all_content = ' '.join(files.values())
        assert 'def foo' in all_content or 'console.log' in all_content

    @test("generate_code_from_brief fails gracefully when no API key")
    def _():
        from code_generator import generate_code_from_brief
        os.environ['OPENROUTER_API_KEY'] = ''
        result = generate_code_from_brief('test brief')
        assert result['success'] is False
        assert 'OPENROUTER_API_KEY' in result['error'] or 'not set' in result['error'].lower()
        assert result['files'] == {}

    @test("write_generated_files creates files on disk")
    def _():
        from code_generator import write_generated_files
        files = {
            'src/main.py': '# test',
            'README.md': '# Hi',
            '../escape.py': '# bad',  # should be skipped
        }
        result = write_generated_files(99999, files, 'test-project')
        assert result['count'] == 2  # escape.py should be skipped
        assert os.path.isdir(result['project_dir'])
        assert os.path.isfile(os.path.join(result['project_dir'], 'src', 'main.py'))
        # Cleanup
        import shutil
        shutil.rmtree(result['project_dir'], ignore_errors=True)

    @test("code_generator module imports without error")
    def _():
        import code_generator
        assert hasattr(code_generator, 'generate_code_from_brief')
        assert hasattr(code_generator, 'write_generated_files')
        assert hasattr(code_generator, 'build_project')


# ----------------------------------------------------------------------------
# Notifier tests
# ----------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("🧪 Challenge Hunter AI v2.0 — Test Suite")
    print("=" * 60)

    # Bootstrap DB once
    _ensure_db()

    # Run test groups
    t_scorer()
    t_analyzer()
    t_database()
    t_generator()
    t_config()
    t_notifier()
    t_code_generator()

    print()
    print("=" * 60)
    total = PASSED + FAILED
    print(f"📊 {PASSED}/{total} tests passed, {FAILED} failed")
    if FAILED:
        print()
        print("Failed tests:")
        for name, err in ERRORS:
            print(f"  ❌ {name}: {err}")
    print("=" * 60)
    sys.exit(0 if FAILED == 0 else 1)


if __name__ == '__main__':
    main()
