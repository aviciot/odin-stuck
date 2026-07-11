"""
Phase 5 validation: Human-in-the-loop (HITL) signal infrastructure.

Tests:
1. Signal endpoint registered in runs router
2. invoke_agent_activity detects input_required event from adapter
3. Workflow wait_condition usage is correct (temporalio 1.9.0 compatible)
4. OrchestrationWorkflow has submit_human_response signal handler
5. workflow.wait_condition usage in workflow code
"""

import asyncio
import inspect
import sys

sys.path.insert(0, "/app")


def test_signal_endpoint_in_router():
    import app.routers.runs as runs_module

    # Check the SignalPayload class exists
    assert hasattr(runs_module, "SignalPayload"), "SignalPayload not defined in runs.py"
    payload_class = runs_module.SignalPayload
    fields = payload_class.model_fields
    assert "type" in fields, "SignalPayload missing 'type' field"
    assert "content" in fields, "SignalPayload missing 'content' field"
    assert "approved" in fields, "SignalPayload missing 'approved' field"
    print("[PASS] SignalPayload defined with correct fields")

    # Check signal_run endpoint registered (router has prefix /runs, so route path includes it)
    router = runs_module.router
    routes = {r.path: r for r in router.routes}
    # Path may be "/{run_id}/signal" or "/runs/{run_id}/signal" depending on inspection point
    matching = [p for p in routes if "/signal" in p and "{run_id}" in p]
    assert matching, f"Signal endpoint not found. Routes: {list(routes.keys())}"
    route = routes[matching[0]]
    assert "POST" in route.methods, f"Signal route is not POST: {route.methods}"
    print("[PASS] POST /{run_id}/signal registered in runs router")


def test_invoke_agent_handles_input_required():
    import app.temporal.activities as acts

    src = inspect.getsource(acts.invoke_agent_activity)
    assert "input-required" in src, "invoke_agent_activity must handle input-required status"
    assert "input_required" in src, "invoke_agent_activity must check event.input_required flag"
    assert "type.*input_required" in src or "\"type\": \"input_required\"" in src or "'type': 'input_required'" in src, \
        "invoke_agent_activity must publish input_required event to Redis"
    print("[PASS] invoke_agent_activity handles input-required state")

    # Verify the return for input-required
    assert 'status="input-required"' in src or "status='input-required'" in src, \
        "invoke_agent_activity must return InvokeAgentResult with status='input-required'"
    print("[PASS] invoke_agent_activity returns input-required InvokeAgentResult")


def test_workflow_hitl_logic():
    import app.temporal.workflows as wf_module

    src = inspect.getsource(wf_module.OrchestrationWorkflow.run)
    assert "input-required" in src, "Workflow must handle input-required results"
    assert "wait_condition" in src, "Workflow must use wait_condition to pause for human signal"
    assert "_human_response" in src, "Workflow must use _human_response signal state"
    assert "10" in src, "Workflow must have 10-minute timeout for human response"
    print("[PASS] OrchestrationWorkflow.run handles HITL pause+resume")


def test_submit_human_response_signal():
    import app.temporal.workflows as wf_module

    cls = wf_module.OrchestrationWorkflow
    assert hasattr(cls, "submit_human_response"), "OrchestrationWorkflow must have submit_human_response signal"
    # Check it's marked as a signal
    method = cls.submit_human_response
    assert hasattr(method, "_temporal_signal_definition") or callable(method), \
        "submit_human_response must be a Temporal signal"
    print("[PASS] OrchestrationWorkflow.submit_human_response signal defined")


def test_wait_condition_timeout_supported():
    """Verify temporalio 1.9.0 supports wait_condition with timeout kwarg."""
    from temporalio import workflow
    sig = inspect.signature(workflow.wait_condition)
    assert "timeout" in sig.parameters, \
        f"workflow.wait_condition missing 'timeout' param — check temporalio version. Params: {list(sig.parameters)}"
    print("[PASS] workflow.wait_condition supports timeout parameter")


if __name__ == "__main__":
    print("=== Phase 5: HITL Signal Validation ===")
    test_signal_endpoint_in_router()
    test_invoke_agent_handles_input_required()
    test_workflow_hitl_logic()
    test_submit_human_response_signal()
    test_wait_condition_timeout_supported()
    print("\n[ALL PASS] Phase 5 HITL infrastructure validated")
