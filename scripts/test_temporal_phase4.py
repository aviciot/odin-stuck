"""
Phase 4 validation: context injection for typed vs text agents.

Tests:
1. Text agent (a2a_echo): context prepended to message
2. Typed agent (mock with input_schema): context injected as __context__ key
3. No context: tool_input passed through unchanged
"""

import asyncio
import sys

sys.path.insert(0, "/app")


def test_context_injection():
    from app.temporal.serde import build_agent_tool_input

    # Test 1: text agent, no schema, with context
    result = build_agent_tool_input(
        tool_call_input={"message": "hello"},
        input_schema=None,
        injected_context="prior context here",
    )
    assert result["message"].startswith("[Context summary]"), f"Expected context prepend, got: {result['message']}"
    assert "prior context here" in result["message"], f"Context missing from message: {result['message']}"
    assert "hello" in result["message"], f"Original message missing: {result['message']}"
    print("[PASS] text agent: context prepended to message")

    # Test 2: typed agent (has schema properties), with context
    typed_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "mode": {"type": "string"},
        },
        "required": ["query"],
    }
    result2 = build_agent_tool_input(
        tool_call_input={"query": "analyze this", "mode": "fast"},
        input_schema=typed_schema,
        injected_context="typed context here",
    )
    assert result2.get("__context__") == "typed context here", f"Expected __context__ key, got: {result2}"
    assert result2["query"] == "analyze this", f"query field modified unexpectedly: {result2}"
    print("[PASS] typed agent: context injected as __context__ key")

    # Test 3: no context, text agent
    result3 = build_agent_tool_input(
        tool_call_input={"message": "no context"},
        input_schema=None,
        injected_context=None,
    )
    assert result3 == {"message": "no context"}, f"Expected unchanged input, got: {result3}"
    print("[PASS] no context: tool_input passed through unchanged")

    # Test 4: no context, typed agent
    result4 = build_agent_tool_input(
        tool_call_input={"query": "something"},
        input_schema=typed_schema,
        injected_context=None,
    )
    assert result4 == {"query": "something"}, f"Expected unchanged typed input, got: {result4}"
    assert "__context__" not in result4, f"__context__ should not be injected with no context: {result4}"
    print("[PASS] typed agent, no context: tool_input unchanged, no __context__ key")

    # Test 5: text agent with no message key (edge case)
    result5 = build_agent_tool_input(
        tool_call_input={"other_field": "value"},
        input_schema=None,
        injected_context="some context",
    )
    # No message key → context not prepended (can't know where to inject)
    assert "__context__" not in result5, f"Unexpected __context__ in text agent result: {result5}"
    assert result5 == {"other_field": "value"}, f"Non-message text agent input modified: {result5}"
    print("[PASS] text agent, no message key: input unchanged (no injection point)")


async def test_invoke_agent_uses_effective_input():
    """Verify invoke_agent_activity applies context injection before adapter call."""
    import inspect
    import app.temporal.activities as acts

    src = inspect.getsource(acts.invoke_agent_activity)
    assert "build_agent_tool_input" in src, "invoke_agent_activity must call build_agent_tool_input"
    assert "effective_input" in src, "invoke_agent_activity must use effective_input for adapter"
    assert "tool_start" in src, "invoke_agent_activity must publish tool_start event"
    print("[PASS] invoke_agent_activity: calls build_agent_tool_input + tool_start")


if __name__ == "__main__":
    print("=== Phase 4: Context Injection Validation ===")
    test_context_injection()

    loop = asyncio.new_event_loop()
    loop.run_until_complete(test_invoke_agent_uses_effective_input())
    loop.close()

    print("\n[ALL PASS] Phase 4 context injection validated")
