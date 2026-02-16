"""
Simple LLM chat functions for different providers.

Usage:
    response = chat_openai("What is 2+2?")
    response = chat_anthropic("What is 2+2?")
    response = chat_local("What is 2+2?", model_name="microsoft/Phi-3-mini-4k-instruct")
"""

import os
import openai, anthropic

def chat_openai(prompt: str, model: str = "gpt-5", temperature: float = 0.0, max_tokens: int = 100) -> str:
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return response.choices[0].message.content.strip()


def chat_anthropic(prompt: str, model: str = "claude-3-5-haiku-20241022", temperature: float = 0.0, max_tokens: int = 100) -> str:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text.strip()

def chat(prompt: str, provider: str = "openai", **kwargs) -> str:
    if provider == "openai":
        return chat_openai(prompt, **kwargs)
    elif provider == "anthropic":
        return chat_anthropic(prompt, **kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}. Choose 'openai', 'anthropic', or 'local'.")
