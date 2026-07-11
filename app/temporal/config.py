"""
Temporal configuration — reads from environment via app.config.settings.
"""

from dataclasses import dataclass


@dataclass
class TemporalConfig:
    host: str
    namespace: str
    task_queue: str
    enabled: bool


def get_temporal_config() -> TemporalConfig:
    from app.config import Settings
    env = Settings()
    return TemporalConfig(
        host=env.TEMPORAL_HOST,
        namespace=env.TEMPORAL_NAMESPACE,
        task_queue=env.TEMPORAL_TASK_QUEUE,
        enabled=env.TEMPORAL_ENABLED,
    )
