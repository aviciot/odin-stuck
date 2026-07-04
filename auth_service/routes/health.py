"""
Health Check Routes
===================
Service health and status endpoints.
"""

from datetime import datetime
from fastapi import APIRouter, Response

from config.database import get_db_pool
from models.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
            active_users = await conn.fetchval(
                "SELECT COUNT(*) FROM auth_service.users WHERE active = true"
            )
        return HealthResponse(
            status="ok",
            service="them-auth-service",
            version="1.0.0",
            timestamp=datetime.utcnow().isoformat(),
            database="connected",
            active_users=active_users,
        )
    except Exception as e:
        return HealthResponse(
            status="degraded",
            service="them-auth-service",
            version="1.0.0",
            timestamp=datetime.utcnow().isoformat(),
            database=f"error: {str(e)}",
        )


@router.get("/health/live")
async def health_live():
    return {"status": "ok"}


@router.get("/health/ready")
async def health_ready():
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {"status": "ok"}
    except Exception as e:
        return Response(content=f"db error: {e}", status_code=503)


@router.get("/info")
async def service_info():
    return {
        "service": "Odin Auth Service",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "health_live": "/health/live",
            "health_ready": "/health/ready",
            "login": "/login",
            "validate": "/validate",
            "refresh": "/refresh",
            "logout": "/logout",
            "users": "/users",
            "roles": "/roles",
        },
    }
