#!/usr/bin/env python3
"""
Challenge Hunter AI v2.1 — Demo Video Generator
Takes a built project, generates a 2-3 minute demo video:
  - AI-written voiceover script
  - Text-to-speech (uses gTTS - free, no API key)
  - Slideshow of the README + project files
  - Background music (silent if not available)
  - Outputs MP4 to a local path

For production, swap gTTS for ElevenLabs / OpenAI TTS for higher quality.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from config import DB_PATH, PROJECTS_DIR
from llm import LLMClient, default_client


# =============================================================================
# Step 1: Generate voiceover script using AI
# =============================================================================

def _generate_script(opp: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    """
    Use the LLM to write a 2-3 minute voiceover script for the demo video.
    Returns plain text script (no stage directions).
    """
    project = (analysis.get('recommended_project') or {})
    system_prompt = """You are writing a voiceover script for a 2-3 minute hackathon demo video.
Write in second-person, present tense, conversational, enthusiastic but not over the top.
Structure:
  1. HOOK (10s) — grab attention, name the problem
  2. INTRO (15s) — what we built, who it's for
  3. DEMO WALKTHROUGH (90s) — show the 3 most impressive features live
  4. WOW MOMENT (15s) — the killer feature
  5. TECH (10s) — quick mention of stack
  6. CLOSE (10s) — call to action, where to find it

Output ONLY the script text, no labels, no directions, just the spoken words.
Target 350-450 words for ~2.5 minutes at normal speaking pace."""

    user_prompt = f"""Project: {opp.get('name')}
Project to build: {project.get('name', '')}
Tagline: {project.get('tagline', '')}
Problem: {project.get('problem_solved', '')}
Concept: {project.get('concept', '')}
Key features: {', '.join(project.get('key_features', []))}
Wow factor: {project.get('wow_factor', '')}
Tech stack: {json.dumps(project.get('tech_stack', {}))}

Write the demo video script now."""

    result = default_client.complete(
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ],
        temperature=0.7,
        max_tokens=800,
        timeout=60
    )
    if not result.get('success'):
        return _fallback_script(opp, analysis)
    return result['content'].strip()


def _fallback_script(opp: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    """A reasonable fallback script when no AI is available."""
    project = (analysis.get('recommended_project') or {})
    return f"""Hi, I'm excited to show you {project.get('name', opp.get('name'))}.

{project.get('concept', 'We built a tool that solves a real problem.')}

The problem? {project.get('problem_solved', 'Existing solutions are slow, expensive, or complicated.')}

Here's what we built: {project.get('tagline', 'A fast, simple, AI-powered solution.')}

Let me show you how it works. First, you {project.get('key_features', ['open the app'])[0] if project.get('key_features') else 'open the app'}.

Then, you {project.get('key_features', ['use the core feature'])[1] if len(project.get('key_features', [])) > 1 else 'see the results instantly'}.

And here's the part I'm most proud of: {project.get('wow_factor', 'the real-time response that makes this special')}.

It's built with {', '.join(project.get('tech_stack', {}).get('frontend', ['modern web tech']))}.

You can try it right now at the link in the description. Thanks for watching!"""


# =============================================================================
# Step 2: Text-to-speech
# =============================================================================

def _text_to_speech(script: str, output_path: str) -> bool:
    """
    Convert script text to speech audio.
    Uses gTTS (Google Translate TTS) - free, no API key.
    Falls back to a silent track if gTTS not available.
    """
    try:
        from gtts import gTTS
        tts = gTTS(text=script, lang='en', slow=False)
        tts.save(output_path)
        return True
    except ImportError:
        print("⚠️  gTTS not installed; using silent track")
        return False
    except Exception as e:
        print(f"⚠️  TTS failed: {e}")
        return False


# =============================================================================
# Step 3: Render slides as PNG screenshots
# =============================================================================

def _render_slides(opp: Dict[str, Any], script: str, slides_dir: str) -> List[str]:
    """
    Render text slides as PNG using PIL.
    Returns list of file paths.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("⚠️  PIL not installed, skipping slides")
        return []

    # Find a font
    font_path = None
    for path in [
        'C:/Windows/Fonts/arialbd.ttf',  # Windows
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',  # Linux
        '/System/Library/Fonts/Helvetica.ttc',  # macOS
    ]:
        if os.path.exists(path):
            font_path = path
            break

    title_font = ImageFont.truetype(font_path, 60) if font_path else ImageFont.load_default()
    body_font = ImageFont.truetype(font_path, 36) if font_path else ImageFont.load_default()

    slides = [
        ('Hook', opp.get('name', 'Project') + '\n\nA new kind of tool'),
        ('The Problem', script.split('\n\n')[1] if '\n\n' in script else 'Users struggle'),
        ('The Solution', 'We built this: ' + (script.split('\n\n')[2] if len(script.split('\n\n')) > 2 else 'an AI tool')),
        ('How It Works', 'Simple. Fast. Beautiful.'),
        ('Try It', f'Live demo: {opp.get("url", "see description")}'),
    ]

    paths = []
    for i, (heading, body) in enumerate(slides):
        img = Image.new('RGB', (1920, 1080), color=(13, 13, 36))  # dark bg
        draw = ImageDraw.Draw(img)
        # Heading
        draw.text((100, 200), heading, fill=(248, 250, 252), font=title_font)
        # Body
        draw.text((100, 400), body, fill=(148, 163, 184), font=body_font)
        path = os.path.join(slides_dir, f"slide_{i:02d}.png")
        img.save(path)
        paths.append(path)
    return paths


