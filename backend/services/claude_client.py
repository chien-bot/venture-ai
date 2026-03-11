"""
services/claude_client.py
────────────────────────────────────────────────────────────────
Robust LLM client supporting:
  1. Anthropic Claude (primary, via ANTHROPIC_API_KEY)
  2. OpenRouter (fallback, via OPENROUTER_API_KEY)
  3. Mock mode (USE_MOCK_API=true, for offline development)

Features:
  - Automatic retry with exponential backoff (3 attempts)
  - Context window management: truncate history if too long
  - Graceful degradation: on API error, returns a polite error message
  - Strips <think> tags from reasoning models
"""
from __future__ import annotations

import re
import time
import logging
from config import ANTHROPIC_API_KEY, OPENROUTER_API_KEY, MODEL_MAIN, USE_MOCK_API, USE_OPENROUTER

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 1.5   # seconds, doubled each retry
MAX_HISTORY_TOKENS_APPROX = 6000  # ~24k chars; trim history beyond this


def _strip_thinking(text: str) -> str:
    """Remove <think>...</think> blocks from reasoning models."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _trim_history(messages: list[dict], max_chars: int = MAX_HISTORY_TOKENS_APPROX * 4) -> list[dict]:
    """
    Trim conversation history from the oldest end to stay within budget.
    Always keep the most recent 2 messages (last user + last assistant).
    """
    if not messages:
        return messages
    total = sum(len(m.get("content", "")) for m in messages)
    if total <= max_chars:
        return messages

    # Keep last 2 messages always; trim from front
    trimmed = list(messages)
    while len(trimmed) > 2:
        total = sum(len(m.get("content", "")) for m in trimmed)
        if total <= max_chars:
            break
        trimmed.pop(0)
    return trimmed


def chat_completion(
    system_prompt: str,
    messages: list[dict],
    model: str = MODEL_MAIN,
    max_tokens: int = 2048,
) -> str:
    """
    Call LLM with retry logic and graceful error handling.
    Returns the assistant's text reply.
    """
    if USE_MOCK_API:
        return ""

    messages = _trim_history(messages)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if USE_OPENROUTER:
                return _openrouter_completion(system_prompt, messages, model, max_tokens)
            else:
                return _anthropic_completion(system_prompt, messages, model, max_tokens)
        except Exception as e:
            logger.warning(f"LLM call attempt {attempt}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)
            else:
                logger.error(f"All LLM retries exhausted. Last error: {e}")
                return _fallback_reply(str(e))

    return _fallback_reply("未知错误")


def _anthropic_completion(
    system_prompt: str,
    messages: list[dict],
    model: str,
    max_tokens: int,
) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Anthropic requires alternating user/assistant roles
    clean_msgs = _ensure_alternating(messages)

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=clean_msgs,
    )
    return response.content[0].text


def _openrouter_completion(
    system_prompt: str,
    messages: list[dict],
    model: str,
    max_tokens: int,
) -> str:
    from openai import OpenAI
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )
    openai_messages = [{"role": "system", "content": system_prompt}] + messages
    response = client.chat.completions.create(
        model=model,
        messages=openai_messages,
        max_tokens=max_tokens,
    )
    text = response.choices[0].message.content or ""
    return _strip_thinking(text)


def _ensure_alternating(messages: list[dict]) -> list[dict]:
    """
    Ensure messages strictly alternate user/assistant.
    Merges consecutive same-role messages.
    """
    if not messages:
        return messages
    result = [messages[0].copy()]
    for msg in messages[1:]:
        if msg["role"] == result[-1]["role"]:
            # Merge: append content
            result[-1] = {
                "role": result[-1]["role"],
                "content": result[-1]["content"] + "\n" + msg["content"],
            }
        else:
            result.append(msg.copy())
    # Must start with user role for Anthropic
    if result and result[0]["role"] != "user":
        result.insert(0, {"role": "user", "content": "（继续上次对话）"})
    return result


def chat_completion_stream(
    system_prompt: str,
    messages: list[dict],
    model: str = MODEL_MAIN,
    max_tokens: int = 2048,
):
    """
    Streaming version of chat_completion.
    Yields text chunks as they arrive from the LLM.
    """
    if USE_MOCK_API:
        yield ""
        return

    messages = _trim_history(messages)

    try:
        if USE_OPENROUTER:
            yield from _openrouter_stream(system_prompt, messages, model, max_tokens)
        else:
            yield from _anthropic_stream(system_prompt, messages, model, max_tokens)
    except Exception as e:
        logger.error(f"Streaming LLM call failed: {e}")
        yield _fallback_reply(str(e))


def _openrouter_stream(
    system_prompt: str,
    messages: list[dict],
    model: str,
    max_tokens: int,
):
    from openai import OpenAI
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )
    openai_messages = [{"role": "system", "content": system_prompt}] + messages
    response = client.chat.completions.create(
        model=model,
        messages=openai_messages,
        max_tokens=max_tokens,
        stream=True,
    )
    in_think = False
    for chunk in response:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta and delta.content:
            text = delta.content
            if "<think>" in text:
                in_think = True
            if in_think:
                if "</think>" in text:
                    in_think = False
                    text = text.split("</think>", 1)[-1]
                else:
                    continue
            if text:
                yield text


def _anthropic_stream(
    system_prompt: str,
    messages: list[dict],
    model: str,
    max_tokens: int,
):
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    clean_msgs = _ensure_alternating(messages)
    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=clean_msgs,
    ) as stream:
        for text in stream.text_stream:
            yield text


def _fallback_reply(error_hint: str = "") -> str:
    """Return a graceful degradation message when the API fails."""
    return (
        "抱歉，AI 服务暂时无法响应，请稍后重试。"
        + (f"（错误提示：{error_hint[:80]}）" if error_hint else "")
    )
