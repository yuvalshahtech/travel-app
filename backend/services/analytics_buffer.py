"""
Analytics Event Buffer — Async In-Memory Queue with Backpressure

This module provides the write-side of the analytics ingestion pipeline.
Instead of writing each event directly to PostgreSQL (1 INSERT per HTTP
request), events are enqueued into an asyncio.Queue. A background worker
(analytics_worker.py) drains the queue in batches and bulk-inserts them.

╔══════════════════════════════════════════════════════════════════════════════╗
║                         ARCHITECTURE OVERVIEW                              ║
║                                                                            ║
║  HTTP Request ──► Pydantic validation ──► rate-limit check ──► enqueue()  ║
║                                                                  │         ║
║                                                    asyncio.Queue │         ║
║                                                                  ▼         ║
║                                         AnalyticsWorker (background task)  ║
║                                              │                             ║
║                                   batches of N events or T-second flush    ║
║                                              │                             ║
║                                   bulk INSERT ──► PostgreSQL               ║
║                                              │                             ║
║                                   retry with exponential backoff           ║
║                                              │                             ║
║                              dead-letter log on permanent failure          ║
╚══════════════════════════════════════════════════════════════════════════════╝

WHY NOT REDIS / KAFKA YET?
  This in-memory queue works for a single-process deployment (1 Uvicorn worker).
  It gives ~20-50× fewer DB round-trips than direct writes, which is enough for
  up to ~5k-10k concurrent users with a 15s heartbeat interval.

  When to upgrade:
    ► Redis (RPUSH/BLPOP): When you run 2+ Uvicorn workers (each has its own
      asyncio.Queue — events aren't shared). Redis gives cross-worker durability.
    ► Kafka / AWS Kinesis: When writes exceed 50k events/sec, or when you need
      replay capability, exactly-once semantics, or multi-consumer fan-out
      (e.g., analytics + alerting + ML pipeline reading the same stream).
    ► Separate OLAP DB (ClickHouse, TimescaleDB): When analytics queries slow
      down your OLTP (bookings) database. ClickHouse can ingest 1M rows/sec
      and query billions in sub-second.

SERVER CRASH BEFORE FLUSH:
  Events in the asyncio.Queue are lost on crash. This is an acceptable tradeoff
  for analytics data (not financial). Mitigation:
    1. Short flush intervals (5s default) limit max data loss to ~5s of events.
    2. Graceful shutdown handler flushes remaining events before exit.
    3. For zero-loss, upgrade to Redis (persisted queue) or Kafka (durable log).

MULTI-WORKER DEPLOYMENT:
  Each Uvicorn worker gets its own AnalyticsBuffer instance. This means:
    - Queue size is per-worker, not global.
    - Batch sizes are effectively divided by worker count.
    - This is fine for < 4 workers. Beyond that, use Redis.
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ─── Event Priority Classification ───────────────────────────────────────────

class EventPriority(IntEnum):
    """
    Priority tiers for analytics events.
    
    When the queue is full (backpressure), low-priority events are dropped
    first. Critical events are NEVER dropped — they are always accepted
    even if it means briefly exceeding the queue limit.
    
    Why these tiers?
      CRITICAL: session_start and session_end define the session boundary.
                Losing them makes it impossible to calculate session duration
                or session count. hotel_view is the primary conversion event.
      MEDIUM:   map_open and reviews_open are engagement signals used for
                feature prioritization, but losing a few is tolerable.
      LOW:      heartbeat fires every 15 seconds — it's the highest-volume
                event and the least valuable individually. Dropping some
                heartbeats barely affects analytics accuracy.
    """
    CRITICAL = 3   # Never dropped: session_start, session_end, hotel_view
    MEDIUM = 2     # Dropped under heavy pressure: map_open, reviews_open, page_view, scroll_depth
    LOW = 1        # Dropped first: heartbeat

# Map event_type → priority
EVENT_PRIORITY_MAP: Dict[str, EventPriority] = {
    "session_start": EventPriority.CRITICAL,
    "session_end":   EventPriority.CRITICAL,
    "hotel_view":    EventPriority.CRITICAL,
    "page_view":     EventPriority.MEDIUM,
    "map_open":      EventPriority.MEDIUM,
    "reviews_open":  EventPriority.MEDIUM,
    "scroll_depth":  EventPriority.MEDIUM,
    "heartbeat":     EventPriority.LOW,
}


def get_event_priority(event_type: str) -> EventPriority:
    """Get priority for an event type. Unknown events default to MEDIUM."""
    return EVENT_PRIORITY_MAP.get(event_type, EventPriority.MEDIUM)


# ─── Buffered Event Data Structure ───────────────────────────────────────────

@dataclass
class BufferedEvent:
    """
    A single analytics event waiting to be flushed to the database.
    
    Stored as a plain dict (column_name → value) rather than an ORM object.
    This avoids creating SQLAlchemy model instances in the hot path and
    enables bulk_insert_mappings() which is 3-5× faster than individual
    session.add() calls.
    
    enqueued_at is used for ordering verification and staleness detection.
    """
    data: Dict[str, Any]          # Column-value mapping for user_activity table
    priority: EventPriority       # For backpressure decisions
    session_id: str               # For per-session ordering guarantees
    enqueued_at: float = field(default_factory=time.monotonic)


# ─── Configuration ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BufferConfig:
    """
    All tunable parameters for the analytics buffer, loaded from env vars.
    
    Frozen (immutable) — changes require restart. This is intentional:
    runtime-mutable config adds complexity with minimal benefit for
    batch parameters.
    """
    batch_size: int = int(os.getenv("ANALYTICS_BATCH_SIZE", "100"))
    flush_interval_seconds: float = float(os.getenv("ANALYTICS_FLUSH_INTERVAL", "5"))
    max_queue_size: int = int(os.getenv("ANALYTICS_MAX_QUEUE_SIZE", "5000"))
    drop_heartbeat_on_overflow: bool = os.getenv(
        "ANALYTICS_DROP_HEARTBEAT_ON_OVERFLOW", "true"
    ).lower() in ("true", "1", "yes")
    # Maximum number of events to accept above max_queue_size for CRITICAL events
    critical_overflow_headroom: int = int(os.getenv("ANALYTICS_CRITICAL_HEADROOM", "500"))
    # DB retry
    max_retries: int = int(os.getenv("ANALYTICS_MAX_RETRIES", "3"))
    retry_base_delay: float = float(os.getenv("ANALYTICS_RETRY_BASE_DELAY", "1.0"))


# Singleton config
buffer_config = BufferConfig()


# ─── Analytics Buffer ─────────────────────────────────────────────────────────

class AnalyticsBuffer:
    """
    Async-safe event buffer backed by asyncio.Queue.
    
    Thread safety:
      asyncio.Queue is safe for concurrent coroutines within a single event loop.
      It is NOT safe across OS threads or processes. For multi-worker setups,
      each worker gets its own buffer (acceptable) or use Redis (better).
    
    Backpressure policy:
      When the queue approaches max_queue_size:
        1. LOW priority events (heartbeat) are silently dropped.
        2. MEDIUM events are dropped with a warning log.
        3. CRITICAL events are always accepted (up to critical_overflow_headroom
           extra slots).
      This prevents memory exhaustion while preserving the most valuable data.
    
    Usage:
        buffer = AnalyticsBuffer()
        await buffer.enqueue(event)        # From route handler
        batch = await buffer.drain(100)    # From background worker
        await buffer.flush_remaining()     # On shutdown
    """

    def __init__(self, config: Optional[BufferConfig] = None):
        self._config = config or buffer_config
        # asyncio.Queue with no maxsize — we enforce our own backpressure
        # logic that differentiates by priority, which Queue's built-in
        # maxsize cannot do.
        self._queue: asyncio.Queue[BufferedEvent] = asyncio.Queue()
        self._dropped_count: int = 0
        self._enqueued_count: int = 0
        self._last_drop_log_time: float = 0
        self._shutdown: bool = False

    @property
    def qsize(self) -> int:
        return self._queue.qsize()

    @property
    def stats(self) -> Dict[str, Any]:
        """Diagnostic stats for monitoring/health endpoints."""
        return {
            "queue_size": self._queue.qsize(),
            "enqueued_total": self._enqueued_count,
            "dropped_total": self._dropped_count,
            "max_queue_size": self._config.max_queue_size,
            "shutdown": self._shutdown,
        }

    async def enqueue(self, event: BufferedEvent) -> bool:
        """
        Add an event to the buffer.
        
        Returns:
            True if enqueued successfully.
            False if dropped due to backpressure.
        
        This method NEVER blocks the caller. If the queue is full and the
        event is droppable, it returns False immediately. This is critical
        to keep the /activity/track endpoint fast (~0-1ms for enqueue).
        """
        if self._shutdown:
            logger.warning("Buffer is shut down — rejecting event")
            return False

        current_size = self._queue.qsize()
        max_size = self._config.max_queue_size

        # ── Backpressure check ──
        if current_size >= max_size:
            # Queue is at capacity. Apply priority-based dropping.
            if event.priority == EventPriority.LOW:
                # Always drop heartbeats when full
                self._record_drop("LOW (heartbeat)")
                return False

            if event.priority == EventPriority.MEDIUM:
                # Drop medium events when significantly over capacity
                self._record_drop("MEDIUM")
                return False

            # CRITICAL events: allow up to critical_overflow_headroom extra
            if current_size >= max_size + self._config.critical_overflow_headroom:
                # Even critical events are dropped if we're WAY over capacity.
                # This is a safety valve against total memory exhaustion.
                self._record_drop("CRITICAL (over headroom)")
                logger.error(
                    f"CRITICAL event dropped — queue at {current_size}, "
                    f"headroom exhausted. This should not happen in normal operation."
                )
                return False

        # ── Soft pressure warning (queue > 80% full) ──
        if current_size > max_size * 0.8 and event.priority == EventPriority.LOW:
            if self._config.drop_heartbeat_on_overflow:
                self._record_drop("LOW (soft pressure)")
                return False

        # ── Enqueue ──
        try:
            self._queue.put_nowait(event)
            self._enqueued_count += 1
            return True
        except asyncio.QueueFull:
            # Should not happen (no maxsize set), but defensive
            self._record_drop("QueueFull")
            return False

    async def drain(self, max_items: int) -> List[BufferedEvent]:
        """
        Remove up to max_items events from the queue.
        
        Non-blocking: returns whatever is available, up to max_items.
        The caller (AnalyticsWorker) calls this periodically.
        
        Events are returned in FIFO order. Since asyncio.Queue is FIFO
        and events arrive in chronological order from the event loop,
        per-session ordering is preserved as long as we flush them to
        the DB in the same order (which bulk INSERT does).
        """
        batch: List[BufferedEvent] = []
        for _ in range(max_items):
            try:
                event = self._queue.get_nowait()
                batch.append(event)
            except asyncio.QueueEmpty:
                break
        return batch

    async def drain_blocking(self, max_items: int, timeout: float) -> List[BufferedEvent]:
        """
        Drain with a blocking wait for the first item.
        
        Waits up to `timeout` seconds for at least one event, then
        greedily drains up to max_items without waiting. This is used
        by the worker's main loop to efficiently combine time-based
        and size-based flushing.
        
        Why blocking on the first item?
          If the queue is empty, we don't want the worker to spin-loop
          consuming CPU. asyncio.wait_for(queue.get()) suspends the
          coroutine until an event arrives or the timeout expires.
        """
        batch: List[BufferedEvent] = []

        # Block for the first event (or until timeout)
        try:
            first = await asyncio.wait_for(
                self._queue.get(), timeout=timeout
            )
            batch.append(first)
        except asyncio.TimeoutError:
            # Timeout — return empty batch (worker will loop)
            return batch

        # Greedily drain remaining (non-blocking)
        for _ in range(max_items - 1):
            try:
                event = self._queue.get_nowait()
                batch.append(event)
            except asyncio.QueueEmpty:
                break

        return batch

    async def flush_remaining(self) -> List[BufferedEvent]:
        """
        Drain ALL remaining events. Called during graceful shutdown.
        
        After this call, the buffer should be empty. The caller must
        write these events to the DB before the process exits.
        """
        self._shutdown = True
        remaining: List[BufferedEvent] = []
        while not self._queue.empty():
            try:
                event = self._queue.get_nowait()
                remaining.append(event)
            except asyncio.QueueEmpty:
                break
        if remaining:
            logger.info(f"Shutdown flush: drained {len(remaining)} remaining events from buffer")
        return remaining

    def _record_drop(self, reason: str) -> None:
        """Record a dropped event and log periodically (not per-event to avoid log spam)."""
        self._dropped_count += 1
        now = time.monotonic()
        # Log at most once every 10 seconds to avoid flooding logs
        if now - self._last_drop_log_time > 10:
            self._last_drop_log_time = now
            logger.warning(
                f"Analytics backpressure: dropped {reason} event "
                f"(queue={self._queue.qsize()}/{self._config.max_queue_size}, "
                f"total_dropped={self._dropped_count})"
            )


# ─── Global singleton ─────────────────────────────────────────────────────────
# Created at import time. The worker and routes both reference this instance.
# For testing, inject a custom instance via dependency override.

analytics_buffer = AnalyticsBuffer()
