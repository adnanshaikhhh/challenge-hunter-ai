#!/usr/bin/env python3
"""
Challenge Hunter AI v2.2 — Autonomous Hermes Build Loop
A new Hermes session (or this autonomous agent) can:
  1. Generate the initial codebase
  2. Install dependencies
  3. Run tests; collect failures
  4. Auto-fix by calling LLM with the error context (up to N attempts)
  5. Run security audit
  6. Commit to GitHub
  7. Deploy to Railway
  8. Generate demo video
  9. Generate submission package
  10. Mark complete

The dashboard's 🤖 Build button triggers just steps 1-2.
The "📋 Open in Hermes" button triggers the full pipeline.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from config import DB_PATH, GITHUB_TOKEN, GITHUB_USERNAME, PROJECTS_DIR
from llm import default_client


# =============================================================================
# Configuration
# =============================================================================

HERMES_MAX_FIX_ATTEMPTS = int(os.environ.get('HERMES_MAX_FIX_ATTEMPTS', '3'))
HERMES_TEST_TIMEOUT = int(os.environ.get('HERMES_TEST_TIMEOUT', '120'))
HERMES_INSTALL_TIMEOUT = int(os.environ.get('HERMES_INSTALL_TIMEOUT', '300'))


# =============================================================================
# Helpers
# =============================================================================

def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def _log(opportunity_id: int, step: str, status: str, output: str = '') -> None:
    try:
        conn = _conn()
        conn.execute("""
            INSERT INTO build_log (opportunity_id, step, status, output, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (opportunity_id, step, status, output[:4000], datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️  log failed: {e}")


def _set_status(opportunity_id: int, **fields) -> None:
    if not fields:
        return
    cols = ', '.join(f"{k} = ?" for k in fields.keys())
    vals = list(fields.values()) + [datetime.now().isoformat(), opportunity_id]
    conn = _conn()
    conn.execute(f"UPDATE opportunities SET {cols}, updated_at = ? WHERE id = ?", vals)
    conn.commit()
    conn.close()


def _run(cmd: str, cwd: Optional[str] = None, timeout: int = 120) -> Dict[str, Any]:
    """Run a shell command and capture output. Safe (no shell=True)."""
    import shlex
    cmd_list = shlex.split(cmd) if isinstance(cmd, str) else list(cmd)
    try:
        result = subprocess.run(
            cmd_list, shell=False, cwd=cwd,
            capture_output=True, text=True, timeout=timeout
        )
        return {
            'ok': result.returncode == 0,
            'stdout': (result.stdout or '')[:3000],
            'stderr': (result.stderr or '')[:3000],
            'code': result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {'ok': False, 'stdout': '', 'stderr': f'timeout after {timeout}s', 'code': -1}
    except Exception as e:
        return {'ok': False, 'stdout': '', 'stderr': f'{type(e).__name__}: {e}', 'code': -1}


# =============================================================================
# Phase 1: Initial code generation (uses code_generator)
# =============================================================================

def _phase_generate(opportunity_id: int) -> Dict[str, Any]:
    from code_generator import build_project
    return build_project(opportunity_id)


# =============================================================================
# Phase 2: Install dependencies
# =============================================================================

def _phase_install(opportunity_id: int) -> Dict[str, Any]:
    """Install Python deps via pip or Node deps via npm. Skipped if tool not available."""
    _log(opportunity_id, 'hermes_install', 'started')
    base = _find_built_dir(opportunity_id)
    if not base:
        return {'ok': False, 'error': 'no_built_dir'}

    if os.path.exists(os.path.join(base, 'requirements.txt')):
        pip_check = _run(['pip', '--version'], timeout=5)
        if not pip_check.get('ok'):
            _log(opportunity_id, 'hermes_install', 'skipped', 'pip not installed')
            return {'ok': True, 'skipped': 'pip not installed'}
        result = _run(['pip', 'install', '-q', '-r', 'requirements.txt'],
                      cwd=base, timeout=HERMES_INSTALL_TIMEOUT)
        _log(opportunity_id, 'hermes_install', 'pip',
             f"ok={result['ok']} stderr={result['stderr'][:500]}")
        return {'ok': result['ok'], 'tool': 'pip', 'result': result}
    elif os.path.exists(os.path.join(base, 'package.json')):
        npm_check = _run(['npm', '--version'], timeout=5)
        if not npm_check.get('ok'):
            _log(opportunity_id, 'hermes_install', 'skipped', 'npm not installed')
            return {'ok': True, 'skipped': 'npm not installed'}
        result = _run(['npm', 'install', '--silent'],
                      cwd=base, timeout=HERMES_INSTALL_TIMEOUT)
        _log(opportunity_id, 'hermes_install', 'npm',
             f"ok={result['ok']} stderr={result['stderr'][:500]}")
        return {'ok': result['ok'], 'tool': 'npm', 'result': result}
    else:
        return {'ok': True, 'skipped': 'no_deps_file'}


# =============================================================================
# Phase 3: Run tests
# =============================================================================

def _phase_test(opp: Dict[str, Any]) -> Dict[str, Any]:
    """Run pytest in the project directory. Best-effort. Skipped if pytest not installed."""
    _log(opp['id'], 'hermes_test', 'started')
    base = _find_built_dir(opp['id'])
    if not base:
        return {'ok': False, 'error': 'no_built_dir'}

    if os.path.exists(os.path.join(base, 'tests')) or os.path.exists(os.path.join(base, 'test_*.py')):
        # Check if pytest is available
        try:
            import pytest
        except ImportError:
            _log(opp['id'], 'hermes_test', 'skipped', 'pytest not installed')
            return {'ok': True, 'skipped': 'pytest not installed'}

        result = _run(['python', '-m', 'pytest', '-x', '--tb=short', '-q'],
                      cwd=base, timeout=HERMES_TEST_TIMEOUT)
        _log(opp['id'], 'hermes_test', 'pytest',
             f"ok={result['ok']} stdout={result['stdout'][:500]} stderr={result['stderr'][:500]}")
        return {
            'ok': result['ok'],
            'stdout': result['stdout'],
            'stderr': result['stderr'],
            'code': result['code'],
        }
    elif os.path.exists(os.path.join(base, 'package.json')):
        # Check if npm is available
        npm_check = _run(['npm', '--version'], timeout=5)
        if not npm_check.get('ok'):
            _log(opp['id'], 'hermes_test', 'skipped', 'npm not installed')
            return {'ok': True, 'skipped': 'npm not installed'}

        result = _run(['npm', 'test', '--silent'], cwd=base, timeout=HERMES_TEST_TIMEOUT)
        _log(opp['id'], 'hermes_test', 'npm',
             f"ok={result['ok']} stderr={result['stderr'][:500]}")
        return {
            'ok': result['ok'],
            'stdout': result['stdout'],
            'stderr': result['stderr'],
        }
    return {'ok': True, 'skipped': 'no_tests'}


# =============================================================================
# Phase 4: Auto-fix using LLM
# =============================================================================

def _phase_fix(opportunity_id: int, test_output: str, attempt: int) -> Dict[str, Any]:
    """Use the LLM to fix test failures or runtime errors."""
    _log(opportunity_id, 'hermes_fix', f'started attempt {attempt}')

    base = _find_built_dir(opportunity_id)
    if not base:
        return {'ok': False, 'error': 'no_built_dir'}

    # Find files in the project
    files = {}
    for root, _, filenames in os.walk(base):
        if '.git' in root or 'node_modules' in root or '__pycache__' in root:
            continue
        for fn in filenames:
            if fn.endswith(('.py', '.js', '.ts', '.json', '.md', '.yml', '.yaml')):
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, base)
                try:
                    with open(full, 'r', encoding='utf-8', errors='ignore') as f:
                        files[rel] = f.read()[:4000]  # truncate
                except Exception:
                    pass

    # Build a fix prompt
    file_summary = '\n'.join(f"--- {p} ---\n{c[:1500]}\n" for p, c in list(files.items())[:15])
    system = """You are an expert debugger. Given a project, a test failure,
and the source files, output ONLY the files that need to change.
Use this fence format:

```python:path/to/file.py
# corrected file content
```

Be conservative — only modify what's necessary. Preserve all other code exactly.
Output 0 files (just an empty array `[]`) if the issue is in unfixable infrastructure."""

    user_prompt = f"""Test output / error:
{test_output[:3000]}

Project files (truncated):
{file_summary}

Identify the minimal fix. Output the corrected file(s) using the fence format."""

    result = default_client.complete(
        messages=[{'role': 'system', 'content': system},
                  {'role': 'user', 'content': user_prompt}],
        temperature=0.1,
        max_tokens=8000,
        timeout=180
    )

    if not result.get('success'):
        _log(opportunity_id, 'hermes_fix', 'failed', result.get('error', ''))
        return {'ok': False, 'error': 'llm_failed'}

    content = result['content']
    # Parse fixed files
    fixed = _parse_fenced_files(content)
    if not fixed:
        _log(opportunity_id, 'hermes_fix', 'no_changes', content[:500])
        return {'ok': True, 'fixed': 0, 'note': 'no_files_changed'}

    # Apply fixes
    applied = 0
    for path, new_content in fixed.items():
        full = os.path.join(base, path)
        # Path safety
        if '..' in path or path.startswith('/'):
            continue
        try:
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, 'w', encoding='utf-8') as f:
                f.write(new_content)
            applied += 1
        except Exception as e:
            _log(opportunity_id, 'hermes_fix', f'write_error {path}', str(e))

    _log(opportunity_id, 'hermes_fix', f'applied {applied} files', str(list(fixed.keys()))[:500])
    return {'ok': True, 'fixed': applied}


def _parse_fenced_files(text: str) -> Dict[str, str]:
    """Extract files from LLM response in `lang:path\ncontent` format."""
    files = {}
    pattern = re.compile(r'```(\w+):([^\n`]+)\n(.*?)```', re.DOTALL)
    for m in pattern.finditer(text):
        path = m.group(2).strip()
        content = m.group(3).strip()
        if path and content and not path.startswith('http') and '..' not in path:
            files[path] = content
    return files


# =============================================================================
# Phase 5: Security audit (bandit)
# =============================================================================

def _phase_security(opportunity_id: int) -> Dict[str, Any]:
    _log(opportunity_id, 'hermes_security', 'started')
    base = _find_built_dir(opportunity_id)
    if not base:
        return {'ok': False, 'error': 'no_built_dir'}

    # Check if bandit is installed
    bandit_check = _run(['python', '-m', 'bandit', '--version'], timeout=5)
    if not bandit_check.get('ok'):
        _log(opportunity_id, 'hermes_security', 'skipped', 'bandit not installed')
        return {'ok': True, 'skipped': 'bandit not installed'}

    result = _run(['python', '-m', 'bandit', '-q', '-r', '.'],
                  cwd=base, timeout=60)
    issues = result['stdout'].count('Issue:')
    _log(opportunity_id, 'hermes_security', f'{issues} issues',
         result['stdout'][:1500])
    return {
        'ok': result['ok'] or issues == 0,
        'issue_count': issues,
        'output': result['stdout'][:2000]
    }


# =============================================================================
# Phase 6: Commit to GitHub
# =============================================================================

def _phase_commit(opportunity_id: int, github_url: Optional[str] = None) -> Dict[str, Any]:
    """Commit + push to GitHub via API (no git binary required). Returns the repo URL."""
    base = _find_built_dir(opportunity_id)
    if not base:
        return {'ok': False, 'error': 'no_built_dir'}

    # Get project name from opportunity
    conn = _conn()
    cursor = conn.cursor()
    cursor.execute("SELECT name, analysis_json FROM opportunities WHERE id = ?", (opportunity_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return {'ok': False, 'error': 'opp_not_found'}

    project_name = ''
    try:
        analysis = json.loads(row['analysis_json'] or '{}')
        rec = analysis.get('recommended_project', {})
        project_name = (rec.get('name') or f"ch-{opportunity_id}").lower().replace(' ', '-')[:50]
    except Exception:
        project_name = f"ch-{opportunity_id}"

    # Use the new git-free GitHub push
    if GITHUB_TOKEN and GITHUB_USERNAME:
        from deployer import push_to_github
        url = push_to_github(base, project_name)
        if url:
            _set_status(opportunity_id, github_repo_url=url)
            _log(opportunity_id, 'hermes_commit', 'github_pushed', url)
            return {'ok': True, 'github_url': url, 'project_name': project_name}

    _log(opportunity_id, 'hermes_commit', 'skipped', 'no GITHUB_TOKEN/USER')
    return {'ok': False, 'error': 'no_github_credentials'}


# =============================================================================
# Phase 7: Deploy to Railway
# =============================================================================

def _phase_deploy(opportunity_id: int) -> Dict[str, Any]:
    from deployer import deploy_project
    return deploy_project(opportunity_id)


# =============================================================================
# Phase 8: Demo video
# =============================================================================

def _phase_video(opportunity_id: int) -> Dict[str, Any]:
    from video_gen import generate_demo_video
    return generate_demo_video(opportunity_id)


# =============================================================================
# Phase 9: Submission package
# =============================================================================

def _phase_submission(opportunity_id: int) -> Dict[str, Any]:
    from submitter import generate_submission_package
    return generate_submission_package(opportunity_id)


# =============================================================================
# Helpers
# =============================================================================

def _find_built_dir(opportunity_id: int) -> Optional[str]:
    base = PROJECTS_DIR
    if not os.path.isdir(base):
        return None
    candidates = []
    for d in os.listdir(base):
        full = os.path.join(base, d)
        if (os.path.isdir(full) and d.startswith(f"{opportunity_id:04d}_")
                and d.endswith('_built')):
            candidates.append(full)
    if not candidates:
        return None
    return max(candidates, key=os.path.getmtime)


# =============================================================================
# MAIN ORCHESTRATOR — Full Hermes Pipeline
# =============================================================================

def run_hermes_pipeline(opportunity_id: int) -> Dict[str, Any]:
    """
    Run the full autonomous Hermes pipeline:
      generate → install → test → fix (loop) → security → commit → deploy → video → submission

    Each phase logs to build_log. Returns a summary dict.
    """
    started = time.time()
    results = {}

    # Phase 1: Generate
    _set_status(opportunity_id, build_status='in_progress', status='approved')
    _log(opportunity_id, 'hermes_pipeline', 'started')
    r = _phase_generate(opportunity_id)
    results['generate'] = r
    if not r.get('success'):
        _log(opportunity_id, 'hermes_pipeline', 'failed_at_generate', str(r)[:500])
        return {'success': False, 'failed_at': 'generate', 'detail': r}

    # Phase 2: Install deps
    r = _phase_install(opportunity_id)
    results['install'] = {'ok': r.get('ok')}

    # Phase 3+4: Test and fix loop
    test_result = _phase_test(opportunity_id)
    results['test'] = test_result
    fix_attempts = 0
    while not test_result.get('ok') and fix_attempts < HERMES_MAX_FIX_ATTEMPTS:
        fix_attempts += 1
        _log(opportunity_id, 'hermes_loop', f'fix attempt {fix_attempts}')
        fix_result = _phase_fix(opportunity_id,
                                test_result.get('stderr', '') + test_result.get('stdout', ''),
                                fix_attempts)
        results[f'fix_{fix_attempts}'] = fix_result
        if not fix_result.get('ok'):
            break
        # Re-run tests
        test_result = _phase_test(opportunity_id)
        results[f'test_after_fix_{fix_attempts}'] = test_result
        if test_result.get('ok'):
            break

    # Phase 5: Security
    r = _phase_security(opportunity_id)
    results['security'] = r

    # Phase 6: Commit
    r = _phase_commit(opportunity_id)
    results['commit'] = r

    # Phase 7: Deploy
    r = _phase_deploy(opportunity_id)
    results['deploy'] = r

    # Phase 8: Video
    r = _phase_video(opportunity_id)
    results['video'] = {'success': r.get('success'), 'file_path': r.get('file_path')}

    # Phase 9: Submission
    r = _phase_submission(opportunity_id)
    results['submission'] = {'success': r.get('success')}

    # Mark complete
    _set_status(opportunity_id, build_status='complete', status='approved')
    duration = round(time.time() - started, 1)
    _log(opportunity_id, 'hermes_pipeline', f'complete in {duration}s')

    return {
        'success': True,
        'duration_seconds': duration,
        'fix_attempts': fix_attempts,
        'phases': results,
        'github_url': results.get('commit', {}).get('github_url'),
        'deploy_url': results.get('deploy', {}).get('url') or results.get('deploy', {}).get('railway_dashboard'),
        'video_path': results.get('video', {}).get('file_path'),
    }


# =============================================================================
# Background runner
# =============================================================================

def run_hermes_async(opportunity_id: int) -> Dict[str, Any]:
    """Spawn the Hermes pipeline in a background thread."""
    import threading
    def _bg():
        try:
            result = run_hermes_pipeline(opportunity_id)
            print(f"🤖 Hermes #{opportunity_id} complete: {result.get('success')}, "
                  f"{result.get('duration_seconds', 0)}s, fix={result.get('fix_attempts', 0)}")
        except Exception as e:
            print(f"❌ Hermes #{opportunity_id} crashed: {e}")
            _log(opportunity_id, 'hermes_pipeline', 'crashed', str(e))
            _set_status(opportunity_id, build_status='failed')

    t = threading.Thread(target=_bg, daemon=True, name=f"hermes-{opportunity_id}")
    t.start()
    return {
        'triggered': True,
        'message': f'Hermes pipeline started for #{opportunity_id}. This runs the full build loop (5-30 min depending on test fixes needed).',
        'opportunity_id': opportunity_id,
        'status_url': f'/api/hermes/{opportunity_id}/status',
    }


def get_hermes_status(opportunity_id: int) -> Dict[str, Any]:
    """Get latest build_log entries for the pipeline."""
    conn = _conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT step, status, output, timestamp FROM build_log
        WHERE opportunity_id = ? AND step LIKE 'hermes%' OR step = 'ai_build'
        ORDER BY id DESC LIMIT 30
    """, (opportunity_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    cursor.execute("""
        SELECT build_status, status, github_repo_url FROM opportunities
        WHERE id = ?
    """, (opportunity_id,))
    opp = dict(cursor.fetchone() or {})
    conn.close()
    return {
        'opportunity': opp,
        'log': rows[::-1],  # chronological
        'running': opp.get('build_status') == 'in_progress',
    }


# =============================================================================
# CLI
# =============================================================================

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python hermes.py <opportunity_id>")
        sys.exit(1)
    opp_id = int(sys.argv[1])
    result = run_hermes_pipeline(opp_id)
    print(json.dumps(result, indent=2, default=str)[:2000])
