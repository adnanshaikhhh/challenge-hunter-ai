#!/usr/bin/env python3
"""
Challenge Hunter AI v2.2 — Unified LLM Client
Supports multiple providers with automatic fallback:
  1. tokenrouter.com (Minimax M3) - PRIMARY
  2. NVIDIA NIM - FALLBACK
  3. OpenAI-compatible custom endpoints

Use via:
  from llm import LLMClient
  client = LLMClient()
  result = client.complete(messages=[...], model='minimax-m3')
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

import requests


# =============================================================================
# Configuration
# =============================================================================

# tokenrouter.com (your custom endpoint, primary)
# Default model: minimax-m3 (works on tokenrouter)
LLM_PRIMARY_BASE_URL = os.environ.get(
    'LLM_PRIMARY_BASE_URL',
    'https://api.tokenrouter.com/v1'
)
LLM_PRIMARY_KEY = os.environ.get(
    'LLM_PRIMARY_KEY',
    os.environ.get('TOKENROUTER_API_KEY', '')
)
LLM_PRIMARY_MODEL = os.environ.get(
    'LLM_PRIMARY_MODEL',
    'minimax-m3'
)

# NVIDIA NIM (fallback)
# Get a free key at https://build.nvidia.com
LLM_FALLBACK_BASE_URL = os.environ.get(
    'LLM_FALLBACK_BASE_URL',
    'https://integrate.api.nvidia.com/v1'
)
LLM_FALLBACK_KEY = os.environ.get(
    'LLM_FALLBACK_KEY',
    os.environ.get('NVIDIA_API_KEY', '')
)
LLM_FALLBACK_MODEL = os.environ.get(
    'LLM_FALLBACK_MODEL',
    'meta/llama-3.1-70b-instruct'  # or 'mistralai/mistral-7b-instruct-v0.3'
)

# Optional: OpenAI (tertiary fallback)
LLM_OPENAI_KEY = os.environ.get('OPENAI_API_KEY', '')
LLM_OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')


# =============================================================================
# LLM Client with automatic fallback
# =============================================================================

class LLMClient:
    """
    Unified LLM client. Tries primary (tokenrouter/Minimax M3), then
    NVIDIA NIM, then OpenAI. Returns first success.
    """

    def __init__(self, primary: Optional[str] = None, fallback: Optional[str] = None):
        # Allow per-call override of provider
        self.primary = primary or 'auto'
        self.fallback = fallback or 'auto'
        self.last_provider = None
        self.last_error = None

    def _try_provider(
        self,
        name: str,
        base_url: str,
        api_key: str,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 8000,
        timeout: int = 120,
    ) -> Optional[Dict[str, Any]]:
        """Try a single provider. Returns response dict or None."""
        if not api_key or not base_url:
            return None
        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }
        # tokenrouter / NVIDIA NIM can be picky — send both common header names
        try:
            r = requests.post(
                url,
                json={
                    'model': model,
                    'messages': messages,
                    'temperature': temperature,
                    'max_tokens': max_tokens,
                    'stream': False,
                },
                headers=headers,
                timeout=timeout
            )
            r.raise_for_status()
            data = r.json()
            content = data['choices'][0]['message']['content']
            usage = data.get('usage', {})
            return {
                'success': True,
                'content': content,
                'model': data.get('model', model),
                'provider': name,
                'tokens': usage.get('total_tokens', 0),
                'prompt_tokens': usage.get('prompt_tokens', 0),
                'completion_tokens': usage.get('completion_tokens', 0),
            }
        except Exception as e:
            self.last_error = f'{name}: {type(e).__name__}: {str(e)[:200]}'
            print(f"⚠️  {name} failed: {self.last_error}")
            return None

    def complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 8000,
        timeout: int = 120,
    ) -> Dict[str, Any]:
        """
        Send messages to LLM. Tries providers in order:
          tokenrouter → NVIDIA NIM → OpenAI
        Returns dict with: success, content, model, provider, tokens, error
        """
        # Override model if specified
        primary_model = model or LLM_PRIMARY_MODEL
        fallback_model = model or LLM_FALLBACK_MODEL

        # 1. Primary: tokenrouter / Minimax M3
        result = self._try_provider(
            'tokenrouter', LLM_PRIMARY_BASE_URL, LLM_PRIMARY_KEY,
            primary_model, messages, temperature, max_tokens, timeout
        )
        if result:
            self.last_provider = 'tokenrouter'
            return result

        # 2. Fallback: NVIDIA NIM
        result = self._try_provider(
            'nvidia-nim', LLM_FALLBACK_BASE_URL, LLM_FALLBACK_KEY,
            fallback_model, messages, temperature, max_tokens, timeout
        )
        if result:
            self.last_provider = 'nvidia-nim'
            return result

        # 3. Tertiary: OpenAI
        if LLM_OPENAI_KEY:
            result = self._try_provider(
                'openai', 'https://api.openai.com/v1', LLM_OPENAI_KEY,
                LLM_OPENAI_MODEL, messages, temperature, max_tokens, timeout
            )
            if result:
                self.last_provider = 'openai'
                return result

        return {
            'success': False,
            'error': 'All LLM providers failed. Check LLM_PRIMARY_KEY / LLM_FALLBACK_KEY env vars.',
            'last_error': self.last_error,
            'content': None,
        }

    # Convenience methods
    def chat(self, system: str, user: str, **kw) -> Dict[str, Any]:
        return self.complete([
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': user}
        ], **kw)

    def generate_code(self, brief: str, language: str = 'python', **kw) -> Dict[str, Any]:
        system = f"""You are an expert {language} engineer. Output complete, production-ready code.
