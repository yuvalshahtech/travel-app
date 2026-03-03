"""
Pydantic schemas for activity tracking endpoint
Validates and constrains incoming tracking payloads
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator
import json


# White-listed event types — reject anything not in this set
ALLOWED_EVENT_TYPES = {
    "session_start",
    "session_end",
    "session_checkpoint",  # NEW: Sparse cumulative checkpoint (every ~90s)
    "page_view",
    "hotel_view",
    "map_open",
    "reviews_open",
    "scroll_depth",
    "heartbeat",  # Legacy (deprecated, but keeping for backward compat)
}

MAX_METADATA_BYTES = 2048  # 2 KB limit


class TrackEventRequest(BaseModel):
    """
    Inbound tracking event from the frontend.
    Durations are client-reported and stored as-is (marked accordingly).
    """
    session_id: str = Field(..., min_length=36, max_length=36, description="UUID v4 session identifier")
    page: Optional[str] = Field(None, max_length=100, description="Page slug e.g. home, hotel_details")
    hotel_id: Optional[int] = Field(None, ge=1, description="Hotel ID when on a hotel page")
    event_type: str = Field(..., max_length=50, description="One of the allowed event types")
    duration_seconds: Optional[int] = Field(None, ge=0, le=86400, description="Client-reported duration (max 24h)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Free-form JSONB payload (max 2KB)")

    @validator("event_type")
    def validate_event_type(cls, v):
        if v not in ALLOWED_EVENT_TYPES:
            raise ValueError(f"Invalid event_type '{v}'. Allowed: {', '.join(sorted(ALLOWED_EVENT_TYPES))}")
        return v

    @validator("metadata")
    def validate_metadata_size(cls, v):
        if v is not None:
            serialized = json.dumps(v, separators=(",", ":"))
            if len(serialized.encode("utf-8")) > MAX_METADATA_BYTES:
                raise ValueError(f"metadata must not exceed {MAX_METADATA_BYTES} bytes")
        return v

    @validator("session_id")
    def validate_uuid_format(cls, v):
        """Loose UUID v4 format check (8-4-4-4-12 hex groups)"""
        import re
        if not re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', v, re.IGNORECASE):
            raise ValueError("session_id must be a valid UUID v4 string")
        return v


class TrackEventResponse(BaseModel):
    """
    Response after enqueuing a tracking event.

    The `id` field is a placeholder (always 0) because the real database
    auto-incremented ID isn't assigned until the background worker
    bulk-inserts the batch.  Existing frontend code (tracker.js) uses
    fire-and-forget semantics and ignores this value.
    """
    status: str = "ok"
    id: int = 0
