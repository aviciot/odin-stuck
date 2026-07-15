"""
bridge_client — the bridge's interface to Temporal.

Provides two functions:
  start_orchestration_workflow() — starts or resumes an OrchestrationWorkflow
  stream_run_events()           — subscribes to Redis side-channel and forwards events

Used by ws_orchestrator.py and apps.py when TEMPORAL_ENABLED=true.
"""

import asyncio
import json
import uuid
from typing import Callable, Coroutine, Optional

from temporalio.client import WorkflowHandle, WorkflowExecutionStatus
from temporalio.exceptions import WorkflowAlreadyStartedError

import app.database as db_module
from app.temporal.client import get_temporal_client
from app.temporal.shared import OrchestrationInput
from app.temporal.workflows import OrchestrationWorkflow
from app.utils.logger import logger


class DeadContextError(Exception):
    """Raised when a client resends a context_id whose workflow already closed/failed.
    The caller must discard that context_id and tell the client to start fresh."""

_TASK_QUEUE = None  # resolved lazily


def _get_task_queue() -> str:
    global _TASK_QUEUE
    if _TASK_QUEUE is None:
        from app.temporal.config import get_temporal_config
        _TASK_QUEUE = get_temporal_config().task_queue
    return _TASK_QUEUE


_DASH_RUN_PREFIX = "them:dash:run:"


async def start_orchestration_workflow(
    *,
    orchestrator_name: str,
    user_message: str,
    user_id: int,
    token_payload: dict,
    context_id: uuid.UUID,
    session_id: uuid.UUID,
    history_window: int = 20,
    entry_point_slug: Optional[str] = None,
) -> tuple[WorkflowHandle, str, object]:
    """
    Start or signal-resume an OrchestrationWorkflow for the given context_id.

    Workflow ID = f"ctx-{context_id}" — one per conversation thread.

    Returns (workflow_handle, workflow_id, pubsub) where pubsub is already
    subscribed to the context channel BEFORE the workflow starts — this
    eliminates the race where a fast workflow publishes its ready event
    before stream_run_events has a chance to subscribe.

    Pass the returned pubsub directly to stream_run_events(..., pubsub=pubsub).
    The pubsub is closed by stream_run_events when own_pubsub=False and the
    caller passes it in; here we return it and the caller is responsible via
    stream_run_events closing it. Actually stream_run_events only closes if
    own_pubsub — so caller must close on error paths. See error handling below.
    """
    client = await get_temporal_client()
    workflow_id = f"ctx-{context_id}"
    task_queue = _get_task_queue()
    ctx_channel = f"{_DASH_RUN_PREFIX}{context_id}:ctx"

    # Subscribe BEFORE starting the workflow so we never miss the ready event.
    pubsub = None
    if db_module.redis_client is not None:
        pubsub = db_module.redis_client.pubsub()
        await pubsub.subscribe(ctx_channel)

    inp = OrchestrationInput(
        orchestrator_name=orchestrator_name,
        user_message=user_message,
        user_id=user_id,
        token_payload=token_payload,
        session_id=str(session_id),
        context_id=str(context_id),
        history_window=history_window,
        entry_point_slug=entry_point_slug,
    )

    try:
        handle = await client.start_workflow(
            OrchestrationWorkflow.run,
            inp,
            id=workflow_id,
            task_queue=task_queue,
        )
        logger.info(
            "bridge_client: workflow started",
            workflow_id=workflow_id,
            orchestrator=orchestrator_name,
        )
    except WorkflowAlreadyStartedError:
        handle = client.get_workflow_handle(workflow_id)
        # Part B: check whether the existing workflow is still running.
        # If it closed (completed, failed, cancelled, terminated, timed out),
        # the context_id is dead — re-attaching would stream nothing or the
        # old failure. Raise DeadContextError so the caller can tell the client
        # to discard this context_id and start fresh.
        try:
            desc = await handle.describe()
            status = desc.status
            _CLOSED = {
                WorkflowExecutionStatus.COMPLETED,
                WorkflowExecutionStatus.FAILED,
                WorkflowExecutionStatus.CANCELED,
                WorkflowExecutionStatus.TERMINATED,
                WorkflowExecutionStatus.TIMED_OUT,
            }
            if status in _CLOSED:
                logger.warning(
                    "bridge_client: context workflow is closed — rejecting reuse",
                    workflow_id=workflow_id,
                    status=str(status),
                )
                raise DeadContextError(
                    f"Context {context_id} points to a closed workflow ({status}). "
                    "Start a new conversation."
                )
        except DeadContextError:
            raise
        except Exception as desc_exc:
            # describe() failed (e.g. workflow not found at all) — also dead
            logger.warning(
                "bridge_client: could not describe existing workflow — treating as dead",
                workflow_id=workflow_id,
                error=str(desc_exc),
            )
            raise DeadContextError(
                f"Context {context_id} is no longer valid. Start a new conversation."
            )
        logger.info("bridge_client: attached to existing workflow", workflow_id=workflow_id)

    return handle, workflow_id, pubsub


