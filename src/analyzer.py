#!/usr/bin/env python3
"""
Challenge Hunter AI v2.0 — AI Analysis Engine
Generates rich JSON analysis for each opportunity.

Strategy:
  1. If OPENAI_API_KEY is set, call the OpenAI Chat Completions endpoint.
  2. Otherwise, fall back to a deterministic template-based generator
     that produces a well-formed, judge-ready analysis.

The output schema is the same in both cases so downstream code is identical.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List

import requests

from config import AI_ANALYSIS_DELAY_SECONDS


# ----------------------------------------------------------------------------
# JSON schema (kept as a string for use in the LLM prompt)
# ----------------------------------------------------------------------------

ANALYSIS_SCHEMA_DESCRIPTION = """
Return ONLY a single JSON object with EXACTLY this shape (no commentary, no markdown):

{
  "summary": "2-3 sentence plain English overview",
  "why_this_is_good": "1-2 sentences on why this is worth pursuing",
  "requirements": ["req1", "req2", "req3"],
  "risks": ["risk1 with mitigation", "risk2 with mitigation"],
  "win_probability_reasoning": "explanation of the probability score",
  "build_complexity": "low | medium | high",
  "time_to_build_estimate": "X days working solo with AI tools",
  "recommended_project": {
    "name": "catchy project name",
    "tagline": "one line description",
    "concept": "2-3 sentence concept explanation",
    "problem_solved": "what problem does this solve",
    "tech_stack": {
      "frontend": ["React", "TailwindCSS"],
      "backend": ["Python", "FastAPI"],
      "database": ["SQLite"],
      "ai": ["OpenAI API"],
      "deployment": ["Railway", "Vercel"]
    },
    "key_features": [
      "feature 1 — why it impresses judges",
      "feature 2 — why it impresses judges",
      "feature 3 — why it impresses judges"
    ],
    "demo_approach": "step by step what to show in 3 minutes",
    "wow_factor": "the one thing that makes judges remember this",
    "estimated_build_days": 5
  },
  "submission_strategy": "specific tactical advice for winning",
  "judge_appeal": "what judges at this competition care about",
  "alternative_projects": [
    {"name": "lite", "concept": "brief description", "build_days": 3},
    {"name": "pro", "concept": "brief description", "build_days": 7}
  ],
  "recommended_action": "approve | skip | monitor",
  "action_reasoning": "why this specific action is recommended"
}
"""


# ----------------------------------------------------------------------------
# Deterministic fallback analysis
# ----------------------------------------------------------------------------

TECH_STACKS = {
    'easy': {
        'frontend': ['React', 'TailwindCSS'],
        'backend': ['Python', 'Flask'],
        'database': ['SQLite'],
        'ai': ['OpenAI API'],
        'deployment': ['Railway', 'Vercel']
    },
    'medium': {
        'frontend': ['React', 'TailwindCSS'],
        'backend': ['Python', 'FastAPI'],
        'database': ['PostgreSQL', 'SQLite'],
        'ai': ['OpenAI API', 'LangChain'],
        'deployment': ['Railway', 'Vercel', 'Docker']
    },
    'hard': {
        'frontend': ['React', 'Next.js', 'TailwindCSS'],
        'backend': ['Python', 'FastAPI'],
        'database': ['PostgreSQL', 'Redis'],
        'ai': ['OpenAI API', 'LangChain', 'Vector DB'],
        'deployment': ['Railway', 'Vercel', 'Docker', 'Kubernetes']
    }
}

PROJECT_NAME_PREFIXES = [
    'Pulse', 'Vibe', 'Spark', 'Forge', 'Lift', 'Bolt', 'Quill',
    'Halo', 'Orbit', 'Beacon', 'Helix', 'Nimbus', 'Echo', 'Atlas',
    'Pioneer', 'Aurora', 'Cipher', 'Ember', 'Vista', 'Drift'
]

PROJECT_NAME_SUFFIXES = [
    'AI', 'Lab', 'OS', 'Kit', 'Studio', 'Forge', 'Hub', 'Loop',
    'Sync', 'Pilot', 'Wave', 'Spark', 'Beam', 'Shift', 'Core'
]


def _slugify(text: str, max_len: int = 24) -> str:
    s = ''.join(c.lower() if c.isalnum() else '-' for c in text)
    s = '-'.join(part for part in s.split('-') if part)
    return s[:max_len].strip('-')


def _project_name(seed: str) -> str:
    h = abs(hash(seed))
    prefix = PROJECT_NAME_PREFIXES[h % len(PROJECT_NAME_PREFIXES)]
    suffix = PROJECT_NAME_SUFFIXES[(h // 7) % len(PROJECT_NAME_SUFFIXES)]
    return f"{prefix}{suffix}"


def _summary(name, prize, days, ai_policy, difficulty) -> str:
    return (
        f"{name} is offering ${prize:,} in prizes with a {days}-day deadline. "
        f"AI policy is {ai_policy}, and the difficulty is rated {difficulty}. "
        f"This is a competitive opportunity worth serious evaluation."
    )


def _why_good(prize, days, ai_policy, source) -> str:
    bits = []
    if prize >= 10000:
        bits.append(f"the ${prize:,} prize is meaningful")
    if 14 <= days <= 45:
        bits.append("the deadline is in the sweet spot")
    if ai_policy == 'allowed':
        bits.append("AI tooling is explicitly allowed, accelerating build")
    if source:
        bits.append(f"{source} is a high-signal platform")
    if not bits:
        bits.append("the opportunity aligns with solo AI-assisted building")
    return "Worth pursuing because " + ", ".join(bits) + "."


def _requirements(ai_policy, source) -> List[str]:
    base = [
        "Build a working demo and submit a 2-3 minute walkthrough video.",
        "Document setup, architecture, and roadmap in the README.",
        "Publish source code publicly (GitHub) and deploy a live demo URL."
    ]
    if ai_policy == 'allowed':
        base.append("Lean into AI-assisted development to maximise output.")
    if source and 'devpost' in source.lower():
        base.append("Submit on Devpost with all required media and tags.")
    return base


def _risks(days, prize) -> List[str]:
    risks = [
        "Tight deadline — mitigate by shipping a vertical slice first and polishing last.",
        "Judge subjectivity — mitigate with clear metrics, strong visuals, and confident copy."
    ]
    if days < 14:
        risks.append("Very short runway — scope ruthlessly and avoid feature creep.")
    if prize > 25000:
        risks.append("High competition — differentiate on UX and demo polish.")
    return risks


def _complexity(difficulty) -> str:
    return {'easy': 'low', 'medium': 'medium', 'hard': 'high'}.get(difficulty, 'medium')


def _build_days(difficulty) -> int:
    return {'easy': 4, 'medium': 7, 'hard': 12}.get(difficulty, 7)


def _time_to_build(difficulty) -> str:
    return f"{_build_days(difficulty)} days working solo with AI tools"


def _key_features(difficulty) -> List[str]:
    return [
        "One-tap core flow — judges will demo this within 5 seconds.",
        "Persistent memory — surprising recall across sessions wins screenshots.",
        "Beautiful shareable output — wins word-of-mouth and re-watches."
    ]


def _demo_approach() -> str:
    return (
        "1) Open with the empty state and the headline problem. "
        "2) Run the core action live. "
        "3) Show the saved, shareable result. "
        "4) Highlight the unique angle (the wow factor). "
        "5) Close with a metrics dashboard and the roadmap."
    )


def _submission_strategy(source) -> str:
    if source and 'devpost' in source.lower():
        return "Lead with the demo video, then 5 screenshots, then the GitHub repo. Submit 24h early."
    return "Polish the README, record a tight 2-minute demo, submit 24h early, and engage with the community."


def _judge_appeal(source) -> str:
    if source and 'solana' in source.lower():
        return "Solana judges reward working on-chain flows, real wallets, and visible transactions."
    if source and 'huggingface' in source.lower():
        return "HF judges reward clear model use, evaluation, and reproducibility."
    if source and 'anthropic' in source.lower():
        return "Anthropic judges reward thoughtful Claude integration, safety, and documentation."
    return "Judges reward execution speed, polish, working demos, and clear problem articulation."


def _alternatives(name) -> List[Dict[str, Any]]:
    return [
        {"name": f"{_project_name(name)}-lite", "concept": "Stripped-down CLI version of the same idea.", "build_days": 2},
        {"name": f"{_project_name(name)}-pro", "concept": "Full SaaS with auth, billing, and team workspaces.", "build_days": 12}
    ]


def _recommend(score, days, ai_policy) -> tuple:
    if score >= 70 and ai_policy != 'banned' and days > 0:
        return 'approve', f"Score {score} is high, rules are workable, deadline is healthy."
    if score < 40 or days <= 0 or ai_policy == 'banned':
        return 'skip', f"Score {score} too low or opportunity no longer viable."
    return 'monitor', f"Score {score} is borderline — revisit next scan."


# ----------------------------------------------------------------------------
# Public: build deterministic analysis
# ----------------------------------------------------------------------------

def build_deterministic_analysis(opportunity: Dict[str, Any]) -> Dict[str, Any]:
    name = opportunity.get('name') or 'Unknown Opportunity'
    prize = int(opportunity.get('prize_usd') or 0)
    days = int(opportunity.get('days_remaining') or 0)
    ai_policy = (opportunity.get('ai_policy') or 'unclear').lower()
    difficulty = (opportunity.get('difficulty') or 'medium').lower()
    source = opportunity.get('source') or ''
    score = int(opportunity.get('opportunity_score') or 0)
    prob = int(opportunity.get('win_probability') or 30)
    rec, reason = _recommend(score, days, ai_policy)

    project_name = _project_name(name)
    return {
        "summary": _summary(name, prize, days, ai_policy, difficulty),
        "why_this_is_good": _why_good(prize, days, ai_policy, source),
        "requirements": _requirements(ai_policy, source),
        "risks": _risks(days, prize),
        "win_probability_reasoning": (
            f"Estimated {prob}% reflects the {difficulty} difficulty, "
            f"${prize:,} prize class, and {ai_policy} AI policy."
        ),
        "build_complexity": _complexity(difficulty),
        "time_to_build_estimate": _time_to_build(difficulty),
        "recommended_project": {
            "name": project_name,
            "tagline": f"AI-powered companion for {source or 'the target domain'}.",
            "concept": (
                "A pragmatic, AI-native tool that closes a real workflow gap "
                "with delightful UX. Ships as a web app with a tight vertical slice."
            ),
            "problem_solved": "Slow, manual workflows that burn time and break flow.",
            "tech_stack": TECH_STACKS.get(difficulty, TECH_STACKS['medium']),
            "key_features": _key_features(difficulty),
            "demo_approach": _demo_approach(),
            "wow_factor": "Live, real-time visualization that reacts to user input — the screenshot judges remember.",
            "estimated_build_days": _build_days(difficulty)
        },
        "submission_strategy": _submission_strategy(source),
        "judge_appeal": _judge_appeal(source),
        "alternative_projects": _alternatives(name),
        "recommended_action": rec,
        "action_reasoning": reason,
        "meta": {
            "generated_by": "deterministic-v2",
            "generated_at": datetime.now().isoformat(),
            "schema_version": "2.0"
        }
    }


# ----------------------------------------------------------------------------
# LLM-backed analysis (optional)
# ----------------------------------------------------------------------------

def _openai_analysis(opportunity: Dict[str, Any]) -> Dict[str, Any] | None:
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return None
    model = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
    url = 'https://api.openai.com/v1/chat/completions'
    prompt_user = json.dumps({
        'opportunity': {
            'name': opportunity.get('name'),
            'url': opportunity.get('url'),
            'prize_usd': opportunity.get('prize_usd'),
            'prize_text': opportunity.get('prize_text'),
            'deadline': opportunity.get('deadline'),
            'days_remaining': opportunity.get('days_remaining'),
            'rules_summary': opportunity.get('rules_summary'),
            'ai_policy': opportunity.get('ai_policy'),
            'difficulty': opportunity.get('difficulty'),
            'eligibility': opportunity.get('eligibility'),
            'team_size': opportunity.get('team_size'),
            'source': opportunity.get('source'),
        }
    }, indent=2)
    body = {
        'model': model,
        'temperature': 0.5,
        'response_format': {'type': 'json_object'},
        'messages': [
            {
                'role': 'system',
                'content': 'You are a senior hackathon strategist. ' + ANALYSIS_SCHEMA_DESCRIPTION
            },
            {'role': 'user', 'content': prompt_user}
        ]
    }
    try:
        r = requests.post(
            url,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            json=body,
            timeout=60
        )
        r.raise_for_status()
        content = r.json()['choices'][0]['message']['content']
        parsed = json.loads(content)
        parsed.setdefault('meta', {})
        parsed['meta'].update({
            'generated_by': f'openai:{model}',
            'generated_at': datetime.now().isoformat(),
            'schema_version': '2.0'
        })
        return parsed
    except Exception as e:
        print(f"⚠️  OpenAI analysis failed, falling back: {e}")
        return None


# ----------------------------------------------------------------------------
# Public entry point
# ----------------------------------------------------------------------------

def analyze(opportunity: Dict[str, Any], use_llm: bool = True) -> Dict[str, Any]:
    """
    Generate a complete analysis for an opportunity.
    Honours AI_ANALYSIS_DELAY_SECONDS between calls.
    """
    if use_llm:
        result = _openai_analysis(opportunity)
        if result is not None:
            time.sleep(AI_ANALYSIS_DELAY_SECONDS)
            return result
    return build_deterministic_analysis(opportunity)


if __name__ == '__main__':
    sample = {
        'name': 'Test Hackathon',
        'prize_usd': 10000,
        'days_remaining': 30,
        'ai_policy': 'allowed',
        'difficulty': 'medium',
        'source': 'Devpost',
        'opportunity_score': 95,
        'win_probability': 55,
    }
    print(json.dumps(analyze(sample, use_llm=False), indent=2)[:1200])
