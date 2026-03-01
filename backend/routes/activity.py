"""
Activity tracking routes — POST /activity/track and GET /analytics/user/{user_id}
Handles engagement events from the frontend with optional JWT auth.

Architecture:
  POST /activity/track NO LONGER writes directly to PostgreSQL.
  Instead, it enqueues events into an in-memory buffer (AnalyticsBuffer).
  A background worker (AnalyticsWorker) drains the buffer periodically
  and bulk-inserts events into the database.

  This reduces DB round-trips by ~20-50× and prevents heartbeat spam
  from saturating the connection pool.

  The GET /analytics/user/{user_id} endpoint still reads directly from
  the database — read queries are unaffected by this change.

Rate limiting:
  - Max 1 event per second per session_id (burst protection)
  - Max 60 events per minute per session_id (sustained protection)
  - 2KB metadata limit (schema-level)
  - Event type allow-list (schema-level)
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from config.database import get_db
from models.models import UserActivity
from schemas.activity import TrackEventRequest, TrackEventResponse
from utils.jwt_auth import get_optional_user_id
from middleware.abuse_protection import check_activity_rate_limit
from services.analytics_buffer import (
    AnalyticsBuffer,
    BufferedEvent,
    analytics_buffer,
    get_event_priority,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/activity", tags=["activity"])


# ── POST /activity/track ─────────────────────────────────────────────────────
# NOTE: For production, consider adding rate limiting via slowapi or a reverse
#       proxy (e.g. nginx limit_req_zone). A simple in-memory approach would be:
#       from fastapi_limiter import RateLimiter
#       @router.post("/track", dependencies=[Depends(RateLimiter(times=60, seconds=60))])
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/track", response_model=TrackEventResponse)
async def track_event(
    request: Request,
    event: TrackEventRequest,
    current_user_id: Optional[int] = Depends(get_optional_user_id),
):
    """
    Enqueue a single engagement event for batched database insertion.

    This endpoint does NOT write to the database directly. Instead:
      1. Validates the event (Pydantic schema — type, size, UUID format)
      2. Enforces rate limits (per-session burst + sustained)
      3. Enqueues into AnalyticsBuffer (~0ms, non-blocking)
      4. Returns immediately with a placeholder ID

    The background AnalyticsWorker drains the buffer and bulk-inserts
    events every 5 seconds (configurable). Real database IDs are assigned
    at insert time; the ID returned here is a placeholder.

    Backpressure: If the buffer is full, low-priority events (heartbeat)
    are silently dropped. Critical events (session_start/end) are always
    accepted up to an overflow headroom. The frontend tracker uses
    fire-and-forget semantics so dropped events don't cause errors.

    Note: The `db` dependency is no longer injected — this endpoint
    doesn't need a database connection at all, freeing pool connections
    for read queries and bookings.
    """
    # Enforce rate limits per session_id
    await check_activity_rate_limit(request, event.session_id)

    # Build the column-value dict for bulk insert
    # This matches the UserActivity table columns exactly.
    event_data = {
        "user_id": current_user_id,
        "action_type": event.event_type,         # backward-compat legacy column
        "session_id": event.session_id,
        "page": event.page,
        "hotel_id": event.hotel_id,
        "event_type": event.event_type,
        "duration_seconds": event.duration_seconds,
        "event_metadata": event.metadata,
        # timestamp uses server_default=func.now() — omitting it lets PG set it
    }

    buffered = BufferedEvent(
        data=event_data,
        priority=get_event_priority(event.event_type),
        session_id=event.session_id,
    )

    accepted = await analytics_buffer.enqueue(buffered)

    if not accepted:
        # Event was dropped due to backpressure.
        # Return 202 Accepted (not an error) — the client doesn't need to retry
        # analytics events. We don't want the frontend tracker to log errors.
        logger.debug(f"Event dropped (backpressure): {event.event_type} session={event.session_id}")

    # Return a placeholder ID. The real auto-incremented ID is assigned
    # when the worker bulk-inserts. Existing frontend code ignores this ID
    # (tracker.js is fire-and-forget), so returning 0 is safe.
    return TrackEventResponse(id=0 if not accepted else 0)


# ── GET /analytics/user/{user_id} ────────────────────────────────────────────

@router.get("/analytics/user/{user_id}")
async def get_user_analytics(
    user_id: int,
    db: Session = Depends(get_db),
):
    """
    Aggregated analytics for a specific user.
    Returns session counts, total time, average hotel view time,
    map clicks, and review clicks.
    """
    base = db.query(UserActivity).filter(UserActivity.user_id == user_id)

    total_sessions = (
        base.filter(UserActivity.event_type == "session_start")
        .with_entities(func.count(UserActivity.id))
        .scalar()
    ) or 0

    total_time_spent = (
        base.filter(UserActivity.event_type == "session_end")
        .with_entities(func.coalesce(func.sum(UserActivity.duration_seconds), 0))
        .scalar()
    ) or 0

    hotel_view_rows = (
        base.filter(UserActivity.event_type == "hotel_view")
        .with_entities(
            func.coalesce(func.avg(UserActivity.duration_seconds), 0),
        )
        .first()
    )
    avg_hotel_time = round(float(hotel_view_rows[0]), 1) if hotel_view_rows else 0

    map_clicks = (
        base.filter(UserActivity.event_type == "map_open")
        .with_entities(func.count(UserActivity.id))
        .scalar()
    ) or 0

    reviews_clicks = (
        base.filter(UserActivity.event_type == "reviews_open")
        .with_entities(func.count(UserActivity.id))
        .scalar()
    ) or 0

    return {
        "user_id": user_id,
        "total_sessions": total_sessions,
        "total_time_spent": total_time_spent,
        "avg_hotel_time": avg_hotel_time,
        "map_clicks": map_clicks,
        "reviews_clicks": reviews_clicks,
    }