# =============================================================================
# Step 4: Stitch into MP4 with ffmpeg
# =============================================================================

def _stitch_video(slides: List[str], audio: Optional[str], output: str) -> bool:
    """Combine slides + audio into a single MP4."""
    if not slides:
        return False
    try:
        # Use ffmpeg if available
        # Create a 5-second-per-slide video, optionally with audio
        per_slide = 5
        if audio and os.path.exists(audio):
            cmd = [
                'ffmpeg', '-y',
                '-framerate', f'1/{per_slide}',
                '-i', os.path.join(os.path.dirname(slides[0]), 'slide_%02d.png'),
                '-i', audio,
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-shortest',
                '-pix_fmt', 'yuv420p',
                output
            ]
        else:
            cmd = [
                'ffmpeg', '-y',
                '-framerate', f'1/{per_slide}',
                '-i', os.path.join(os.path.dirname(slides[0]), 'slide_%02d.png'),
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                output
            ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            print(f"⚠️  ffmpeg error: {result.stderr[:300]}")
            return False
        return True
    except FileNotFoundError:
        print("⚠️  ffmpeg not installed")
        return False
    except Exception as e:
        print(f"⚠️  ffmpeg error: {e}")
        return False


# =============================================================================
# Public API
# =============================================================================

def generate_demo_video(opportunity_id: int) -> Dict[str, Any]:
    """
    Generate a complete demo video for the given opportunity.
    Saves to projects/{id}_*/demo.mp4
    Logs to videos table.
    """
    import sqlite3

    # Load opp + analysis
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM opportunities WHERE id = ?", (opportunity_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return {'success': False, 'error': 'opportunity_not_found'}
    opp = dict(row)

    try:
        analysis = json.loads(opp.get('analysis_json') or '{}')
    except Exception:
        analysis = {}

    # Update status
    cursor.execute(
        "INSERT INTO videos (opportunity_id, title, status, voice) VALUES (?, ?, ?, ?)",
        (opportunity_id, opp.get('name', 'demo'), 'generating', 'gtts-en')
    )
    video_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # Create work dir
    work_dir = os.path.join(PROJECTS_DIR, f"video_{opportunity_id}_{int(time.time())}")
    os.makedirs(work_dir, exist_ok=True)
    slides_dir = os.path.join(work_dir, 'slides')
    os.makedirs(slides_dir, exist_ok=True)
    audio_path = os.path.join(work_dir, 'voice.mp3')
    output_path = os.path.join(work_dir, 'demo.mp4')

    try:
        # 1. Script
        script = _generate_script(opp, analysis)
        with open(os.path.join(work_dir, 'script.txt'), 'w', encoding='utf-8') as f:
            f.write(script)

        # 2. Slides
        slides = _render_slides(opp, script, slides_dir)

        # 3. Audio (best-effort)
        has_audio = _text_to_speech(script, audio_path)

        # 4. Stitch
        if _stitch_video(slides, audio_path if has_audio else None, output_path):
            # Save final record
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE videos SET script = ?, file_path = ?, status = ?, duration_seconds = ?
                WHERE id = ?
            """, (script, output_path, 'ready', 30, video_id))
            conn.commit()
            conn.close()
            return {
                'success': True,
                'video_id': video_id,
                'file_path': output_path,
                'script': script,
                'has_audio': has_audio,
                'slide_count': len(slides),
            }
        else:
            # Even if ffmpeg failed, the script + slides + audio exist
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE videos SET script = ?, file_path = ?, status = ?
                WHERE id = ?
            """, (script, audio_path if has_audio else slides_dir, 'partial', video_id))
            conn.commit()
            conn.close()
            return {
                'success': True,
                'video_id': video_id,
                'file_path': work_dir,
                'script': script,
                'has_audio': has_audio,
                'slide_count': len(slides),
                'note': 'Stitching failed (no ffmpeg?) but script + audio + slides saved to disk',
            }
    except Exception as e:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE videos SET status = ? WHERE id = ?", ('failed', video_id))
        conn.commit()
        conn.close()
        return {'success': False, 'error': str(e)}


# =============================================================================
# CLI
# =============================================================================

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python video_gen.py <opportunity_id>")
        sys.exit(1)
    result = generate_demo_video(int(sys.argv[1]))
    print(json.dumps({k: v for k, v in result.items() if k != 'script'},
                     indent=2, default=str))
    if result.get('script'):
        print("\n--- SCRIPT ---\n" + result['script'][:500] + "...")
