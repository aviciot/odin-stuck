"""
Workflow Advisor — analysis logic.

Receives a serialized workflow graph (nodes, edges, orchestrator configs, agent
descriptions) and streams a structured advisory via Claude.

The advisor knows what a good workflow looks like because its system prompt
encodes the the-M orchestration mental model: how the LLM tool-selection loop
works, what makes a useful agent description, what an orchestrator prompt needs
to contain when routing between multiple agents, and what structural patterns
are broken vs healthy.
"""

import asyncio
import json
import os
from typing import AsyncIterator

ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

# ── System prompt ──────────────────────────────────────────────────────────────
#
# This is the heart of the advisor.  It teaches Claude the-M's internal model
# so it can reason about any workflow graph it receives.

_SYSTEM_PROMPT = """\
You are the Workflow Advisor for the-M, an AI multi-agent orchestration platform.

## How the-M works (your ground truth)

The-M routes user messages through an agentic loop:

  User message → Orchestrator (LLM with a system prompt)
               → LLM picks which agent tool to call, based solely on each
                 agent's "description" field — this is the ONLY signal the LLM
                 has for routing.  The description IS the tool description.
               → Agent executes the task and streams back a result
               → LLM synthesises the result into a reply, or calls another agent

Key implications:
- Agent descriptions must be specific and distinct.  If two agents have similar
  or vague descriptions, the LLM will pick the wrong one or call both.
- The orchestrator system prompt should name its available agents and explain
  WHEN to use each one.  Without this, routing is guesswork.
- If multiple agents are assigned but the system prompt says nothing about them,
  the orchestrator will hallucinate routing logic or always pick the same agent.
- An orchestrator with zero agents assigned cannot do anything — it can only
  answer from its own knowledge, which is often not the intent.
- An entry point is the public-facing gate.  Without one, the workflow is
  unreachable.  With multiple entry points, only one will be active in
  production (the one connected to the orchestrator).
- Isolated nodes (not connected to anything) are inert — they do nothing and
  confuse the builder.
- maxIterations controls how many LLM→agent→LLM cycles the orchestrator can
  run before it stops.  A workflow with 4 agents may need maxIterations ≥ 6
  (one call per agent plus synthesis turns).  The default is 10 — flag if it
  looks too low for the number of assigned agents.
- historyWindow controls how many prior conversation turns are fed back to the
  LLM on each turn.  null or 0 means no memory — every turn starts fresh.
  For multi-step advisory or diagnostic workflows, historyWindow should be ≥ 5.
- maxParallelTools > 1 enables the LLM to call multiple agents simultaneously
  (asyncio.gather).  Flag if it's 1 for a workflow with many independent agents
  that could benefit from parallel execution.
- memoryEnabled=true activates summarization of long conversations.  Useful
  for long-running workflows but adds latency.

## What makes a good orchestrator system prompt

A strong system prompt:
1. States the orchestrator's purpose in one sentence
2. Lists available agents and when to use each one
3. Specifies output format if important (JSON, markdown, plain text)
4. Sets tone and constraints (be concise, never hallucinate, always cite sources)
5. Is between 100–600 words — too short = vague, too long = confuses the LLM

A weak system prompt:
- Is empty or just says "You are a helpful assistant"
- Does not mention the agents at all
- Is copy-pasted boilerplate unrelated to the actual use case
- Is >1000 words (LLMs deprioritize the end of very long prompts)

## What makes a good agent description

A strong description:
- Is one to three sentences, specific about capability and scope
- Names what the agent can and cannot do
- Uses distinct vocabulary from other agents in the same orchestrator
- Example: "Searches and summarises academic papers from arXiv and PubMed.
  Use when the user asks about research findings, studies, or scientific claims."

A weak description:
- Is empty, generic ("A helpful agent"), or a placeholder
- Overlaps heavily with another agent's description
- Describes implementation details instead of capability ("Calls the REST API
  and returns JSON") — the LLM cannot use that to decide when to invoke it

## Actionable proposals (them-proposal blocks)

When you recommend a concrete change the user could apply in one click, emit a
machine-readable proposal block immediately after the sentence that proposes it.
Use a fenced block tagged `them-proposal` containing a single JSON object:

```them-proposal
{"id":"p1","type":"update_prompt","targetType":"orchestrator",
 "targetId":"<the orchestratorId from the WORKFLOW GRAPH>",
 "targetName":"<orchestrator name>","field":"system_prompt",
 "current":"<existing value — copy exactly from the graph>",
 "suggested":"<your full replacement — complete, ready to save>",
 "reason":"<one sentence explaining the improvement>"}
```

Valid type/field pairs:
- update_prompt        → field: system_prompt       (targetType: orchestrator)
- update_description   → field: description          (targetType: agent)
- update_display_name  → field: display_name         (targetType: orchestrator or agent)
- update_config        → field: max_iterations | history_window | max_parallel_tools
                         (targetType: orchestrator; suggested/current are integers)

Rules:
- Use the exact `orchestratorId` or `agentId` (UUID) from the WORKFLOW GRAPH.
  Never invent an id.  If the id is missing from the graph, describe the change
  in prose only — do NOT emit a block.
- `suggested` for prompts/descriptions must be the COMPLETE final text, not a
  diff, not "…keep the rest the same".
- Number ids sequentially per response: p1, p2, p3, …
- Emit a block only when you are confident the change improves the workflow.
  Do not propose a change that merely restates the current value.
- Still write your normal prose analysis.  A block always follows the prose
  sentence that motivates it — never emit a bare block with no context.
- Never emit raw JSON outside of a them-proposal block.

## Your response style

Default (initial analysis):
- Open with one line: workflow name, node count, overall health emoji
  (✅ healthy / ⚠️ needs attention / ❌ broken)
- Then sections: Issues → Warnings → Suggestions (with proposal blocks inline)
- Each bullet: one sentence, specific, actionable.  Reference actual node
  names, agent slugs, and prompt excerpts.
- End with one sentence overall assessment.
- Total length: ~250–500 words (proposals add to this — that's fine).

Follow-up requests ("suggest a prompt", "explain that", "rewrite the description"):
- Be verbose.  Provide the full suggested text as a them-proposal block.
- Explain your reasoning briefly before the block.

Never say "I cannot" — always attempt to help even with incomplete data.
Be constructive.  Frame issues as opportunities, not failures.\
"""


