"""
Simple LLM chat functions for different providers.

Supports single-turn and multi-turn conversations with OpenAI and Anthropic.
"""

import os
from typing import Optional, List, Dict, Any

import openai
import anthropic


def chat_openai(
    prompt: str,
    model: str = "gpt-4o",
    temperature: float = 0.0,
    max_tokens: int = 1000,
    system_prompt: Optional[str] = None,
    messages: Optional[List[Dict[str, str]]] = None,
) -> str:
    """
    Chat with OpenAI models.
    
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
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
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


def chat_anthropic(
    prompt: str,
    model: str = "claude-sonnet-4-20250514",
    temperature: float = 0.0,
    max_tokens: int = 1000,
    system_prompt: Optional[str] = None,
    messages: Optional[List[Dict[str, str]]] = None,
) -> str:
    """
    Chat with Anthropic models.
    
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
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    if messages is None:
        messages = [{"role": "user", "content": prompt}]
    
    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages,
    }
    
    if system_prompt:
        kwargs["system"] = system_prompt
    
    response = client.messages.create(**kwargs)
    
    return response.content[0].text.strip()


def chat(
    prompt: str,
    provider: str = "anthropic",
    **kwargs,
) -> str:
    """
    Chat with any supported LLM provider.
    
    Args:
        prompt: User message
        provider: "openai" or "anthropic"
        **kwargs: Additional arguments passed to provider function
        
    Returns:
        Model response text
    """
    if provider == "openai":
        return chat_openai(prompt, **kwargs)
    elif provider == "anthropic":
        return chat_anthropic(prompt, **kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}. Choose 'openai' or 'anthropic'.")
