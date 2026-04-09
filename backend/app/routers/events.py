import asyncio
import json
import logging
from typing import Dict, Set
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.core.database import User
from app.routers.deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Events"])

# user_id -> set of asyncio.Queue instances (one per open browser tab/connection)
_connections: Dict[int, Set[asyncio.Queue]] = {}


def get_connections() -> Dict[int, Set[asyncio.Queue]]:
    return _connections


async def push_event(user_id: int, event: str, data: dict) -> None:
    """Push an SSE event to all active connections for a user."""
    queues = _connections.get(user_id)
    if not queues:
        return
    message = f"event: {event}\ndata: {json.dumps(data)}\n\n"
    for queue in list(queues):
        try:
            queue.put_nowait(message)
        except asyncio.QueueFull:
            logger.warning(f"SSE queue full for user_id={user_id}, dropping event")


@router.get("/events")
async def sse_events(
    request: Request,
    user: User = Depends(get_current_user),
):
    """
    Server-Sent Events stream for the current user.
    The frontend connects once and receives push notifications (e.g. activities_updated).
    """
    queue: asyncio.Queue = asyncio.Queue(maxsize=20)

    # Register connection
    if user.id not in _connections:
        _connections[user.id] = set()
    _connections[user.id].add(queue)
    logger.info(f"SSE connection opened for user_id={user.id}")

    async def stream():
        try:
            # Send an initial ping so the client knows the connection is live
            yield "event: connected\ndata: {}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield message
                except asyncio.TimeoutError:
                    # Send a keepalive comment to prevent proxy timeouts
                    yield ": keepalive\n\n"
        finally:
            _connections.get(user.id, set()).discard(queue)
            if user.id in _connections and not _connections[user.id]:
                del _connections[user.id]
            logger.info(f"SSE connection closed for user_id={user.id}")

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx/Caddy buffering
        },
    )