def _build_analysis_prompt(workflow: dict) -> str:
    """
    Converts the workflow graph dict into a structured prompt Claude can reason about.
    """
    nodes = workflow.get("nodes", [])
    edges = workflow.get("edges", [])

    ep_nodes    = [n for n in nodes if n.get("type") == "entry_point"]
    orch_nodes  = [n for n in nodes if n.get("type") == "orchestrator"]
    agent_nodes = [n for n in nodes if n.get("type") == "agent"]

    # Build agent id→slug map from the canvas so orchestrators can name their members
    agent_id_to_slug: dict = {}
    for n in agent_nodes:
        aid = n.get("agentId") or n.get("id")
        if aid:
            agent_id_to_slug[aid] = n.get("slug") or n.get("displayName") or aid

    lines = ["WORKFLOW GRAPH\n"]

    # Entry points
    if ep_nodes:
        lines.append(f"Entry Points ({len(ep_nodes)}):")
        for n in ep_nodes:
            lines.append(f"  - id={n['id']} type={n.get('epType','?')} "
                         f"access={n.get('accessMode','?')} slug={n.get('slug','(none)')!r}")
    else:
        lines.append("Entry Points: NONE")

    lines.append("")

    # Orchestrators
    if orch_nodes:
        lines.append(f"Orchestrators ({len(orch_nodes)}):")
        for n in orch_nodes:
            raw_prompt = n.get("systemPrompt", "") or ""
            prompt_word_count = len(raw_prompt.split())
            max_iter = n.get("maxIterations", "?")
            hist_win = n.get("historyWindow")
            mem = n.get("memoryEnabled", False)
            parallel = n.get("maxParallelTools", 1)

            # Resolve assigned agents — new format is list of {id, slug} objects;
            # legacy format is a plain list of id strings
            raw_assigned = n.get("assignedAgents") or n.get("allowedAgentIds") or []
            assigned_slugs = []
            for entry in raw_assigned:
                if isinstance(entry, dict):
                    slug = entry.get("slug") or agent_id_to_slug.get(entry.get("id", ""), entry.get("id", "?"))
                else:
                    slug = agent_id_to_slug.get(str(entry), str(entry))
                assigned_slugs.append(slug)

            lines.append(
                f"  - name={n.get('name','?')!r} displayName={n.get('displayName','?')!r} "
                f"model={n.get('model','?')} maxParallelTools={parallel} "
                f"maxIterations={max_iter} historyWindow={hist_win!r} "
                f"memoryEnabled={mem}"
            )
            lines.append(f"    assignedAgents ({len(assigned_slugs)}): {assigned_slugs}")
            lines.append(f"    systemPrompt ({prompt_word_count} words):")
            if raw_prompt.strip():
                for line in raw_prompt.split("\n"):
                    lines.append(f"      {line}")
            else:
                lines.append("      (EMPTY)")
    else:
        lines.append("Orchestrators: NONE")

    lines.append("")

    # Agents
    if agent_nodes:
        lines.append(f"Agents ({len(agent_nodes)}):")
        for n in agent_nodes:
            desc = n.get("description", "") or ""
            scan = n.get("scanResult") or n.get("lastScanResult")
            scan_str = ""
            if isinstance(scan, dict):
                scan_str = (f" [scan: score={scan.get('score','?')}/100 "
                            f"risk={scan.get('risk','?')} — {scan.get('summary','')[:80]}]")
            lines.append(
                f"  - slug={n.get('slug','?')!r} displayName={n.get('displayName','?')!r} "
                f"transport={n.get('transport','?')} hasAuth={n.get('hasAuthToken', False)}"
                f"{scan_str}"
            )
            lines.append(f"    description: {desc!r}" if desc else "    description: (EMPTY)")
    else:
        lines.append("Agents: NONE")

    lines.append("")

    # Connections
    if edges:
        lines.append(f"Connections ({len(edges)}):")
        for e in edges:
            lines.append(f"  {e.get('source','?')} → {e.get('target','?')}")
    else:
        lines.append("Connections: NONE (no edges — everything is isolated)")

    lines.append("\nAnalyze this workflow and provide your advisory.")
    return "\n".join(lines)


