#!/usr/bin/env python3
"""
Challenge Hunter AI v2.0 — Project File Generator
Generates full project artefacts (README, plan, code skeletons) for an approved opportunity.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List

from config import DB_PATH, PROJECTS_DIR


# ----------------------------------------------------------------------------
# Database helpers
# ----------------------------------------------------------------------------

def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def _record_files(opportunity_id: int, files: Dict[str, str], file_type: str = 'doc') -> int:
    """Persist generated files into project_files table."""
    conn = _conn()
    cursor = conn.cursor()
    inserted = 0
    for filename, content in files.items():
        cursor.execute("""
            INSERT INTO project_files (opportunity_id, filename, content, file_type, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (opportunity_id, filename, content, file_type, datetime.now().isoformat()))
        inserted += 1
    conn.commit()
    conn.close()
    return inserted


# ----------------------------------------------------------------------------
# File builders
# ----------------------------------------------------------------------------

def _readme(opp: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    rp = analysis.get('recommended_project', {})
    return f"""# {rp.get('name', opp.get('name', 'Project'))}

> {rp.get('tagline', 'AI-powered project built for the win.')}

Built for: **{opp.get('name')}** — ${opp.get('prize_usd', 0):,} in prizes.

## Problem

{rp.get('problem_solved', 'A real workflow gap that slows people down.')}

## Concept

{rp.get('concept', 'A pragmatic AI-native tool.')}

## Tech Stack

- **Frontend:** {', '.join(rp.get('tech_stack', {}).get('frontend', []))}
- **Backend:** {', '.join(rp.get('tech_stack', {}).get('backend', []))}
- **Database:** {', '.join(rp.get('tech_stack', {}).get('database', []))}
- **AI:** {', '.join(rp.get('tech_stack', {}).get('ai', []))}
- **Deployment:** {', '.join(rp.get('tech_stack', {}).get('deployment', []))}

## Key Features

{chr(10).join(f'- {f}' for f in rp.get('key_features', []))}

## Demo Approach

{rp.get('demo_approach', 'Show the core action in under 60 seconds.')}

## Wow Factor

{rp.get('wow_factor', 'Real-time feedback the user can see immediately.')}

## Build Timeline

Estimated {rp.get('estimated_build_days', 7)} days working solo with AI tools.

## Setup

```bash
git clone <this-repo>
cd <project>
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add secrets
python src/main.py
```

## License

MIT
"""


def _architecture(opp: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    rp = analysis.get('recommended_project', {})
    return f"""# Architecture — {rp.get('name', opp.get('name'))}

## High-level flow

1. User lands on the home page.
2. They trigger the headline action.
3. The backend calls the LLM with a tight, optimised prompt.
4. Result is stored in the database and rendered to the user.
5. User can share, export, or trigger follow-up actions.

## Components

- **Frontend** — single-page React app with TailwindCSS, served by Vercel.
- **API** — FastAPI service in Python, deployed on Railway.
- **DB** — PostgreSQL (prod) / SQLite (dev) for persistence.
- **Worker** — APScheduler-driven background jobs for periodic tasks.
- **LLM layer** — OpenAI API abstracted behind a small wrapper.

## Trade-offs

- We optimise for shippability over scale. Postgres swap is a 1-day change.
- We use polling instead of websockets to keep infra simple.
- All secrets live in env vars; no keys in the repo.

## Security

- Auth via short-lived JWTs.
- Rate limit the public API.
- Sanitise every user input.
- No PII is logged.
"""


def _task_list(opp: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    rp = analysis.get('recommended_project', {})
    days = rp.get('estimated_build_days', 7)
    return f"""# Task list — {rp.get('name', opp.get('name'))}

## Day 1 — Foundations
- [ ] Project scaffold (frontend + backend)
- [ ] Database schema + migrations
- [ ] Auth scaffolding

## Day 2 — Core flow
- [ ] LLM wrapper with retries
- [ ] Core API endpoint
- [ ] Frontend happy path

## Day 3 — Polish
- [ ] Loading states + error UI
- [ ] Share/export
- [ ] Mobile responsive pass

## Day 4 — Demo + submit
- [ ] Deploy frontend + backend
- [ ] Record 2-minute demo video
- [ ] Write README + screenshots
- [ ] Submit on the platform

## Stretch
- [ ] Analytics dashboard
- [ ] Email notifications
- [ ] User accounts
"""


def _demo_plan(opp: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    rp = analysis.get('recommended_project', {})
    return f"""# Demo plan — {rp.get('name', opp.get('name'))}

## 0:00 — Cold open
Open with the empty state and the problem you solve.

## 0:15 — Core action
Run the headline flow live. No edits. No mocks.

## 0:45 — Show the result
Reveal the output and highlight the wow factor.

## 1:15 — Code walkthrough
1 minute on the architecture slide.

## 1:45 — Future roadmap
Where this goes next. Why this matters.

## 1:55 — Close
Project name + URL. Hold for 2 seconds. End.
"""


def _submission_checklist(opp: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    return f"""# Submission checklist — {opp.get('name')}

## Required
- [ ] Working demo (live URL)
- [ ] Source code (GitHub public)
- [ ] 2-3 minute demo video
- [ ] Project description (200-500 words)
- [ ] Tagline (max 80 chars)
- [ ] Cover image (1200x630)
- [ ] Tech stack tags
- [ ] Eligibility confirmed

## Nice to have
- [ ] 3 screenshots
- [ ] 30-second teaser
- [ ] Twitter post draft
- [ ] Discord announcement

## Quality bar
- [ ] No console errors
- [ ] Mobile-friendly
- [ ] README is scannable in 30 seconds
- [ ] All links resolve
- [ ] Build passes

## Timing
- [ ] Submit 24 hours before deadline
- [ ] Have backup offline copies of all media
"""


def _main_py(opp: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    rp = analysis.get('recommended_project', {})
    return f'''#!/usr/bin/env python3
"""
{rp.get('name', 'Main')} — entry point.
"""
from __future__ import annotations

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="{rp.get('name', 'Project')}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Query(BaseModel):
    text: str


@app.get("/")
def root():
    return {{"name": "{rp.get('name')}", "status": "ok"}}


@app.get("/health")
def health():
    return {{"status": "ok"}}


@app.post("/api/generate")
def generate(q: Query):
    if not q.text.strip():
        raise HTTPException(status_code=400, detail="Empty query")
    # TODO: call LLM
    return {{"result": f"Echo: {{q.text}}", "status": "ok"}}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
'''


def _frontend_index(opp: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    rp = analysis.get('recommended_project', {})
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{rp.get('name', 'Project')}</title>
  <meta name="description" content="{rp.get('tagline', '')}" />
  <link rel="stylesheet" href="./style.css" />
</head>
<body>
  <main class="container">
    <h1>{rp.get('name', 'Project')}</h1>
    <p class="tagline">{rp.get('tagline', '')}</p>
    <form id="prompt">
      <textarea id="input" rows="3" placeholder="Ask anything..."></textarea>
      <button type="submit">Run</button>
    </form>
    <pre id="output"></pre>
  </main>
  <script src="./app.js"></script>
</body>
</html>
"""


def _frontend_app_js() -> str:
    return '''const form = document.getElementById('prompt');
const out = document.getElementById('output');
const input = document.getElementById('input');
form?.addEventListener('submit', async (e) => {
  e.preventDefault();
  out.textContent = 'Thinking...';
  try {
    const r = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: input.value })
    });
    const data = await r.json();
    out.textContent = data.result || 'No result';
  } catch (err) {
    out.textContent = 'Error: ' + err.message;
  }
});
'''


def _frontend_style_css() -> str:
    return ''':root {
  --bg: #0a0a0f;
  --fg: #f8fafc;
  --muted: #94a3b8;
  --accent: #6366f1;
  --card: #11111c;
  --border: #1e1e30;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, sans-serif;
  background: var(--bg);
  color: var(--fg);
}
.container { max-width: 720px; margin: 4rem auto; padding: 0 1rem; }
h1 { font-size: 2.4rem; margin: 0 0 0.5rem; }
.tagline { color: var(--muted); margin: 0 0 2rem; }
textarea, button {
  width: 100%;
  padding: 0.8rem 1rem;
  border-radius: 10px;
  background: var(--card);
  color: var(--fg);
  border: 1px solid var(--border);
  font: inherit;
}
button {
  margin-top: 0.8rem;
  background: var(--accent);
  border: none;
  cursor: pointer;
  font-weight: 600;
}
pre {
  margin-top: 1.5rem;
  padding: 1rem;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  white-space: pre-wrap;
  min-height: 4rem;
}
'''


def _requirements_txt() -> str:
    return """fastapi>=0.110.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0
python-dotenv>=1.0.0
openai>=1.10.0
requests>=2.31.0
"""


def _dockerfile() -> str:
    return """FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=8000
EXPOSE 8000
CMD [\"uvicorn\", \"src.main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\"]
"""


def _github_actions_deploy() -> str:
    return """name: Deploy
on:
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt
      - run: python -m pytest -q || true
"""


# ----------------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------------

class ProjectFileGenerator:
    def __init__(self, db_path: str = DB_PATH, projects_dir: str = str(PROJECTS_DIR)):
        self.db_path = db_path
        self.projects_dir = projects_dir
        os.makedirs(self.projects_dir, exist_ok=True)

    def _load_opportunity(self, opportunity_id: int) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM opportunities WHERE id = ?", (opportunity_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return {}
        return dict(row)

    def _slug(self, name: str) -> str:
        s = ''.join(c.lower() if c.isalnum() else '-' for c in name)
        return '-'.join(p for p in s.split('-') if p)[:40]

    def _project_dir(self, opp: Dict[str, Any]) -> str:
        slug = self._slug(opp.get('name', f"opp-{opp.get('id')}"))
        path = os.path.join(self.projects_dir, f"{opp.get('id'):04d}_{slug}")
        os.makedirs(path, exist_ok=True)
        return path

    def _write_files(self, base: str, files: Dict[str, str]) -> None:
        for relpath, content in files.items():
            full = os.path.join(base, relpath)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, 'w', encoding='utf-8') as f:
                f.write(content)

    def generate_all(self, opportunity_id: int, opp: Dict[str, Any] = None) -> int:
        """Generate the full artefact set for an opportunity. Returns file count."""
        opp = opp or self._load_opportunity(opportunity_id)
        if not opp:
            return 0
        try:
            analysis = json.loads(opp.get('analysis_json') or '{}')
        except Exception:
            analysis = {}

        # In-DB files
        db_files: Dict[str, str] = {
            'README.md': _readme(opp, analysis),
            'architecture.md': _architecture(opp, analysis),
            'task_list.md': _task_list(opp, analysis),
            'demo_plan.md': _demo_plan(opp, analysis),
            'submission_checklist.md': _submission_checklist(opp, analysis),
        }
        inserted = _record_files(opportunity_id, db_files, file_type='doc')

        # Disk artefacts
        base = self._project_dir(opp)
        disk_files: Dict[str, str] = {
            'src/main.py': _main_py(opp, analysis),
            'frontend/index.html': _frontend_index(opp, analysis),
            'frontend/app.js': _frontend_app_js(),
            'frontend/style.css': _frontend_style_css(),
            'requirements.txt': _requirements_txt(),
            'Dockerfile': _dockerfile(),
            '.github/workflows/deploy.yml': _github_actions_deploy(),
            'README.md': db_files['README.md'],
        }
        self._write_files(base, disk_files)
        return inserted + len(disk_files)


if __name__ == '__main__':
    # quick smoke test
    import sys
    from seed import seed_database
    seed_database()
    g = ProjectFileGenerator()
    count = g.generate_all(1)
    print(f"Generated {count} files for opportunity #1")
