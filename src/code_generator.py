#!/usr/bin/env python3
"""
Challenge Hunter AI v2.0 — AI Code Generator
Calls an LLM (OpenRouter by default — works with MiniMax, Claude, GPT-4, etc.)
to generate the actual project source code for an approved opportunity.

Uses the Hermes brief as the prompt, then writes all generated files to disk.
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from config import DB_PATH, PROJECTS_DIR


# =============================================================================
# Configuration
# =============================================================================

# OpenRouter supports MiniMax, Anthropic, OpenAI, etc. via one endpoint.
# You can also point at a custom OpenAI-compatible endpoint (e.g. your own
# MiniMax proxy, NVIDIA NIM, etc.) by setting OPENROUTER_BASE_URL.
# https://openrouter.ai/docs
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
# Default model: MiniMax M2.7 (cheap, fast, good enough for code gen)
# Swap to "anthropic/claude-3-5-sonnet" for higher quality if you have credits
OPENROUTER_MODEL = os.environ.get('OPENROUTER_MODEL', 'minimax/minimax-m2.7')
# Base URL — defaults to OpenRouter, but you can override for any
# OpenAI-compatible endpoint (custom MiniMax proxy, NVIDIA NIM, etc.)
OPENROUTER_BASE_URL = os.environ.get(
    'OPENROUTER_BASE_URL',
    'https://openrouter.ai/api/v1/chat/completions'
)
OPENROUTER_URL = OPENROUTER_BASE_URL
CODE_GEN_TIMEOUT = 300  # 5 min max per generation


# =============================================================================
# File extraction from LLM output
# =============================================================================

def extract_files_from_response(text: str) -> Dict[str, str]:
    """
    Parse the LLM's output and extract code files.
    Accepts these formats:
      1. ```language:path/to/file\n<code>\n```
      2. ```path/to/file\n<code>\n```
      3. ==== FILE: path/to/file ====\n<code>\n==== END ====
    """
    files = {}
    # Pattern 1: ```python:src/main.py
    pattern1 = re.compile(r'```(?:\w+)?:([^\n`]+)\n(.*?)```', re.DOTALL)
    for match in pattern1.finditer(text):
        path = match.group(1).strip()
        content = match.group(2).strip()
        if path and content and not path.startswith('http'):
            files[path] = content
    if files:
        return files
    # Pattern 2: bare ```lang then look for filename in first line
    pattern2 = re.compile(r'```(\w+)\n(.*?)```', re.DOTALL)
    for i, match in enumerate(pattern2.finditer(text)):
        lang = match.group(1).strip()
        content = match.group(2).strip()
        # Try to infer filename from surrounding context
        if not content:
            continue
        ext = {'python': '.py', 'javascript': '.js', 'typescript': '.ts',
               'html': '.html', 'css': '.css', 'json': '.json',
               'yaml': '.yml', 'markdown': '.md', 'bash': '.sh',
               'dockerfile': '.dockerfile'}.get(lang.lower(), '.txt')
        path = f"src/generated_file_{i+1}{ext}"
        files[path] = content
    return files


# =============================================================================
# Public API
# =============================================================================

def generate_code_from_brief(brief_text: str, model: Optional[str] = None,
                             project_name: str = 'project') -> Dict[str, Any]:
    """
    Call OpenRouter with the brief and get back source files.

    Returns:
        {
            'success': bool,
            'files': {path: content, ...},
            'model': model_used,
            'tokens': int,
            'error': str (if failed),
        }
    """
    if not OPENROUTER_API_KEY:
        return {
            'success': False,
            'error': 'OPENROUTER_API_KEY not set. Add it to your .env or Railway variables.',
            'files': {},
            'model': None,
            'tokens': 0
        }

    system_prompt = """You are an expert full-stack engineer. Given a project brief,
generate the COMPLETE source code for the project.

OUTPUT FORMAT — strictly follow this:
For each file, use this fenced block format:

```python:src/main.py
# complete file content
```

```html:frontend/index.html
<!doctype html>...
```

```css:frontend/style.css
body { ... }
```

```javascript:frontend/app.js
console.log('hello');
```

```markdown:README.md
# Project Title
...
```

```dockerfile:Dockerfile
FROM python:3.11-slim
...
```

```yaml:.github/workflows/deploy.yml
name: Deploy
...
```

```json:package.json
{ "name": "..." }
```

Rules:
- Output AT LEAST these files: README.md, src/main.py (or index.js), frontend/index.html,
  frontend/style.css, frontend/app.js, requirements.txt (or package.json), Dockerfile,
  .github/workflows/deploy.yml, tests/test_main.py
- Use the EXACT fence format `language:path` on the opening fence
- Code must be COMPLETE, runnable, production-quality
- No placeholders, no TODOs, no "[rest of code]"
- Include a brief 1-2 line comment header on each file
- Add docstrings to every Python function
- Make the UI beautiful and the backend solid
"""

    user_prompt = f"""Project brief:

{brief_text}

