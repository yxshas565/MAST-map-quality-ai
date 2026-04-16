# """
# Thin wrapper around Anthropic API.
# Lazy imports so the module loads even if packages aren't installed yet.
# """
# from __future__ import annotations
# from utils.logger import get_logger
# from core.config import ANTHROPIC_API_KEY, OPENAI_API_KEY, PRIMARY_MODEL, FALLBACK_MODEL

# log = get_logger(__name__)


# def call_llm(prompt: str, system: str = "", model: str = PRIMARY_MODEL,
#              max_tokens: int = 2048, temperature: float = 0.2) -> str:
#     if ANTHROPIC_API_KEY:
#         return _call_anthropic(prompt, system, model, max_tokens, temperature)
#     elif OPENAI_API_KEY:
#         log.warning("Falling back to OpenAI (no Anthropic key)")
#         return _call_openai(prompt, system, max_tokens, temperature)
#     else:
#         raise RuntimeError("No LLM API key found. Set ANTHROPIC_API_KEY in .env")


# def _call_anthropic(prompt, system, model, max_tokens, temperature) -> str:
#     try:
#         import anthropic
#     except ImportError:
#         raise RuntimeError("Run: pip install anthropic")
#     client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
#     messages = [{"role": "user", "content": prompt}]
#     kwargs = dict(model=model, max_tokens=max_tokens, messages=messages)
#     if system:
#         kwargs["system"] = system
#     response = client.messages.create(**kwargs)
#     return response.content[0].text


# def _call_openai(prompt, system, max_tokens, temperature) -> str:
#     try:
#         from openai import OpenAI
#     except ImportError:
#         raise RuntimeError("Run: pip install openai")
#     client = OpenAI(api_key=OPENAI_API_KEY)
#     messages = []
#     if system:
#         messages.append({"role": "system", "content": system})
#     messages.append({"role": "user", "content": prompt})
#     response = client.chat.completions.create(
#         model=FALLBACK_MODEL, messages=messages,
#         max_tokens=max_tokens, temperature=temperature,
#     )
#     return response.choices[0].message.content













"""
LLM Client — Anthropic Claude (primary) + rule-based fallback.
Uses claude-haiku-3-5 — cheapest Anthropic model, ~25x cheaper than Sonnet.
"""
from __future__ import annotations
import os
from utils.logger import get_logger
from core.config import ANTHROPIC_API_KEY, PRIMARY_MODEL

log = get_logger(__name__)

# Cheapest Anthropic model — perfect for classification + patch synthesis
CHEAP_MODEL = "claude-haiku-4-5-20251001"


def call_llm(
    prompt: str,
    system: str = "",
    model: str = CHEAP_MODEL,   # always use haiku unless overridden
    max_tokens: int = 512,      # keep low — our prompts need short JSON responses
    temperature: float = 0.1,
) -> str:
    if ANTHROPIC_API_KEY:
        log.info(f"Using Anthropic {model}")
        return _call_anthropic(prompt, system, model, max_tokens, temperature)
    raise RuntimeError(
        "ANTHROPIC_API_KEY not set in .env"
    )


def _call_anthropic(prompt, system, model, max_tokens, temperature) -> str:
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("Run: pip install anthropic")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    kwargs = dict(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    if system:
        kwargs["system"] = system
    return client.messages.create(**kwargs).content[0].text