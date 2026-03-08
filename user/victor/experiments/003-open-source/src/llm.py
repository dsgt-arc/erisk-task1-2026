"""
LLM chat with dual routing:
- Paid models (gpt-5-nano) → direct OpenAI API
- Free models (gemini:*) → Google AI Studio (free, generous limits)
"""

import os
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

    if messages is None:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

    kwargs = {
        "model": api_model,
        "messages": messages,
    }
    # gpt-5-nano does not support temperature/max_tokens
    if _is_google_model(model):
        kwargs["temperature"] = temperature
        kwargs["max_tokens"] = max_tokens

    for attempt in range(3):
        response = client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        if content and content.strip():
            return content.strip()
        print(f"  [LLM returned empty response, retry {attempt + 1}/3]")

    raise RuntimeError(f"Model {model} returned empty content after 3 retries")