Generate the COMPLETE codebase for this project now. Output all files using the fence format specified.
"""

    body = {
        'model': model or OPENROUTER_MODEL,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ],
        'temperature': 0.3,
        'max_tokens': 16000,
    }

    headers = {
        'Authorization': f'Bearer {OPENROUTER_API_KEY}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://challenge-hunter-ai-production.up.railway.app',
        'X-Title': 'Challenge Hunter AI'
    }

    try:
        r = requests.post(OPENROUTER_URL, json=body, headers=headers, timeout=CODE_GEN_TIMEOUT)
        if r.status_code != 200:
            return {
                'success': False,
                'error': f'OpenRouter returned {r.status_code}: {r.text[:500]}',
                'files': {},
                'model': body['model'],
                'tokens': 0
            }
        result = r.json()
        content = result['choices'][0]['message']['content']
        usage = result.get('usage', {})
        tokens = usage.get('total_tokens', 0)

        files = extract_files_from_response(content)
        return {
            'success': True,
            'files': files,
            'model': body['model'],
            'tokens': tokens,
            'raw_response': content,
            'error': None
        }
    except requests.exceptions.Timeout:
        return {'success': False, 'error': f'Code gen timed out after {CODE_GEN_TIMEOUT}s',
                'files': {}, 'model': body['model'], 'tokens': 0}
    except Exception as e:
        return {'success': False, 'error': f'{type(e).__name__}: {e}',
                'files': {}, 'model': body['model'], 'tokens': 0}


def write_generated_files(opportunity_id: int, files: Dict[str, str],
                          project_name: str = 'project') -> Dict[str, Any]:
    """Write the LLM-generated files to a project folder + DB."""
    from config import PROJECTS_DIR
    # Create a clean project directory
    safe_name = re.sub(r'[^a-z0-9-]', '-', project_name.lower())[:40].strip('-')
    proj_dir = os.path.join(PROJECTS_DIR, f"{opportunity_id:04d}_{safe_name}_built")
    os.makedirs(proj_dir, exist_ok=True)

    written = []
    for relpath, content in files.items():
        # Skip paths that try to escape
        if '..' in relpath or relpath.startswith('/'):
            continue
        full = os.path.join(proj_dir, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, 'w', encoding='utf-8') as f:
            f.write(content)
        written.append(relpath)

    # Also save to DB as project_files
    try:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        for relpath, content in files.items():
            if '..' in relpath or relpath.startswith('/'):
                continue
            cursor.execute("""
                INSERT INTO project_files (opportunity_id, filename, content, file_type, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (opportunity_id, relpath, content, 'ai_generated', datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️  failed to persist files to DB: {e}")

    return {
        'project_dir': proj_dir,
        'files_written': written,
        'count': len(written)
    }


def build_project(opportunity_id: int) -> Dict[str, Any]:
    """
    Top-level: read the brief, call the LLM, write the files.
    Updates build_status and logs to build_log.
    """
    import sqlite3
    from config import PROJECTS_DIR
    from auto_builder import _log, _set_status

    # Load brief
    brief_path = os.path.join(PROJECTS_DIR, f"hermes_session_{opportunity_id}.txt")
    if not os.path.exists(brief_path):
        return {'success': False, 'error': f'Hermes brief not found at {brief_path}'}

    with open(brief_path, 'r', encoding='utf-8') as f:
        brief_text = f.read()

    # Load opportunity
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT name, analysis_json FROM opportunities WHERE id = ?", (opportunity_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return {'success': False, 'error': f'Opportunity {opportunity_id} not found'}

    # Update status
    _set_status(opportunity_id, build_status='in_progress')
    _log(opportunity_id, 'ai_build', 'started', f'Using model {OPENROUTER_MODEL}')

    # Extract project name from brief
    project_name = 'project'
    try:
        analysis = json.loads(row['analysis_json'] or '{}')
        rec = analysis.get('recommended_project', {})
        if rec.get('name'):
            project_name = rec['name']
    except Exception:
        pass

    # Call the LLM
    _log(opportunity_id, 'ai_build', 'calling_api', f'Model: {OPENROUTER_MODEL}')
    result = generate_code_from_brief(brief_text, project_name=project_name)

    if not result['success']:
        _log(opportunity_id, 'ai_build', 'failed', result.get('error', 'unknown')[:1000])
        _set_status(opportunity_id, build_status='failed')
        return result

    if not result['files']:
        _log(opportunity_id, 'ai_build', 'no_files',
             f'Model returned text but no parseable files. Tokens: {result["tokens"]}')
        _set_status(opportunity_id, build_status='failed')
        return {'success': False, 'error': 'LLM returned no parseable files',
                'raw': result.get('raw_response', '')[:2000]}

    # Write files to disk
    written = write_generated_files(opportunity_id, result['files'], project_name)

    # Log success
    _log(opportunity_id, 'ai_build', 'complete',
         f"Generated {written['count']} files using {result['model']} ({result['tokens']} tokens). "
         f"Project dir: {written['project_dir']}")

    _set_status(opportunity_id, build_status='complete', status='approved')

    return {
        'success': True,
        'project_dir': written['project_dir'],
        'files_generated': written['count'],
        'files': list(result['files'].keys()),
        'model': result['model'],
        'tokens': result['tokens'],
    }


# =============================================================================
# CLI
# =============================================================================

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python code_generator.py <opportunity_id>")
        sys.exit(1)
    opp_id = int(sys.argv[1])
    result = build_project(opp_id)
    print(json.dumps(result, indent=2, default=str)[:2000])
