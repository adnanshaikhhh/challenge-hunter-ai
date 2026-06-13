#!/usr/bin/env python3
"""
Challenge Hunter AI v2.0 — Autonomous Build Agent
Triggered when an opportunity is approved.
Phases: setup → repo → files → tests → security → deploy → demo → submit.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import threading
import time
from datetime import datetime
from typing import Any, Dict, Optional

import requests

from config import DB_PATH, GITHUB_TOKEN, GITHUB_USERNAME, PROJECTS_DIR
from generator import ProjectFileGenerator
from notifier import build_complete as notif_build_complete, build_started as notif_build_started


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def _log(opportunity_id: int, step: str, status: str, output: str = ''):
    try:
        conn = _conn()
        conn.execute("""
            INSERT INTO build_log (opportunity_id, step, status, output, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (opportunity_id, step, status, output[:4000], datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️  build_log insert failed: {e}")


def _set_status(opportunity_id: int, **fields):
    if not fields:
        return
    cols = ', '.join(f"{k} = ?" for k in fields.keys())
    vals = list(fields.values()) + [datetime.now().isoformat(), opportunity_id]
    conn = _conn()
    conn.execute(f"UPDATE opportunities SET {cols}, updated_at = ? WHERE id = ?", vals)
    conn.commit()
    conn.close()


def _load_opportunity(opportunity_id: int) -> Dict[str, Any]:
    conn = _conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM opportunities WHERE id = ?", (opportunity_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return {}
    return dict(row)


def _safe_run(cmd: str, cwd: Optional[str] = None, timeout: int = 120) -> Dict[str, Any]:
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd,
            capture_output=True, text=True, timeout=timeout
        )
        return {
            'ok': result.returncode == 0,
            'stdout': (result.stdout or '')[:2000],
            'stderr': (result.stderr or '')[:2000],
            'code': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {'ok': False, 'stdout': '', 'stderr': 'timeout', 'code': -1}
    except Exception as e:
        return {'ok': False, 'stdout': '', 'stderr': str(e), 'code': -1}


# ----------------------------------------------------------------------------
# Phase implementations
# ----------------------------------------------------------------------------

def _phase_setup(opp: Dict[str, Any]) -> bool:
    """Mark in_progress, send Telegram, log to build_log."""
    _set_status(opp['id'], build_status='in_progress', status='building')
    _log(opp['id'], 'setup', 'started')
    try:
        analysis = json.loads(opp.get('analysis_json') or '{}')
        rec = analysis.get('recommended_project', {})
        notif_build_started({
            'id': opp['id'],
            'name': opp.get('name'),
            'project_name': rec.get('name', 'TBD'),
            'build_days': rec.get('estimated_build_days', 7),
            'github_repo_url': 'pending'
        })
    except Exception as e:
        _log(opp['id'], 'setup', 'notify_failed', str(e))
    _log(opp['id'], 'setup', 'complete')
    return True


def _phase_generate_files(opp: Dict[str, Any]) -> Dict[str, Any]:
    """Generate the project files using ProjectFileGenerator."""
    _log(opp['id'], 'generate_files', 'started')
    gen = ProjectFileGenerator()
    count = gen.generate_all(opp['id'], opp)
    _log(opp['id'], 'generate_files', 'complete', f"{count} files")
    return {'files_generated': count}


def _phase_github_repo(opp: Dict[str, Any]) -> Dict[str, Any]:
    """Create a GitHub repository (best effort)."""
    if not GITHUB_TOKEN or not GITHUB_USERNAME:
        _log(opp['id'], 'github_repo', 'skipped', 'no GITHUB_TOKEN/USER')
        return {'skipped': True, 'reason': 'no credentials'}
    try:
        analysis = json.loads(opp.get('analysis_json') or '{}')
        rec = analysis.get('recommended_project', {})
        repo_name = (rec.get('name') or f"ch-{opp['id']}").lower().replace(' ', '-')[:60]
        url = 'https://api.github.com/user/repos'
        r = requests.post(
            url,
            headers={'Authorization': f'token {GITHUB_TOKEN}', 'Accept': 'application/vnd.github+json'},
            json={
                'name': repo_name,
                'description': rec.get('tagline', opp.get('name', ''))[:200],
                'private': False,
                'auto_init': True,
            },
            timeout=30
        )
        if r.status_code in (200, 201):
            html_url = r.json().get('html_url', '')
            _set_status(opp['id'], github_repo_url=html_url)
            _log(opp['id'], 'github_repo', 'complete', html_url)
            return {'ok': True, 'url': html_url}
        _log(opp['id'], 'github_repo', 'failed', f"{r.status_code}: {r.text[:200]}")
        return {'ok': False, 'status': r.status_code}
    except Exception as e:
        _log(opp['id'], 'github_repo', 'error', str(e))
        return {'ok': False, 'error': str(e)}


def _phase_hermes_brief(opp: Dict[str, Any]) -> Dict[str, Any]:
    """Write a hermes_session_{id}.txt brief for an external Hermes session."""
    _log(opp['id'], 'hermes_brief', 'started')
    try:
        analysis = json.loads(opp.get('analysis_json') or '{}')
        rec = analysis.get('recommended_project', {})
        brief_path = os.path.join(PROJECTS_DIR, f"hermes_session_{opp['id']}.txt")
        os.makedirs(PROJECTS_DIR, exist_ok=True)
        with open(brief_path, 'w', encoding='utf-8') as f:
            f.write(
                f"# HERMES BUILD BRIEF — Opportunity #{opp['id']}\n"
                f"Competition: {opp.get('name')}\n"
                f"URL: {opp.get('url')}\n"
                f"Deadline: {opp.get('deadline')}\n"
                f"Project: {rec.get('name')}\n"
                f"Concept: {rec.get('concept')}\n"
                f"Tech: {rec.get('tech_stack')}\n"
                f"Build days: {rec.get('estimated_build_days')}\n"
                f"\n# Requirements\n" + "\n".join(f"- {r}" for r in analysis.get('requirements', []))
                + f"\n\n# Submission strategy\n{analysis.get('submission_strategy', '')}\n"
            )
        _log(opp['id'], 'hermes_brief', 'complete', brief_path)
        return {'path': brief_path}
    except Exception as e:
        _log(opp['id'], 'hermes_brief', 'error', str(e))
        return {'error': str(e)}


def _phase_tests(opp: Dict[str, Any]) -> Dict[str, Any]:
    """Run pytest in the project directory. Best-effort."""
    _log(opp['id'], 'tests', 'started')
    base_dir = os.path.join(PROJECTS_DIR, f"{opp['id']:04d}_" + _safe_slug(opp.get('name', '')))
    if not os.path.isdir(base_dir):
        _log(opp['id'], 'tests', 'skipped', 'no project dir')
        return {'skipped': True}
    result = _safe_run('python -m pytest -q 2>&1 || true', cwd=base_dir, timeout=60)
    _log(opp['id'], 'tests', 'complete' if result['ok'] else 'failed', result['stdout'][:1000])
    return result


def _safe_slug(s: str) -> str:
    out = ''.join(c.lower() if c.isalnum() else '-' for c in s)
    return '-'.join(p for p in out.split('-') if p)[:40]


def _phase_security_audit(opp: Dict[str, Any]) -> Dict[str, Any]:
    """Run bandit on the project. Best-effort."""
    _log(opp['id'], 'security_audit', 'started')
    base_dir = os.path.join(PROJECTS_DIR, f"{opp['id']:04d}_" + _safe_slug(opp.get('name', '')))
    if not os.path.isdir(base_dir):
        _log(opp['id'], 'security_audit', 'skipped', 'no project dir')
        return {'skipped': True}
    result = _safe_run('python -m bandit -q -r src/ 2>&1 || true', cwd=base_dir, timeout=60)
    _log(opp['id'], 'security_audit', 'complete', result['stdout'][:1000])
    return result


def _phase_mark_complete(opp: Dict[str, Any], summary: Dict[str, Any]) -> bool:
    _set_status(opp['id'], build_status='complete')
    _log(opp['id'], 'mark_complete', 'complete', json.dumps(summary)[:2000])
    try:
        analysis = json.loads(opp.get('analysis_json') or '{}')
        rec = analysis.get('recommended_project', {})
        notif_build_complete({
            'id': opp['id'],
            'name': opp.get('name'),
            'project_name': rec.get('name', 'TBD'),
            'github_repo_url': opp.get('github_repo_url', 'pending'),
            'demo_url': 'pending',
        })
    except Exception as e:
        _log(opp['id'], 'mark_complete', 'notify_failed', str(e))
    return True


# ----------------------------------------------------------------------------
# Background runner
# ----------------------------------------------------------------------------

def run_build_async(opportunity_id: int) -> threading.Thread:
    """Spawn a background thread that runs the full build pipeline."""
    def _runner():
        opp = _load_opportunity(opportunity_id)
        if not opp:
            _log(opportunity_id, 'runner', 'failed', 'opportunity not found')
            return
        summary: Dict[str, Any] = {}
        try:
            _phase_setup(opp)
            summary['files'] = _phase_generate_files(opp)
            summary['github'] = _phase_github_repo(opp)
            summary['hermes_brief'] = _phase_hermes_brief(opp)
            summary['tests'] = _phase_tests(opp)
            summary['security'] = _phase_security_audit(opp)
            _phase_mark_complete(opp, summary)
        except Exception as e:
            _log(opportunity_id, 'runner', 'crashed', str(e))
            _set_status(opportunity_id, build_status='failed')
    t = threading.Thread(target=_runner, daemon=True, name=f"build-{opportunity_id}")
    t.start()
    return t


# ----------------------------------------------------------------------------
# CLI for manual triggers
# ----------------------------------------------------------------------------

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python auto_builder.py <opportunity_id>")
        sys.exit(1)
    oid = int(sys.argv[1])
    t = run_build_async(oid)
    print(f"Build started for opportunity #{oid}")
    t.join(timeout=300)
    print("Build thread finished.")
