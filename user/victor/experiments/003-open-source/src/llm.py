"""
LLM chat via OpenRouter API.

Uses the OpenAI SDK with OpenRouter's base URL to access any model
(OpenAI, Anthropic, Meta, Google, Mistral, etc.) through a single endpoint.
"""

import os
from typing import Optional, List, Dict

import openai

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Model presets
PAID_DEFAULT = "openai/gpt-5-nano"
FREE_DEFAULT = "meta-llama/llama-3.1-8b-instruct:free"


def chat(
    prompt: str,
    model: str = PAID_DEFAULT,
    temperature: float = 0.0,
    max_tokens: int = 1000,
    system_prompt: Optional[str] = None,
    messages: Optional[List[Dict[str, str]]] = None,
) -> str:
    """
    Chat with any model via OpenRouter.

    Args:
        prompt: User message (ignored if messages provided)
        model: OpenRouter model string (e.g. "openai/gpt-4.1-mini")
        temperature: Sampling temperature
        max_tokens: Maximum response tokens
        system_prompt: Optional system prompt
        messages: Optional list of {"role": str, "content": str} messages

    Returns:
        Model response text
    """
    client = openai.OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )

    if messages is None:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return response.choices[0].message.content.strip()
