import re
from typing import Any, AsyncGenerator, Dict, List, Tuple

from app.adapters.base import AdapterEvent
from app.middleware.base import CallNext, Middleware, MiddlewareContext
from app.utils.logger import logger

_DEFAULT_ON_BLOCK = "This request was blocked by a safety guard."

_PII_PATTERNS: Dict[str, re.Pattern] = {
    "EMAIL": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "CREDIT_CARD": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
    "SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "PHONE": re.compile(r"\b(?:\+?\d{1,3}[ .-]?)?(?:\(?\d{3}\)?[ .-]?)\d{3}[ .-]?\d{4}\b"),
}

_PII_REDACT_ORDER: List[str] = ["EMAIL", "SSN", "CREDIT_CARD", "PHONE"]

_INJECTION_KEYWORDS: List[str] = [
    "ignore previous instructions",
    "ignore all previous instructions",
    "disregard system prompt",
    "disregard the system prompt",
    "disregard previous instructions",
    "forget previous instructions",
    "you are now",
    "jailbreak",
    "developer mode",
    "override your instructions",
    "reveal your system prompt",
    "print your system prompt",
    "act as an unrestricted",
]


class GuardMiddleware(Middleware):
    kind = "guard"

    def _text_of(self, input: Dict[str, Any]) -> str:
        val = input.get("message")
        return val if isinstance(val, str) else ""

    def _detect_injection(self, text: str) -> List[str]:
        low = text.lower()
        return [kw for kw in _INJECTION_KEYWORDS if kw in low]

    def _detect_pii(self, text: str, entities: List[str]) -> List[str]:
        found: List[str] = []
        for ent in _PII_REDACT_ORDER:
            if ent not in entities:
                continue
            if _PII_PATTERNS[ent].search(text):
                found.append(ent)
        return found

    def _redact_pii(self, text: str, entities: List[str]) -> Tuple[str, List[str]]:
        redacted = text
        hit: List[str] = []
        for ent in _PII_REDACT_ORDER:
            if ent not in entities:
                continue
            pattern = _PII_PATTERNS[ent]
            if pattern.search(redacted):
                hit.append(ent)
                redacted = pattern.sub(f"[REDACTED:{ent}]", redacted)
        return redacted, hit

    async def process(
        self,
        input: Dict[str, Any],
        ctx: MiddlewareContext,
        call_next: CallNext,
    ) -> AsyncGenerator[AdapterEvent, None]:
        cfg = self.config
        mode: str = cfg.get("mode", "redact")
        checks: List[str] = cfg.get("checks", ["pii", "prompt_injection"])
        entities: List[str] = cfg.get("pii_entities", ["EMAIL", "PHONE", "CREDIT_CARD", "SSN"])
        on_block: str = cfg.get("on_block_message", _DEFAULT_ON_BLOCK)

        text = self._text_of(input)

        if "prompt_injection" in checks and text:
            inj = self._detect_injection(text)
            if inj:
                logger.info("guard: prompt_injection detected", agent=ctx.agent_slug, run_id=ctx.run_id, matches=inj)
                yield self._refuse(on_block, reason="prompt_injection")
                return

        if "pii" in checks and text:
            if mode == "block":
                found = self._detect_pii(text, entities)
                if found:
                    logger.info("guard: pii blocked", agent=ctx.agent_slug, run_id=ctx.run_id, entities=found)
                    yield self._refuse(on_block, reason="pii")
                    return
            else:
                redacted, hit = self._redact_pii(text, entities)
                if hit:
                    logger.info("guard: pii redacted", agent=ctx.agent_slug, run_id=ctx.run_id, entities=hit)
                    input = {**input, "message": redacted}

        async for ev in call_next(input):
            yield ev
