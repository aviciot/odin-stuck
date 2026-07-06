"""
Task store — CRUD + state machine for them.tasks, them.artifacts, them.task_messages.

Design rules:
- the-M is the sole writer. Agents never touch these tables directly.
- State transitions are guarded: illegal moves are rejected.
- Every transition publishes to Redis them:tasks:{id}:events for subscribers.
- All errors are caught and logged — callers should not crash if store fails.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

import app.database as db_module
from app.models import Task, Artifact, TaskMessage
from app.utils.logger import logger

# Valid state transitions: from_state → set of allowed to_states
_TRANSITIONS: dict[str, set[str]] = {
    "submitted":      {"working", "canceled", "rejected"},
    "working":        {"input-required", "completed", "failed", "canceled"},
    "input-required": {"working", "canceled"},
    "completed":      set(),  # terminal
    "failed":         set(),  # terminal
    "canceled":       set(),  # terminal
    "rejected":       set(),  # terminal
}

_TERMINAL = {"completed", "failed", "canceled", "rejected"}

_TASK_EVENTS_PREFIX = "them:tasks:"
_TASK_EVENTS_SUFFIX = ":events"


# ─────────────────────────────────────────────────────────────────────────────
# Publish helper
# ─────────────────────────────────────────────────────────────────────────────

async def _publish(task_id: uuid.UUID, event: dict) -> None:
    if db_module.redis_client is None:
        return
    try:
        channel = f"{_TASK_EVENTS_PREFIX}{task_id}{_TASK_EVENTS_SUFFIX}"
        await db_module.redis_client.publish(channel, json.dumps(event))
    except Exception as exc:
        logger.warning("task_store: publish failed", task_id=str(task_id), error=str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# Create task
# ─────────────────────────────────────────────────────────────────────────────

async def create_task(
    db: AsyncSession,
    *,
    context_id: uuid.UUID,
    input_message: dict,
    kind: str = "root",
    run_id: Optional[uuid.UUID] = None,
    parent_task_id: Optional[uuid.UUID] = None,
    orchestrator_id: Optional[uuid.UUID] = None,
    agent_id: Optional[uuid.UUID] = None,
    budget_tokens: Optional[int] = None,
    deadline: Optional[datetime] = None,
    max_depth: int = 5,
    user_id: Optional[int] = None,
) -> Task:
    task = Task(
        id=uuid.uuid4(),
        run_id=run_id,
        parent_task_id=parent_task_id,
        orchestrator_id=orchestrator_id,
        agent_id=agent_id,
        context_id=context_id,
        state="submitted",
        kind=kind,
        input_message=input_message,
        budget_tokens=budget_tokens,
        deadline=deadline,
        max_depth=max_depth,
        tokens_used=0,
        user_id=user_id,
    )
    db.add(task)
    try:
        await db.commit()
        await db.refresh(task)
    except Exception as exc:
        await db.rollback()
        logger.error("task_store: create_task failed", error=str(exc))
        raise

    await _publish(task.id, {
        "type": "task_created",
        "task_id": str(task.id),
        "context_id": str(context_id),
        "kind": kind,
        "state": "submitted",
    })
    return task


# ─────────────────────────────────────────────────────────────────────────────
# Transition state
# ─────────────────────────────────────────────────────────────────────────────

async def transition(
    db: AsyncSession,
    task_id: uuid.UUID,
    new_state: str,
    *,
    error: Optional[str] = None,
    status_message: Optional[dict] = None,
    remote_task_id: Optional[str] = None,
    tokens_used_delta: int = 0,
) -> Task | None:
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        logger.warning("task_store: transition — task not found", task_id=str(task_id))
        return None

    allowed = _TRANSITIONS.get(task.state, set())
    if new_state not in allowed:
        logger.warning(
            "task_store: illegal transition",
            task_id=str(task_id),
            from_state=task.state,
            to_state=new_state,
        )
        return task  # return current state, don't crash

    task.state = new_state
    task.updated_at = datetime.now(timezone.utc)
    if error is not None:
        task.error = error
    if status_message is not None:
        task.status_message = status_message
    if remote_task_id is not None:
        task.remote_task_id = remote_task_id
    if tokens_used_delta > 0:
        task.tokens_used = (task.tokens_used or 0) + tokens_used_delta

    try:
        await db.commit()
        await db.refresh(task)
    except Exception as exc:
        await db.rollback()
        logger.error("task_store: transition commit failed", task_id=str(task_id), error=str(exc))
        return None

    await _publish(task.id, {
        "type": "task_state",
        "task_id": str(task_id),
        "context_id": str(task.context_id),
        "state": new_state,
        "error": error,
    })
    return task


# ─────────────────────────────────────────────────────────────────────────────
# Get task
# ─────────────────────────────────────────────────────────────────────────────

async def get_task(db: AsyncSession, task_id: uuid.UUID) -> Task | None:
    result = await db.execute(select(Task).where(Task.id == task_id))
    return result.scalar_one_or_none()


async def get_tasks_by_context(
    db: AsyncSession,
    context_id: uuid.UUID,
    limit: int = 100,
) -> list[Task]:
    result = await db.execute(
        select(Task)
        .where(Task.context_id == context_id)
        .order_by(Task.created_at)
        .limit(limit)
    )
    return list(result.scalars().all())


# ─────────────────────────────────────────────────────────────────────────────
# Record artifact
# ─────────────────────────────────────────────────────────────────────────────

async def record_artifact(
    db: AsyncSession,
    *,
    task_id: uuid.UUID,
    context_id: uuid.UUID,
    artifact_id: str,
    parts: list[dict],
    name: Optional[str] = None,
    append_index: int = 0,
    last_chunk: bool = True,
) -> Artifact | None:
    artifact = Artifact(
        task_id=task_id,
        context_id=context_id,
        artifact_id=artifact_id,
        name=name,
        parts=parts,
        append_index=append_index,
        last_chunk=last_chunk,
    )
    db.add(artifact)
    try:
        await db.commit()
        await db.refresh(artifact)
    except Exception as exc:
        await db.rollback()
        logger.error("task_store: record_artifact failed", task_id=str(task_id), error=str(exc))
        return None

    await _publish(task_id, {
        "type": "artifact",
        "task_id": str(task_id),
        "context_id": str(context_id),
        "artifact_id": artifact_id,
        "name": name,
        "last_chunk": last_chunk,
    })
    return artifact


# ─────────────────────────────────────────────────────────────────────────────
# Record message
# ─────────────────────────────────────────────────────────────────────────────

async def record_message(
    db: AsyncSession,
    *,
    task_id: uuid.UUID,
    role: str,
    parts: list[dict],
    seq: int,
) -> TaskMessage | None:
    msg = TaskMessage(
        task_id=task_id,
        role=role,
        parts=parts,
        seq=seq,
    )
    db.add(msg)
    try:
        await db.commit()
        await db.refresh(msg)
    except Exception as exc:
        await db.rollback()
        logger.error("task_store: record_message failed", task_id=str(task_id), error=str(exc))
        return None
    return msg


# ─────────────────────────────────────────────────────────────────────────────
# Get artifacts for a context (shared memory read)
# ─────────────────────────────────────────────────────────────────────────────

async def get_context_artifacts(
    db: AsyncSession,
    context_id: uuid.UUID,
    limit: int = 20,
) -> list[Artifact]:
    """Return the most recent completed artifacts for a context_id."""
    result = await db.execute(
        select(Artifact)
        .where(Artifact.context_id == context_id, Artifact.last_chunk == True)
        .order_by(Artifact.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


# ─────────────────────────────────────────────────────────────────────────────
# Update token usage on a task
# ─────────────────────────────────────────────────────────────────────────────

async def add_tokens_used(
    db: AsyncSession,
    task_id: uuid.UUID,
    delta: int,
) -> None:
    try:
        await db.execute(
            update(Task)
            .where(Task.id == task_id)
            .values(
                tokens_used=Task.tokens_used + delta,
                updated_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
    except Exception as exc:
        await db.rollback()
        logger.error("task_store: add_tokens_used failed", task_id=str(task_id), error=str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# Fork-bomb guard
# ─────────────────────────────────────────────────────────────────────────────

async def count_context_tasks(db: AsyncSession, context_id: uuid.UUID) -> int:
    """Count active (non-terminal) tasks in a context. Used for fork-bomb guard."""
    result = await db.execute(
        select(func.count()).select_from(Task).where(
            Task.context_id == context_id,
            Task.state.notin_(["completed", "failed", "canceled"])
        )
    )
    return result.scalar_one()


# ─────────────────────────────────────────────────────────────────────────────
# Ownership check
# ─────────────────────────────────────────────────────────────────────────────

def owns_task(task: Task, user_id: Optional[int]) -> bool:
    """True if user_id owns the task. NULL task.user_id = legacy task, always allowed."""
    if task.user_id is None:
        return True
    return task.user_id == user_id
