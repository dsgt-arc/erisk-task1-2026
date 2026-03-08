"""
LLM chat with dual routing:
- Paid models (gpt-5-nano) → direct OpenAI API
- Free/open-source models → OpenRouter API
"""

import os
from typing import Optional, List, Dict

import openai

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Model presets
PAID_DEFAULT = "gpt-5-nano"
FREE_DEFAULT = "nvidia/nemotron-3-nano-30b-a3b:free"


def _is_openrouter_model(model: str) -> bool:
    """Models with a '/' are OpenRouter-style (provider/model)."""
    return "/" in model


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
    - Models with '/' (e.g. nvidia/nemotron:free) → OpenRouter
    - Models without '/' (e.g. gpt-5-nano) → direct OpenAI

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
    if _is_openrouter_model(model):
        client = openai.OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
    else:
        client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
        )

    if messages is None:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

    kwargs = {
        "model": model,
        "messages": messages,
    }
    # OpenRouter models support temperature/max_tokens; direct OpenAI gpt-5-nano does not
    if _is_openrouter_model(model):
        kwargs["temperature"] = temperature
        kwargs["max_tokens"] = max_tokens

    response = client.chat.completions.create(**kwargs)

    return response.choices[0].message.content.strip()
