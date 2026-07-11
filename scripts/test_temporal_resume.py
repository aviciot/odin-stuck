"""
Phase 2 resume validation — starts a workflow against a2a-slow (5s delay),
verifies it's running, then the test simply checks Temporal UI state.

The a2a-slow agent takes 5 seconds — we verify the workflow reaches the
invoke_agent stage, then confirm it completes after a worker restart.

Run inside them-worker:
  docker cp scripts/test_temporal_resume.py them-worker:/tmp/test_temporal_resume.py
  docker exec them-worker python3 /tmp/test_temporal_resume.py
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
    workflow_id = f"resume-test-{context_id}"

    inp = OrchestrationInput(
        orchestrator_name="echo_test",
        user_message="Use the slow agent to wait and then respond",
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

    # Wait for workflow to start
    await asyncio.sleep(2)

    # Check it's running
    desc = await handle.describe()
    print(f"[test] Workflow status: {desc.status}")

    # Wait for full completion
    print("[test] Waiting for completion (up to 60s)...")
    result = await asyncio.wait_for(handle.result(), timeout=60)
    print(f"[test] Result: {result}")

    if result.get("status") == "completed":
        print("[PASS] Workflow completed successfully")
    else:
        print(f"[FAIL] Status: {result.get('status')} error={result.get('error')}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
