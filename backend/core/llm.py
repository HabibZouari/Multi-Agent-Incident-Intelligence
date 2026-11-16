"""LLM factory. Returns ``None`` when no API key is configured so callers can degrade gracefully."""

from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from backend.core.config import settings
from backend.core.logger import logger


def build_llm(model: str | None = None, temperature: float = 0.1) -> ChatAnthropic | None:
    if not settings.llm_enabled:
        return None
    return ChatAnthropic(
        model=model or settings.default_model,
        temperature=temperature,
        api_key=settings.anthropic_api_key,
        base_url=settings.anthropic_base_url or None,
        max_tokens=2048,
        timeout=60,
        max_retries=2,
    )


def complete(llm: ChatAnthropic | None, prompt: str) -> str | None:
    """Run a single-prompt completion. Returns ``None`` if the LLM is unavailable or the call fails."""
    if llm is None:
        return None
    try:
        response: Any = llm.invoke([HumanMessage(content=prompt)])
    except Exception as exc:  # noqa: BLE001 - provider/network errors must not crash an investigation
        logger.warning("LLM call failed (%s); using deterministic fallback.", type(exc).__name__)
        return None
    content = response.content
    if isinstance(content, list):  # content blocks
        content = "".join(block.get("text", "") if isinstance(block, dict) else str(block) for block in content)
    return str(content).strip()
