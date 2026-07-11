"""
serde — serialization helpers for the Workflow ↔ Activity boundary.

Converts provider-native types to/from plain dicts suitable for Temporal
Event History (JSON-serializable, no ORM objects).
"""

from typing import Optional

from app.services.providers.base import NeutralTool, ToolCall
from app.temporal.shared import AgentConfig, InvokeAgentInput


# ─────────────────────────────────────────────────────────────────────────────
# ToolCall ↔ dict
# ─────────────────────────────────────────────────────────────────────────────

def tool_call_to_dict(tc: ToolCall) -> dict:
    return {"id": tc.id, "name": tc.name, "input": tc.input}


def dict_to_tool_call(d: dict) -> ToolCall:
    return ToolCall(id=d["id"], name=d["name"], input=d["input"])


# ─────────────────────────────────────────────────────────────────────────────
# NeutralTool list build
# ─────────────────────────────────────────────────────────────────────────────

def build_tools_for_agents(agents: list[AgentConfig]) -> list[dict]:
    """Build the tool list (as dicts) that the LLM sees. Each entry = one agent."""
    tools = []
    for a in agents:
        schema = a.input_schema or {}
        if not schema.get("properties"):
            schema = {
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
            }
        tools.append({
            "name": f"agent__{a.slug}",
            "description": (a.description or "").strip(),
            "schema": schema,
        })
    return tools


def dicts_to_neutral_tools(tool_dicts: list[dict]) -> list[NeutralTool]:
    return [NeutralTool(name=t["name"], description=t["description"], schema=t["schema"]) for t in tool_dicts]


# ─────────────────────────────────────────────────────────────────────────────
# Agent tool input builder (ports _run_one context injection logic)
# ─────────────────────────────────────────────────────────────────────────────

def build_agent_tool_input(
    tool_call_input: dict,
    input_schema: Optional[dict],
    injected_context: Optional[str],
) -> dict:
    """
    Apply memory context injection to the tool call input.

    Typed agents (explicit input_schema with properties) receive context
    as a separate __context__ key. Text-only agents get it prepended to
    the message string. Matches task_runner._run_one lines 852-859.
    """
    tc_input = dict(tool_call_input)
    if not injected_context:
        return tc_input

    is_typed = bool((input_schema or {}).get("properties"))
    if is_typed:
        tc_input["__context__"] = injected_context
    elif "message" in tc_input:
        tc_input["message"] = f"[Context summary]\n{injected_context}\n\n{tc_input['message']}"
    return tc_input


# ─────────────────────────────────────────────────────────────────────────────
# InvokeAgentInput builder
# ─────────────────────────────────────────────────────────────────────────────

def make_invoke_input(
    *,
    run_id: str,
    context_id: str,
    root_task_id: str,
    iteration: int,
    agent: AgentConfig,
    tool_call: ToolCall,
    injected_context: Optional[str],
) -> InvokeAgentInput:
    tc_input = build_agent_tool_input(tool_call.input, agent.input_schema, injected_context)
    return InvokeAgentInput(
        run_id=run_id,
        context_id=context_id,
        root_task_id=root_task_id,
        iteration=iteration,
        agent_id=agent.id,
        agent_slug=agent.slug,
        agent_name=agent.name,
        transport=agent.transport,
        endpoint_url=agent.endpoint_url,
        auth_token_encrypted=agent.auth_token_encrypted,
        timeout_seconds=agent.timeout_seconds,
        tool_call_id=tool_call.id,
        tool_call_name=tool_call.name,
        tool_input=tc_input,
        injected_context=injected_context,
        input_schema=agent.input_schema,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Message history serialization for Workflow state
# ─────────────────────────────────────────────────────────────────────────────

def serialize_messages(messages: list) -> list[dict]:
    """
    Serialize provider-native messages for storage in Workflow state.

    The Anthropic provider uses dicts already; we pass them through as-is.
    This is the canonical form for Temporal Event History.
    """
    result = []
    for m in messages:
        if isinstance(m, dict):
            result.append(m)
        else:
            # Fallback for any non-dict message (shouldn't happen with current providers)
            result.append({"role": getattr(m, "role", "user"), "content": str(m)})
    return result


def deserialize_messages(raw: list[dict]) -> list:
    """Reconstruct the provider-native message list from serialized form."""
    return list(raw)
