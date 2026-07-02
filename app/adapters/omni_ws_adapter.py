"""
OmniWsAdapter — connects to an Omni agentic gateway WebSocket endpoint.

Protocol:
  1. websockets.connect(endpoint_url, Authorization: Bearer <decrypted token>)
  2. Send: {"type": "message", "content": input["message"]}
  3. Parse Omni stream events → AdapterEvent
"""

import asyncio
import json
from typing import AsyncGenerator, Optional

import websockets

from app.adapters.base import AdapterEvent, AgentAdapter
from app.utils.crypto import decrypt_value
from app.utils.logger import logger


class OmniWsAdapter(AgentAdapter):
    def __init__(
        self,
        *,
        agent_slug: str,
        endpoint_url: str,
        auth_token_encrypted: Optional[str],
    ) -> None:
        self._slug = agent_slug
        self._endpoint_url = endpoint_url
        self._auth_token_encrypted = auth_token_encrypted

    async def stream_invoke(
        self,
        input: dict,
        timeout: float,
    ) -> AsyncGenerator[AdapterEvent, None]:
        token = decrypt_value(self._auth_token_encrypted) if self._auth_token_encrypted else ""
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        assembled: list[str] = []

        try:
            async with asyncio.timeout(timeout):
                async with websockets.connect(
                    self._endpoint_url,
                    additional_headers=headers,
                ) as ws:
                    await ws.send(json.dumps({
                        "type": "message",
                        "content": input.get("message", ""),
                    }))

                    async for raw in ws:
                        try:
                            event = json.loads(raw)
                        except json.JSONDecodeError:
                            continue

                        etype = event.get("type")
                        if etype == "token":
                            text = event.get("text", "")
                            assembled.append(text)
                            yield AdapterEvent(type="token", text=text)
                        elif etype == "done":
                            result = "".join(assembled) if assembled else event.get("result", "")
                            yield AdapterEvent(type="done", result=result)
                            return
                        elif etype == "error":
                            msg = event.get("message", "unknown error")
                            yield AdapterEvent(type="error", error=msg)
                            return

        except asyncio.TimeoutError:
            logger.warning("OmniWsAdapter timeout", agent=self._slug, timeout=timeout)
            yield AdapterEvent(type="error", error=f"agent timed out after {timeout}s")
        except Exception as exc:
            logger.error("OmniWsAdapter error", agent=self._slug, error=str(exc))
            yield AdapterEvent(type="error", error=str(exc))