async def stream_run_events(
    context_id: str,
    workflow_handle: WorkflowHandle,
    emit_fn: Callable[[dict], Coroutine],
    cancel_event: Optional[asyncio.Event] = None,
    pubsub=None,  # pre-subscribed pubsub handle (avoids ready-event race)
) -> None:
    """
    Stream events from a running OrchestrationWorkflow to the WS client.

    Phase 1: Subscribe to context channel (them:dash:run:{context_id}:ctx) to
    receive the ready event and extract run_id.
    Phase 2: Subscribe to run channel (them:dash:run:{run_id}:tokens) for all
    subsequent events.

    Terminates when a terminal event (done/error) arrives or workflow completes.
    Always emits the final done/error from workflow_handle.result() as a guarantee.

    IMPORTANT: pass a pre-subscribed pubsub (created before start_workflow) to
    avoid the race where a fast workflow publishes ready before we subscribe.
    """
    if db_module.redis_client is None:
        logger.warning("bridge_client: Redis not available — waiting for workflow result only")
        try:
            result = await workflow_handle.result()
            if result.get("status") == "completed":
                await emit_fn({"type": "done", "run_id": "", "task_id": result.get("root_task_id", ""), "iterations": result.get("iterations", 0)})
            else:
                await emit_fn({"type": "error", "message": result.get("error") or "Run failed"})
        except Exception as exc:
            await emit_fn({"type": "error", "message": str(exc)})
        return

    ctx_channel = f"{_DASH_RUN_PREFIX}{context_id}:ctx"
    run_id: list[str] = []
    terminal_received = False

    # Use the pre-subscribed pubsub if provided; otherwise create one now.
    # Creating one now risks missing the ready event if the workflow is fast.
    own_pubsub = pubsub is None
    if own_pubsub:
        pubsub = db_module.redis_client.pubsub()
        await pubsub.subscribe(ctx_channel)

    try:
        # Phase 1: wait for ready event on context channel
        ready_timeout = 15  # seconds to wait for run to start
        ready_deadline = asyncio.get_event_loop().time() + ready_timeout
        async for message in pubsub.listen():
            if message["type"] != "message":
                if asyncio.get_event_loop().time() > ready_deadline:
                    await emit_fn({"type": "error", "message": "Timed out waiting for workflow to start"})
                    return
                continue
            try:
                event = json.loads(message["data"])
            except (json.JSONDecodeError, TypeError):
                continue

            if event.get("type") == "ready":
                run_id_str = event.get("run_id", "")
                if run_id_str:
                    run_id.append(run_id_str)
                await emit_fn(event)
                break

            if asyncio.get_event_loop().time() > ready_deadline:
                await emit_fn({"type": "error", "message": "Timed out waiting for workflow ready event"})
                return

        await pubsub.unsubscribe(ctx_channel)

        if not run_id:
            await emit_fn({"type": "error", "message": "No run_id received from workflow"})
            return

        # Phase 2: subscribe to run-specific token channel
        run_channel = f"{_DASH_RUN_PREFIX}{run_id[0]}:tokens"
        await pubsub.subscribe(run_channel)

        async def _reader():
            nonlocal terminal_received
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    event = json.loads(message["data"])
                except (json.JSONDecodeError, TypeError):
                    continue
                event_type = event.get("type")
                try:
                    await emit_fn(event)
                except Exception:
                    break
                if event_type in ("done", "error"):
                    terminal_received = True
                    break
                if cancel_event and cancel_event.is_set():
                    break

        reader_task = asyncio.ensure_future(_reader())
        workflow_result_task = asyncio.ensure_future(workflow_handle.result())

        done_set, pending = await asyncio.wait(
            [reader_task, workflow_result_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for t in pending:
            t.cancel()
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass

        # Guarantee terminal event if Redis dropped it
        if workflow_result_task in done_set and not terminal_received:
            try:
                result = workflow_result_task.result()
                if result.get("status") == "completed":
                    await emit_fn({
                        "type": "done",
                        "run_id": run_id[0],
                        "task_id": result.get("root_task_id", ""),
                        "iterations": result.get("iterations", 0),
                    })
                else:
                    await emit_fn({"type": "error", "message": result.get("error") or "Run failed"})
            except Exception as exc:
                await emit_fn({"type": "error", "message": str(exc)})

        await pubsub.unsubscribe(run_channel)

    finally:
        if own_pubsub:
            try:
                await pubsub.aclose()
            except Exception:
                pass


async def cancel_workflow(workflow_id: str) -> None:
    """Cancel a running workflow by its ID."""
    try:
        client = await get_temporal_client()
        handle = client.get_workflow_handle(workflow_id)
        await handle.cancel()
        logger.info("bridge_client: workflow cancelled", workflow_id=workflow_id)
    except Exception as exc:
        logger.warning("bridge_client: cancel failed", workflow_id=workflow_id, error=str(exc))
