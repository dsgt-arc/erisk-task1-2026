"""
LLM chat with dual routing:
- Paid models (gpt-5-nano) → direct OpenAI API
- Free models (gemini:*) → Google AI Studio (free, generous limits)
"""

import os
import time
from typing import Optional, List, Dict

import openai

GOOGLE_AI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

# Model presets
PAID_DEFAULT = "gpt-5-nano"
FREE_DEFAULT = "gemini:gemma-3-27b-it"

# Google AI Studio prefix
GOOGLE_PREFIX = "gemini:"


def _is_google_model(model: str) -> bool:
    return model.startswith(GOOGLE_PREFIX)


def chat(
    prompt: str,
    model: str = PAID_DEFAULT,
    temperature: float = 0.0,
    max_tokens: int = 1000,
    system_prompt: Optional[str] = None,
    messages: Optional[List[Dict[str, str]]] = None,
) -> str:
    """
    Chat with any model. Routes automatically:
    - Models with 'gemini:' prefix (e.g. gemini:gemma-3-27b-it) → Google AI Studio (free)
    - All other models (e.g. gpt-5-nano) → direct OpenAI API

    Args:
        prompt: User message (ignored if messages provided)
        model: Model name
        temperature: Sampling temperature
        max_tokens: Maximum response tokens
        system_prompt: Optional system prompt
        messages: Optional list of {"role": str, "content": str} messages

    Returns:
        Model response text
    """
    if _is_google_model(model):
        client = openai.OpenAI(
            base_url=GOOGLE_AI_BASE_URL,
            api_key=os.getenv("GOOGLE_AI_API_KEY"),
        )
        api_model = model[len(GOOGLE_PREFIX):]  # strip "gemini:" prefix
    else:
        client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        api_model = model

    google = _is_google_model(model)

    # Start of interview
    if messages is None:
        messages = []
        if system_prompt:
            # Gemma models don't support system role; prepend to user message
            if google:
                prompt = f"{system_prompt}\n\n{prompt}"
            else:
                messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
    
    # Continue interview with previous convo context
    elif google:
        # Strip system messages from pre-built message lists (no system role for Gemma 3)
        messages = [
            {"role": "user" if m["role"] == "system" else m["role"], "content": m["content"]}
            for m in messages
        ]

    kwargs = {
        "model": api_model,
        "messages": messages,
    }
    # gpt-5-nano does not support temperature/max_tokens
    if google:
        kwargs["temperature"] = temperature
        kwargs["max_tokens"] = max_tokens

    # Exponential backoff for free model rate limits
    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            if content and content.strip():
                return content.strip()
            print(f"  [LLM returned empty response, retry {attempt + 1}/{max_retries}]")
        except openai.RateLimitError as e:
            wait = min(2 ** attempt * 5, 60)  # 5s, 10s, 20s, 40s, 60s
            print(f"  [Rate limited, waiting {wait}s before retry {attempt + 1}/{max_retries}]")
            time.sleep(wait)
        except openai.APIError as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt * 2
                print(f"  [API error: {e}, retrying in {wait}s ({attempt + 1}/{max_retries})]")
                time.sleep(wait)
            else:
                raise

    raise RuntimeError(f"Model {model} failed after {max_retries} retries")
