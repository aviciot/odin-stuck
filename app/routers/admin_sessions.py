"""
Admin — Sessions
View and control active WS sessions tracked in Redis by session_manager.

Endpoints:
  GET  /api/v1/admin/sessions?app_id=<uuid>         — sessions for an application
  GET  /api/v1/admin/sessions?ep_slug=<slug>         — sessions for an entry point
  POST /api/v1/admin/sessions/{session_id}/disconnect — terminate a live session
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app._deps import require_admin
from app.services import session_manager

router = APIRouter(prefix="/admin/sessions", tags=["admin-sessions"])


@router.get("")
async def list_sessions(
    app_id: Optional[str] = Query(None, description="Filter by application UUID"),
    ep_slug: Optional[str] = Query(None, description="Filter by entry-point slug"),
    _user: dict = Depends(require_admin),
):
    """Return active sessions for an application or entry point.

    Exactly one of app_id or ep_slug must be provided.
    """
    if app_id:
        session_ids = await session_manager.list_app_sessions(app_id)
    elif ep_slug:
        session_ids = await session_manager.list_ep_sessions(ep_slug)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="app_id or ep_slug required",
        )

    sessions = []
    for sid in session_ids:
        try:
            data = await session_manager.get(uuid.UUID(sid))
        except Exception:
            data = None
        if data is not None:
            sessions.append(data)

    return {"sessions": sessions, "count": len(sessions)}


@router.post("/{session_id}/disconnect")
async def disconnect_session(
    session_id: str,
    _user: dict = Depends(require_admin),
):
    """Send a cross-replica disconnect signal to a live session.

    The per-session control listener on the owning bridge pod will receive the
    signal and close the WebSocket with code 4000 ("terminated by admin").
    Returns 404 if the session is not found in Redis (already ended).
    """
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid session_id")

    data = await session_manager.get(sid)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found or already ended")

    delivered = await session_manager.signal_disconnect(sid)
    return {"session_id": session_id, "signal_delivered": delivered}
