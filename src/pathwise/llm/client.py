"""Thin wrapper around the Anthropic SDK for Pathwise.

Two call shapes:

- ``call_with_research``: runs Claude with the ``web_search_20260209`` tool so
  it can gather grounded numbers (used-car prices, local rent, programs) before
  responding. Server-side; we don't execute any client-side tool code.

- ``call_plain``: a regular streamed call (no tools). Used for plan synthesis.

Both share the same season-pack system prompt with prompt caching enabled, so
research + plan synthesis on the same season hit the cache after the first
call. We use streaming (output can be large), adaptive thinking, and high
effort — Opus 4.7's recommended settings for intelligence-sensitive work.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import anthropic

from pathwise.config import get_settings

logger = logging.getLogger(__name__)


def _fmt_usage(usage: dict[str, int]) -> str:
    return (
        f"in={usage.get('input_tokens', 0)} "
        f"out={usage.get('output_tokens', 0)} "
        f"cache_r={usage.get('cache_read_input_tokens', 0)} "
        f"cache_w={usage.get('cache_creation_input_tokens', 0)}"
    )


@lru_cache(maxsize=1)
def get_client() -> anthropic.Anthropic:
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Add it to your .env or environment."
        )
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


@dataclass
class LlmCallResult:
    text: str
    sources: list[str]  # web_search source URLs, when available
    usage: dict[str, int]


def _extract_sources(content: list[Any]) -> list[str]:
    """Pull source URLs out of any web_search citations in the response."""
    urls: list[str] = []
    for block in content:
        # Citations attach to text blocks via .citations
        citations = getattr(block, "citations", None) or []
        for c in citations:
            url = getattr(c, "url", None)
            if url and url not in urls:
                urls.append(url)
        # web_search_tool_result blocks carry results with URLs
        if getattr(block, "type", None) == "web_search_tool_result":
            for result in getattr(block, "content", []) or []:
                url = getattr(result, "url", None)
                if url and url not in urls:
                    urls.append(url)
    return urls


def _system_blocks(system_text: str) -> list[dict[str, Any]]:
    """Wrap the system prompt as a single cacheable text block."""
    return [
        {
            "type": "text",
            "text": system_text,
            "cache_control": {"type": "ephemeral"},
        }
    ]


def call_with_research(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str,
    max_tokens: int = 16000,
) -> LlmCallResult:
    """Stream a Claude call with the web_search server-side tool enabled.

    Server-side tools loop on Anthropic's side; if they hit their internal
    iteration cap we get ``stop_reason == 'pause_turn'`` and need to re-send.
    We resume up to a small number of times, then give up — the user can
    regenerate the plan.
    """
    client = get_client()

    messages: list[dict[str, Any]] = [{"role": "user", "content": user_prompt}]
    sources: list[str] = []
    final_text = ""
    usage_totals: dict[str, int] = {}

    started = time.monotonic()
    logger.info(
        "llm.research start model=%s max_tokens=%d prompt_chars=%d",
        model, max_tokens, len(user_prompt),
    )
    for resume in range(3):
        logger.info("llm.research streaming (attempt %d)…", resume + 1)
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=_system_blocks(system_prompt),
            messages=messages,
            tools=[{"type": "web_search_20260209", "name": "web_search"}],
            thinking={"type": "adaptive"},
            output_config={"effort": "high"},
        ) as stream:
            response = stream.get_final_message()

        sources.extend(u for u in _extract_sources(response.content) if u not in sources)
        for block in response.content:
            if getattr(block, "type", None) == "text":
                final_text += block.text

        u = response.usage
        for k in (
            "input_tokens",
            "output_tokens",
            "cache_read_input_tokens",
            "cache_creation_input_tokens",
        ):
            usage_totals[k] = usage_totals.get(k, 0) + getattr(u, k, 0) or 0

        if response.stop_reason != "pause_turn":
            break

        # Server-side tool loop hit its cap — resume by echoing the assistant turn
        messages.append({"role": "assistant", "content": response.content})
        if resume == 2:
            logger.warning("web_search loop exceeded resume budget; using partial result")

    logger.info(
        "llm.research done in %.1fs sources=%d text_chars=%d %s",
        time.monotonic() - started, len(sources), len(final_text), _fmt_usage(usage_totals),
    )
    return LlmCallResult(text=final_text, sources=sources, usage=usage_totals)


def call_plain(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str,
    max_tokens: int = 16000,
) -> LlmCallResult:
    """Stream a Claude call with no tools. Used for plan synthesis."""
    client = get_client()

    started = time.monotonic()
    logger.info(
        "llm.plain start model=%s max_tokens=%d prompt_chars=%d",
        model, max_tokens, len(user_prompt),
    )
    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=_system_blocks(system_prompt),
        messages=[{"role": "user", "content": user_prompt}],
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
    ) as stream:
        response = stream.get_final_message()

    text = "".join(b.text for b in response.content if getattr(b, "type", None) == "text")
    u = response.usage
    usage = {
        k: getattr(u, k, 0) or 0
        for k in (
            "input_tokens",
            "output_tokens",
            "cache_read_input_tokens",
            "cache_creation_input_tokens",
        )
    }
    logger.info(
        "llm.plain done in %.1fs text_chars=%d %s",
        time.monotonic() - started, len(text), _fmt_usage(usage),
    )
    return LlmCallResult(text=text, sources=[], usage=usage)
