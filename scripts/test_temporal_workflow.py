"""
Phase 2 validation — runs OrchestrationWorkflow directly against a2a-echo.

Run inside them-worker:
  docker cp scripts/test_temporal_workflow.py them-worker:/tmp/test_temporal_workflow.py
  docker exec them-worker python3 /tmp/test_temporal_workflow.py

Requires:
  - them-worker running with --profile temporal
  - a2a-echo enabled in DB (UPDATE them.agents SET enabled=true WHERE slug='a2a_echo')
  - a2a_test orchestrator in DB with a2a_echo in allowed_agent_ids
"""

import asyncio
import sys
import uuid

sys.path.insert(0, "/app")


async def main():
    from temporalio.client import Client
    from app.temporal.shared import OrchestrationInput
    from app.temporal.workflows import OrchestrationWorkflow

    client = await Client.connect("temporal-frontend:7233", namespace="default")
    print("[test] Connected to Temporal")

    context_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    workflow_id = f"test-ctx-{context_id}"

    inp = OrchestrationInput(
        orchestrator_name="echo_test",
        user_message="Echo back: hello from Temporal Phase 2 test",
        user_id=1,
        token_payload={},
        session_id=session_id,
        context_id=context_id,
    )

    print(f"[test] Starting workflow {workflow_id}")
    handle = await client.start_workflow(
        OrchestrationWorkflow.run,
        inp,
        id=workflow_id,
        task_queue="them-orchestration",
    )
    print(f"[test] Workflow started, waiting for result...")

    result = await asyncio.wait_for(handle.result(), timeout=120)
    print(f"[test] Result: {result}")

    if result.get("status") == "completed":
        print("[PASS] Workflow completed successfully")
    else:
        print(f"[FAIL] Unexpected status: {result.get('status')} error={result.get('error')}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
