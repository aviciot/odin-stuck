"""Health check endpoints."""

from fastapi import APIRouter, Response
from sqlalchemy import text

from app.config import settings
import app.database as db_module

router = APIRouter()


@router.get("/health")
async def health():
    db_status, redis_status = "ok", "ok"

    try:
        if db_module.engine is None:
            raise RuntimeError("engine not initialized")
        async with db_module.engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    try:
        if db_module.redis_client is None:
            raise RuntimeError("redis not initialized")
        await db_module.redis_client.ping()
    except Exception:
        redis_status = "error"

    overall = "ok" if db_status == "ok" and redis_status == "ok" else "degraded"
    return {
        "status": overall,
        "db": db_status,
        "redis": redis_status,
        "redis_db": settings.redis.db,
        "instance_id": settings.instance_id,
    }


@router.get("/health/ready")
async def health_ready():
    try:
        if db_module.engine is None:
            raise RuntimeError("engine not initialized")
        async with db_module.engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        return Response(content=f"db error: {e}", status_code=503)


@router.get("/health/live")
async def health_live():
    return {"status": "ok", "instance_id": settings.instance_id}
