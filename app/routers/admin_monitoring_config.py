"""
Admin — Monitoring Configuration
Stores heatmap thresholds + display settings in them.config["monitoring"].

GET  /api/v1/admin/monitoring-config
PUT  /api/v1/admin/monitoring-config
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app._deps import get_db, require_admin
from app.models import Config

router = APIRouter(prefix="/admin/monitoring-config", tags=["admin-monitoring"])

_CONFIG_KEY = "monitoring"

_DEFAULTS: Dict[str, Any] = {
    # Heatmap intensity thresholds — sessions per node
    "heatmap_low":    1,    # >= this: soft glow
    "heatmap_medium": 10,   # >= this: medium intensity
    "heatmap_high":   50,   # >= this: full bright + strong glow
    # Edge thickness scaling — sessions per edge path
    "edge_thin":      1,    # >= this: 1.5px
    "edge_medium":    10,   # >= this: 3px
    "edge_thick":     50,   # >= this: 5px
    # Max sessions to show in the right panel list before pagination
    "panel_max_sessions": 50,
    # Rolling window for throughput stats (seconds)
    "stats_window_seconds": 300,
}


class MonitoringConfig(BaseModel):
    heatmap_low:           int = 1
    heatmap_medium:        int = 10
    heatmap_high:          int = 50
    edge_thin:             int = 1
    edge_medium:           int = 10
    edge_thick:            int = 50
    panel_max_sessions:    int = 50
    stats_window_seconds:  int = 300


def _load(row: Config | None) -> Dict[str, Any]:
    if row is None or not row.config_value:
        return dict(_DEFAULTS)
    merged = dict(_DEFAULTS)
    merged.update(row.config_value)
    return merged


@router.get("", response_model=MonitoringConfig)
async def get_monitoring_config(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_admin),
) -> MonitoringConfig:
    row = await db.get(Config, _CONFIG_KEY)
    return MonitoringConfig(**_load(row))


@router.put("", response_model=MonitoringConfig)
async def put_monitoring_config(
    body: MonitoringConfig,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_admin),
) -> MonitoringConfig:
    row = await db.get(Config, _CONFIG_KEY)
    data = body.model_dump()
    if row is None:
        db.add(Config(config_key=_CONFIG_KEY, config_value=data))
    else:
        row.config_value = data
    await db.commit()
    return body
