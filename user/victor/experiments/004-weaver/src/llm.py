"""
LLM chat with triple routing:
- Paid models (gpt-5-nano) → direct OpenAI API
- Local free models (gemma-3-27b-it) → transformers on GPU (4-bit quantized)
- [DEPRECATED] Remote free models (gemini:*) → Google AI Studio API

Local mode avoids TPM rate limits and allows concurrent interviews on PACE.
"""

import os
import time
from typing import Optional, List, Dict

import openai

# ── Remote Google AI (deprecated, kept for fallback) ─────────────────────────
# GOOGLE_AI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
# GOOGLE_PREFIX = "gemini:"

# ── Model presets ────────────────────────────────────────────────────────────
PAID_DEFAULT = "gpt-5-nano"
FREE_DEFAULT = "local:gemma-3-27b-it"

# ── Local model prefix ──────────────────────────────────────────────────────
LOCAL_PREFIX = "local:"

# ── Singleton for local model (loaded once, reused across calls) ─────────────
_local_model = None
_local_tokenizer = None


def _is_local_model(model: str) -> bool:
    return model.startswith(LOCAL_PREFIX)


def _load_local_model():
    """Load Gemma 3 27B with 4-bit quantization. Cached as singleton."""
    global _local_model, _local_tokenizer
    if _local_model is not None:
        return _local_model, _local_tokenizer

    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

    model_id = "google/gemma-3-27b-it"
    print(f"  [Loading local model: {model_id} (4-bit)...]")

    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
    )

    _local_tokenizer = AutoTokenizer.from_pretrained(model_id)
    if _local_tokenizer.pad_token_id is None:
        _local_tokenizer.pad_token_id = _local_tokenizer.eos_token_id
    _local_tokenizer.padding_side = "left"

    _local_model = AutoModelForCausalLM.from_pretrained(
        model_id,
        quantization_config=quantization_config,
        device_map="auto",
        torch_dtype=torch.float16,
    )

    print(f"  [Local model loaded on {_local_model.device}]")
    return _local_model, _local_tokenizer


def _local_chat(
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 1000,
) -> str:
    """Generate response using local Gemma model."""
    import torch

    model, tokenizer = _load_local_model()

    # Gemma doesn't support system role — merge into first user message
    merged = []
    system_text = ""
    for m in messages:
        if m["role"] == "system":
            system_text += m["content"] + "\n\n"
        else:
            if system_text and m["role"] == "user" and not merged:
                merged.append({"role": "user", "content": system_text + m["content"]})
                system_text = ""
            else:
                merged.append(m)
    if not merged and system_text:
        merged.append({"role": "user", "content": system_text.strip()})

    inputs = tokenizer.apply_chat_template(
        merged,
        add_generation_prompt=True,
        return_tensors="pt",
        return_dict=True,
    ).to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            input_ids=inputs.input_ids,
            attention_mask=inputs.attention_mask,
            max_new_tokens=max_tokens,
            do_sample=temperature > 0,
            temperature=temperature if temperature > 0 else None,
            top_p=0.9 if temperature > 0 else None,
            pad_token_id=tokenizer.pad_token_id,
        )

    response_tokens = outputs[0][inputs.input_ids.shape[-1]:]
    text = tokenizer.decode(response_tokens, skip_special_tokens=True)
    return text.strip() if text else ""


# ── Remote Google AI (deprecated) ────────────────────────────────────────────
# def _is_google_model(model: str) -> bool:
#     return model.startswith(GOOGLE_PREFIX)


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
    - Models with 'local:' prefix → local GPU via transformers (4-bit quantized)
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
    # Build messages list if not provided
    if messages is None:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

    # ── Local model route ────────────────────────────────────────────────
    if _is_local_model(model):
        result = _local_chat(messages, temperature=temperature, max_tokens=max_tokens)
        if result:
            return result
        raise RuntimeError(f"Local model {model} returned empty response")

    # ── Remote Google AI route (deprecated, commented out) ───────────────
    # if _is_google_model(model):
    #     client = openai.OpenAI(
    #         base_url=GOOGLE_AI_BASE_URL,
    #         api_key=os.getenv("GOOGLE_AI_API_KEY"),
    #     )
    #     api_model = model[len(GOOGLE_PREFIX):]  # strip "gemini:" prefix
    #     google = True
    # else:

    # ── Paid OpenAI route ────────────────────────────────────────────────
    client = openai.OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    api_model = model

    # Strip system messages if needed (for models that don't support them)
    # google = False  # only paid models now
    # if google:
    #     messages = [
    #         {"role": "user" if m["role"] == "system" else m["role"], "content": m["content"]}
    #         for m in messages
    #     ]

    kwargs = {
        "model": api_model,
        "messages": messages,
    }
    # gpt-5-nano does not support temperature/max_tokens
    # if google:
    #     kwargs["temperature"] = temperature
    #     kwargs["max_tokens"] = max_tokens

    # Exponential backoff for rate limits
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