For each file, use this exact format:

```{language}:path/to/file.ext
# complete file content
```

Only output the files needed. No explanations outside the code blocks."""
        return self.chat(system, brief, temperature=0.3, max_tokens=16000, **kw)


# =============================================================================
# Backwards-compat: expose old config names
# =============================================================================

OPENROUTER_API_KEY = LLM_PRIMARY_KEY  # legacy alias
OPENROUTER_URL = f"{LLM_PRIMARY_BASE_URL.rstrip('/')}/chat/completions"
OPENROUTER_MODEL = LLM_PRIMARY_MODEL
OPENROUTER_BASE_URL = LLM_PRIMARY_BASE_URL

# Default client instance
default_client = LLMClient()


def call_llm(messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
    """Quick helper — uses default client."""
    return default_client.complete(messages, **kwargs)


# =============================================================================
# CLI
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("LLM Client — Provider Test")
    print("=" * 60)
    print(f"Primary:  {LLM_PRIMARY_BASE_URL} | model={LLM_PRIMARY_MODEL}")
    print(f"          key={'set ('+LLM_PRIMARY_KEY[:8]+'...)' if LLM_PRIMARY_KEY else 'NOT SET'}")
    print(f"Fallback: {LLM_FALLBACK_BASE_URL} | model={LLM_FALLBACK_MODEL}")
    print(f"          key={'set ('+LLM_FALLBACK_KEY[:8]+'...)' if LLM_FALLBACK_KEY else 'NOT SET'}")
    print(f"Tertiary: OpenAI | model={LLM_OPENAI_MODEL}")
    print(f"          key={'set' if LLM_OPENAI_KEY else 'NOT SET'}")
    print()

    result = call_llm([
        {'role': 'system', 'content': 'You are a helpful assistant.'},
        {'role': 'user', 'content': 'Respond with one short sentence: which LLM is this?'}
    ])
    if result['success']:
        print(f"✅ Working via {result['provider']} (model={result['model']})")
        print(f"   Response: {result['content'][:200]}")
        print(f"   Tokens: {result['tokens']}")
    else:
        print(f"❌ All providers failed")
        print(f"   Last error: {result.get('last_error')}")
