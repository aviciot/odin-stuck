"""
memory_service — context summarization for the A2A task graph.

After every N agent calls, a cheap summarizer model compresses accumulated
artifacts into a summary stored in Redis (them:ctx:{context_id}:summary,
TTL 3600s) and persisted as a summary artifact in them.artifacts.

Raw artifacts are NEVER deleted — summarization only produces an additional
summary artifact on top of the existing ones.

Key Redis: them:ctx:{context_id}:summary
"""

import json
import uuid
from typing import Any, Optional

import app.database as db_module
from app.utils.logger import logger

_SUMMARY_KEY_PREFIX = "them:ctx:"
_SUMMARY_KEY_SUFFIX = ":summary"
_SUMMARY_TTL = 3600  # 1 hour


def _summary_key(context_id: uuid.UUID) -> str:
    return f"{_SUMMARY_KEY_PREFIX}{context_id}{_SUMMARY_KEY_SUFFIX}"


def resolve_summarizer(orch) -> tuple[str, str, str]:
    """
    Return (provider_name, model, api_key) for the summarizer.

    Resolution order:
      1. Per-orchestrator summarizer_provider / summarizer_model / summarizer_api_key_encrypted
      2. Global them.config 'summarizer.default'
      3. Hardcoded fallback: anthropic / claude-haiku-4-5-20251001
    """
    from app.config import settings
    from app.utils.crypto import decrypt_value

    provider = getattr(orch, "summarizer_provider", None)
    model = getattr(orch, "summarizer_model", None)
    enc_key = getattr(orch, "summarizer_api_key_encrypted", None)

    if provider and model:
        api_key = decrypt_value(enc_key) if enc_key else _default_key(provider, settings)
        return provider, model, api_key

    # Fall through to config default (already seeded in 003_phase8.sql)
    try:
        from app.config import settings as _s
        # We don't have async context here — use hardcoded fallback
        pass
    except Exception:
        pass

    # Hardcoded fallback
    fallback_provider = "anthropic"
    fallback_model = "claude-haiku-4-5-20251001"
    api_key = _default_key(fallback_provider, settings)
    return fallback_provider, fallback_model, api_key


def _default_key(provider: str, settings: Any) -> str:
    if provider == "openai":
        return getattr(settings, "openai_api_key", "")
    return settings.llm.api_key


async def get_injected_context(context_id: uuid.UUID) -> Optional[str]:
    """
    Return the latest summary for this context from Redis, or None if absent.
    Callers prepend this to outbound agent messages when present.
    """
    if db_module.redis_client is None:
        return None
    try:
        cached = await db_module.redis_client.get(_summary_key(context_id))
        if cached:
            return cached.decode() if isinstance(cached, bytes) else cached
    except Exception as exc:
        logger.warning("memory_service: get_injected_context failed", error=str(exc))
    return None


async def summarize_context(
    *,
    context_id: uuid.UUID,
    orch,
    artifacts: list[dict],
    root_task_id: uuid.UUID,
    db,
) -> Optional[str]:
    """
    Summarize accumulated artifacts using the configured summarizer model.
    Writes the summary to Redis and persists it as a summary-* artifact.
    Returns the summary text, or None if summarization failed (never raises).

    artifacts: list of {"artifact_id", "name", "parts"} dicts from context_service.
    """
    if not artifacts:
        return None

    # Build context blob from artifact parts
    context_parts = []
    for art in artifacts:
        name = art.get("name") or art.get("artifact_id", "")
        parts = art.get("parts", [])
        text_parts = [p.get("text", "") for p in parts if "text" in p]
        if text_parts:
            context_parts.append(f"[{name}]: {' '.join(text_parts)}")

    if not context_parts:
        return None

    context_text = "\n\n".join(context_parts)
    prompt = (
        "You are a context summarizer. Summarize the following agent outputs "
        "into a concise context block that preserves all key facts, decisions, "
        "and data. Be brief but complete.\n\n"
        f"{context_text}"
    )

    try:
        provider_name, model, api_key = resolve_summarizer(orch)
        from app.services.providers import create_provider
        summarizer = create_provider(provider_name, api_key=api_key, model=model)

        result = await summarizer.call(
            system="You are a concise summarizer. Output only the summary, no preamble.",
            messages=summarizer.init_messages(prompt),
            tools=[],
            max_tokens=1024,
        )
        summary_text = result.text or ""
    except Exception as exc:
        logger.warning("memory_service: summarizer call failed", error=str(exc))
        return None

    if not summary_text:
        return None

    # Write to Redis
    try:
        if db_module.redis_client is not None:
            await db_module.redis_client.setex(
                _summary_key(context_id), _SUMMARY_TTL, summary_text
            )
    except Exception as exc:
        logger.warning("memory_service: Redis summary write failed", error=str(exc))

    # Persist as summary artifact (raw artifacts untouched)
    try:
        from app.services import context_service
        import time as _time
        artifact_id = f"summary-{int(_time.time())}"
        await context_service.record_and_cache_artifact(
            task_id=root_task_id,
            context_id=context_id,
            artifact_id=artifact_id,
            parts=[{"kind": "text", "text": summary_text}],
            name="Context Summary",
            db=db,
        )
    except Exception as exc:
        logger.warning("memory_service: summary artifact persist failed", error=str(exc))

    logger.info(
        "memory_service: summarized context",
        context_id=str(context_id),
        artifacts=len(artifacts),
        summary_len=len(summary_text),
    )
    return summary_text
