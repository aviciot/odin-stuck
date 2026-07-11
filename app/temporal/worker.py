"""
Temporal worker entrypoint — hosts all Workflow and Activity definitions.

Run via:  python -m app.temporal.worker
Or via:   Dockerfile.worker (CMD ["python", "-m", "app.temporal.worker"])
"""

import asyncio
import sys

from temporalio.worker import UnsandboxedWorkflowRunner, Worker

from app.temporal.activities import ALL_ACTIVITIES
from app.temporal.client import get_temporal_client
from app.temporal.config import get_temporal_config
from app.temporal.workflows import OrchestrationWorkflow
from app.utils.logger import logger

WORKFLOWS: list = [OrchestrationWorkflow]
ACTIVITIES: list = ALL_ACTIVITIES


async def main() -> None:
    # Initialize DB + Redis once at worker startup so all activities share the pool.
    import app.database as db_module
    await db_module.init_db()

    cfg = get_temporal_config()
    client = await get_temporal_client()

    logger.info(
        "temporal_worker: starting",
        task_queue=cfg.task_queue,
        namespace=cfg.namespace,
        workflows=len(WORKFLOWS),
        activities=len(ACTIVITIES),
    )

    worker = Worker(
        client,
        task_queue=cfg.task_queue,
        workflows=WORKFLOWS,
        activities=ACTIVITIES,
        max_concurrent_activities=20,
        max_concurrent_workflow_tasks=50,
        workflow_runner=UnsandboxedWorkflowRunner(),
    )

    logger.info("temporal_worker: polling", task_queue=cfg.task_queue)
    try:
        await worker.run()
    finally:
        await db_module.close_db()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("temporal_worker: shutting down")
        sys.exit(0)
