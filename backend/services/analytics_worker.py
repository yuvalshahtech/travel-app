"""
Analytics Worker — Background Bulk-Insert Consumer

This module provides the read-side of the analytics ingestion pipeline.
It runs as a background asyncio task within the FastAPI process and
periodically drains events from the AnalyticsBuffer, writing them to
PostgreSQL in bulk.

╔══════════════════════════════════════════════════════════════════════════════╗
║                        PERFORMANCE CHARACTERISTICS                         ║
║                                                                            ║
║  Direct-write (old):                                                       ║
║    1 event → 1 INSERT → 1 DB round-trip                                    ║
║    With 10k users × 15s heartbeat = ~667 INSERTs/sec                       ║
║    Each INSERT: ~2ms network + ~1ms DB = ~3ms                              ║
║    Total DB time: 667 × 3ms = 2 seconds of DB time per second (saturated)  ║
║                                                                            ║
║  Batched-write (new):                                                      ║
║    100 events → 1 bulk INSERT → 1 DB round-trip                            ║
║    667 events/sec ÷ 100/batch = ~7 bulk INSERTs/sec                        ║
║    Each bulk INSERT: ~2ms network + ~5ms DB = ~7ms                         ║
║    Total DB time: 7 × 7ms = 49ms per second (97% reduction)               ║
║                                                                            ║
║  Expected improvement: ~20-50× fewer DB round-trips                        ║
╚══════════════════════════════════════════════════════════════════════════════╝

BULK INSERT STRATEGY:
  We use SQLAlchemy's session.execute(insert(), list_of_dicts) which generates
  a single multi-row INSERT statement:
    INSERT INTO user_activity (col1, col2, ...) VALUES
      (v1, v2, ...),
      (v1, v2, ...),
      ... (100 rows)
  This is the fastest way to insert multiple rows with SQLAlchemy ORM.
  For even higher throughput, COPY (psycopg2.copy_from) can be used,
  but it bypasses ORM hooks and requires CSV formatting.

RETRY STRATEGY:
  On DB failure (connection lost, deadlock, etc.), the worker retries
  with exponential backoff: 1s, 2s, 4s (configurable). After max_retries
  failures, events are written to a dead-letter log file (JSON Lines)
  so they can be re-ingested later. Events are NEVER silently lost.

ORDERING GUARANTEE:
  Events within a single batch are inserted in the order they were enqueued.
  asyncio.Queue is FIFO, so events from the same session arrive in order.
  Multi-row INSERT preserves row order within the VALUES list.
  Therefore, per-session event ordering is maintained.

  CAVEAT: If events cross batch boundaries (event A in batch 1, event B in
  batch 2), and batch 1 fails while batch 2 succeeds, event B may appear
  before event A after retry. This is acceptable for analytics (not financial
  transactions). For strict ordering, use Kafka with per-session partitioning.

HEARTBEAT AGGREGATION:
  Instead of storing every raw heartbeat (wasteful), the worker can optionally
  aggregate consecutive heartbeats from the same session into a single record
  with a count and time range. This is controlled by ANALYTICS_AGGREGATE_HEARTBEATS.
  
  Why?
    With 10k users and 15s intervals, heartbeats = 667 rows/sec = 57M rows/day.
    Aggregated: 10k sessions × ~1 summary row/flush = ~2k rows/flush = ~400/sec = 34M fewer rows/day.
  
  Current implementation stores raw heartbeats (aggregation is documented
  as a future enhancement). The schema and queries don't need changes —
  aggregated heartbeats would use event_metadata = {"count": N, "from": ts, "to": ts}.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy import insert
from sqlalchemy.orm import Session

from config.database import SessionLocal
from models.models import UserActivity
from services.analytics_buffer import (
    AnalyticsBuffer,
    BufferConfig,
    BufferedEvent,
    analytics_buffer,
    buffer_config,
)

logger = logging.getLogger(__name__)

# Dead-letter log path (JSON Lines format, one failed batch per line)
DEAD_LETTER_DIR = Path(__file__).parent.parent / "logs"
DEAD_LETTER_FILE = DEAD_LETTER_DIR / "analytics_dead_letter.jsonl"


class AnalyticsWorker:
    """
    Background worker that drains the AnalyticsBuffer and writes to PostgreSQL.
    
    Lifecycle:
      1. start()  — called by FastAPI lifespan on_startup
      2. Worker runs in a background asyncio.Task
      3. stop()   — called by FastAPI lifespan on_shutdown
      4. stop() flushes remaining events and waits for the task to complete
    
    The worker loop:
      1. Wait for events (blocking up to flush_interval seconds)
      2. Drain up to batch_size events
      3. Bulk INSERT them in a single transaction
      4. On failure, retry with exponential backoff
      5. On permanent failure, write to dead-letter log
      6. Repeat
    """

    def __init__(
        self,
        buffer: Optional[AnalyticsBuffer] = None,
        config: Optional[BufferConfig] = None,
    ):
        self._buffer = buffer or analytics_buffer
        self._config = config or buffer_config
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._flush_count = 0
        self._total_inserted = 0
        self._total_failed = 0
        self._total_dead_lettered = 0

    @property
    def stats(self) -> Dict:
        """Diagnostic stats for health endpoints."""
        return {
            "running": self._running,
            "flush_count": self._flush_count,
            "total_inserted": self._total_inserted,
            "total_failed_retries": self._total_failed,
            "total_dead_lettered": self._total_dead_lettered,
            **self._buffer.stats,
        }

    def start(self) -> None:
        """
        Start the background worker task.
        
        Must be called from a running asyncio event loop (e.g., FastAPI startup).
        Idempotent — calling start() twice is safe.
        """
        if self._task and not self._task.done():
            logger.warning("AnalyticsWorker.start() called but worker is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop(), name="analytics-worker")
        logger.info(
            f"Analytics worker started "
            f"(batch_size={self._config.batch_size}, "
            f"flush_interval={self._config.flush_interval_seconds}s, "
            f"max_queue={self._config.max_queue_size})"
        )

    async def stop(self) -> None:
        """
        Gracefully shut down the worker.
        
        1. Signal the loop to stop
        2. Flush all remaining events in the buffer
        3. Wait for the task to complete (with timeout)
        
        Race condition handling:
          Between setting _running=False and the flush, new events
          may arrive. The buffer's flush_remaining() sets buffer._shutdown=True
          which rejects further enqueues. Any event rejected during this
          tiny window is logged and lost — acceptable for analytics.
        """
        if not self._running:
            return

        logger.info("Analytics worker shutting down — flushing remaining events...")
        self._running = False

        # Flush everything remaining in the buffer
        remaining = await self._buffer.flush_remaining()
        if remaining:
            await self._bulk_insert(remaining)

        # Wait for the background task to finish
        if self._task and not self._task.done():
            try:
                await asyncio.wait_for(self._task, timeout=10.0)
            except asyncio.TimeoutError:
                logger.error("Analytics worker task did not finish in 10s — cancelling")
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass

        logger.info(
            f"Analytics worker stopped. "
            f"Total inserted: {self._total_inserted}, "
            f"Dead-lettered: {self._total_dead_lettered}"
        )

    async def _run_loop(self) -> None:
        """
        Main worker loop.
        
        Uses drain_blocking() which waits up to flush_interval for the first
        event, then greedily drains the rest. This means:
          - Empty queue: worker sleeps (no CPU usage)
          - Slow traffic: flushes every flush_interval seconds
          - Burst traffic: flushes as soon as batch_size events accumulate
        """
        logger.info("Analytics worker loop started")
        while self._running:
            try:
                batch = await self._buffer.drain_blocking(
                    max_items=self._config.batch_size,
                    timeout=self._config.flush_interval_seconds,
                )

                if batch:
                    await self._bulk_insert(batch)
                    self._flush_count += 1

            except asyncio.CancelledError:
                logger.info("Analytics worker loop cancelled")
                break
            except Exception:
                logger.exception("Unexpected error in analytics worker loop")
                # Don't crash the loop — wait briefly and retry
                await asyncio.sleep(1.0)

        logger.info("Analytics worker loop exited")

    async def _bulk_insert(self, batch: List[BufferedEvent]) -> None:
        """
        Write a batch of events to PostgreSQL using a single multi-row INSERT.
        
        Uses run_in_executor to avoid blocking the event loop during DB I/O.
        SQLAlchemy's session operations are synchronous, so we run them in
        the default thread pool executor.
        
        On failure: retries with exponential backoff, then dead-letters.
        """
        if not batch:
            return

        # Convert BufferedEvent objects to column-value dicts for bulk insert
        rows = [event.data for event in batch]

        loop = asyncio.get_running_loop()
        success = await loop.run_in_executor(
            None,  # default thread pool
            self._sync_bulk_insert_with_retry,
            rows,
        )

        if success:
            self._total_inserted += len(rows)
        else:
            # Permanent failure — dead-letter the batch
            self._total_dead_lettered += len(rows)
            await self._dead_letter(batch)

    def _sync_bulk_insert_with_retry(self, rows: List[Dict]) -> bool:
        """
        Synchronous bulk insert with exponential backoff retry.
        
        Runs in a thread pool executor (not the asyncio event loop thread).
        
        Why not async DB operations?
          SQLAlchemy 2.0 supports async (via asyncpg), but this project
          uses synchronous psycopg2. Running sync DB ops in the executor
          is the standard pattern and works well for batch writes.
        """
        last_error = None
        for attempt in range(self._config.max_retries + 1):
            db: Optional[Session] = None
            try:
                db = SessionLocal()
                # Use insert().values() for a single multi-row INSERT statement.
                # This is significantly faster than db.add() in a loop because:
                #   1. One SQL statement instead of N
                #   2. One network round-trip instead of N
                #   3. One transaction commit instead of N
                stmt = insert(UserActivity).values(rows)
                db.execute(stmt)
                db.commit()
                logger.debug(f"Bulk inserted {len(rows)} analytics events")
                return True

            except Exception as e:
                last_error = e
                self._total_failed += 1
                if db:
                    try:
                        db.rollback()
                    except Exception:
                        pass

                if attempt < self._config.max_retries:
                    # Exponential backoff: 1s, 2s, 4s (default)
                    delay = self._config.retry_base_delay * (2 ** attempt)
                    logger.warning(
                        f"Bulk insert failed (attempt {attempt + 1}/{self._config.max_retries + 1}), "
                        f"retrying in {delay:.1f}s: {e}"
                    )
                    time.sleep(delay)  # Blocking sleep OK — we're in the executor thread
                else:
                    logger.error(
                        f"Bulk insert permanently failed after {self._config.max_retries + 1} attempts: {e}",
                        exc_info=True,
                    )
            finally:
                if db:
                    try:
                        db.close()
                    except Exception:
                        pass

        return False

    async def _dead_letter(self, batch: List[BufferedEvent]) -> None:
        """
        Write failed events to a dead-letter file (JSON Lines format).
        
        Dead-letter events can be re-ingested later with a recovery script:
          cat analytics_dead_letter.jsonl | python recover_analytics.py
        
        Format per line:
          {"ts": "2026-03-01T...", "count": 50, "events": [{...}, ...]}
        
        Why a file and not a database table?
          If the DB is down (which is why we're dead-lettering), we can't
          write to another table in the same DB. A local file is the most
          reliable fallback. For production, dead-letter to S3 or a dead-letter
          Redis list.
        """
        try:
            # Ensure log directory exists
            DEAD_LETTER_DIR.mkdir(parents=True, exist_ok=True)

            payload = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "count": len(batch),
                "events": [event.data for event in batch],
            }

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                self._sync_write_dead_letter,
                payload,
            )

            logger.error(
                f"Dead-lettered {len(batch)} events to {DEAD_LETTER_FILE}"
            )
        except Exception:
            logger.exception(
                f"CRITICAL: Failed to dead-letter {len(batch)} events. "
                f"These events are LOST. This should never happen."
            )

    @staticmethod
    def _sync_write_dead_letter(payload: Dict) -> None:
        """Append a JSON line to the dead-letter file. Runs in executor."""
        with open(DEAD_LETTER_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, default=str) + "\n")


# ─── Global singleton ─────────────────────────────────────────────────────────

analytics_worker = AnalyticsWorker()