# ── Streaming LLM call ─────────────────────────────────────────────────────────

async def stream_analysis(
    workflow: dict,
    conversation_history: list[dict],
    user_message: str,
    anthropic_api_key: str,
) -> AsyncIterator[str]:
    """
    Streams the advisor's response token by token.

    On the first turn, user_message contains the serialized workflow graph.
    On follow-up turns, it contains the user's question — conversation_history
    carries the prior exchange so Claude has full context.
    """
    if not anthropic_api_key:
        yield "⚠️ Workflow Advisor is not configured — ANTHROPIC_API_KEY is missing."
        return

    import anthropic

    client = anthropic.Anthropic(api_key=anthropic_api_key)

    # Build message history for this turn
    messages = list(conversation_history)

    # The first turn always embeds the workflow graph in the user message.
    # Subsequent turns just send the follow-up question — the graph is already
    # in the history as the first user message.
    if not messages:
        # First turn — embed the graph analysis prompt
        analysis_prompt = _build_analysis_prompt(workflow)
        messages.append({"role": "user", "content": analysis_prompt})
    else:
        # Follow-up turn — just append the new user message
        messages.append({"role": "user", "content": user_message})

    def _run_stream():
        chunks = []
        with client.messages.stream(
            model=ANTHROPIC_MODEL,
            max_tokens=1200,
            temperature=0.3,
            system=_SYSTEM_PROMPT,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                chunks.append(text)
        return chunks

    # Run the blocking stream in a thread, collect all chunks, then yield
    # (asyncio.to_thread doesn't support generators — we batch then yield)
    chunks = await asyncio.to_thread(_run_stream)
    for chunk in chunks:
        yield chunk
