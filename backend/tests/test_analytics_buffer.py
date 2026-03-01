"""
Tests for Analytics Buffer and Worker

Run with:
    cd travel-app
    python -m pytest backend/tests/test_analytics_buffer.py -v

These tests verify the batched-ingestion pipeline:
  1. Enqueue / drain FIFO ordering
  2. Priority-based backpressure (heartbeat dropped first)
  3. CRITICAL overflow headroom
  4. Soft-pressure heartbeat dropping (>80%)
  5. Shutdown flush
  6. Worker bulk insert (mocked DB)
  7. Worker retry on failure
  8. Dead-lettering on permanent failure
  9. Worker start / stop lifecycle
  10. Drain-blocking timeout behaviour
"""

import asyncio
import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

# ─── Ensure env vars are set before any app imports ──────────────────────────
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars!")
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("ANALYTICS_BATCH_SIZE", "5")
os.environ.setdefault("ANALYTICS_FLUSH_INTERVAL", "0.5")
os.environ.setdefault("ANALYTICS_MAX_QUEUE_SIZE", "20")
os.environ.setdefault("ANALYTICS_CRITICAL_HEADROOM", "5")
os.environ.setdefault("ANALYTICS_MAX_RETRIES", "2")
os.environ.setdefault("ANALYTICS_RETRY_BASE_DELAY", "0.01")

from backend.services.analytics_buffer import (
    AnalyticsBuffer,
    BufferConfig,
    BufferedEvent,
    EventPriority,
    get_event_priority,
)
from backend.services.analytics_worker import AnalyticsWorker


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def make_event(
    event_type: str = "page_view",
    session_id: str = "aaaa-bbbb-cccc-dddd",
    user_id: int = 1,
    page: str = "home",
    hotel_id: int = None,
) -> BufferedEvent:
    """Create a BufferedEvent with sensible defaults."""
    return BufferedEvent(
        data={
            "user_id": user_id,
            "action_type": event_type,
            "session_id": session_id,
            "page": page,
            "hotel_id": hotel_id,
            "event_type": event_type,
            "duration_seconds": None,
            "event_metadata": None,
        },
        priority=get_event_priority(event_type),
        session_id=session_id,
    )


def small_config(**overrides) -> BufferConfig:
    """Return a BufferConfig with small sizes for fast tests."""
    defaults = dict(
        batch_size=5,
        flush_interval_seconds=0.2,
        max_queue_size=20,
        drop_heartbeat_on_overflow=True,
        critical_overflow_headroom=5,
        max_retries=2,
        retry_base_delay=0.01,
    )
    defaults.update(overrides)
    return BufferConfig(**defaults)


# ═══════════════════════════════════════════════════════════════════════════════
# Unit Tests — EventPriority Mapping
# ═══════════════════════════════════════════════════════════════════════════════

class TestEventPriority:
    """Verify event types map to correct priority tiers."""

    def test_critical_events(self):
        assert get_event_priority("session_start") == EventPriority.CRITICAL
        assert get_event_priority("session_end") == EventPriority.CRITICAL
        assert get_event_priority("hotel_view") == EventPriority.CRITICAL

    def test_medium_events(self):
        assert get_event_priority("page_view") == EventPriority.MEDIUM
        assert get_event_priority("map_open") == EventPriority.MEDIUM
        assert get_event_priority("reviews_open") == EventPriority.MEDIUM
        assert get_event_priority("scroll_depth") == EventPriority.MEDIUM

    def test_low_events(self):
        assert get_event_priority("heartbeat") == EventPriority.LOW

    def test_unknown_defaults_to_medium(self):
        assert get_event_priority("some_unknown_event") == EventPriority.MEDIUM


# ═══════════════════════════════════════════════════════════════════════════════
# Unit Tests — AnalyticsBuffer
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsBuffer:
    """Tests for the in-memory event buffer."""

    @pytest.fixture
    def buf(self):
        """Fresh buffer with small queue for fast testing."""
        return AnalyticsBuffer(config=small_config())

    @pytest.mark.asyncio
    async def test_enqueue_and_drain(self, buf):
        """Events are enqueued and drained in FIFO order."""
        e1 = make_event("page_view", session_id="s1")
        e2 = make_event("hotel_view", session_id="s2")
        e3 = make_event("heartbeat", session_id="s3")

        assert await buf.enqueue(e1) is True
        assert await buf.enqueue(e2) is True
        assert await buf.enqueue(e3) is True
        assert buf.qsize == 3

        batch = await buf.drain(10)
        assert len(batch) == 3
        assert batch[0].data["event_type"] == "page_view"
        assert batch[1].data["event_type"] == "hotel_view"
        assert batch[2].data["event_type"] == "heartbeat"
        assert buf.qsize == 0

    @pytest.mark.asyncio
    async def test_drain_respects_max_items(self, buf):
        """Drain returns at most max_items events."""
        for i in range(10):
            await buf.enqueue(make_event("page_view", session_id=f"s{i}"))
        batch = await buf.drain(3)
        assert len(batch) == 3
        assert buf.qsize == 7

    @pytest.mark.asyncio
    async def test_stats_tracking(self, buf):
        """Stats reflect enqueue/drop counts."""
        for i in range(5):
            await buf.enqueue(make_event("page_view", session_id=f"s{i}"))

        stats = buf.stats
        assert stats["enqueued_total"] == 5
        assert stats["dropped_total"] == 0
        assert stats["queue_size"] == 5

    @pytest.mark.asyncio
    async def test_shutdown_rejects_events(self, buf):
        """After shutdown, new events are rejected."""
        await buf.flush_remaining()
        result = await buf.enqueue(make_event("page_view"))
        assert result is False

    # ── Backpressure Tests ────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_drop_heartbeat_when_full(self):
        """LOW (heartbeat) events are dropped when queue is at capacity."""
        cfg = small_config(max_queue_size=5)
        buf = AnalyticsBuffer(config=cfg)

        # Fill to capacity with MEDIUM events
        for i in range(5):
            await buf.enqueue(make_event("page_view", session_id=f"s{i}"))
        assert buf.qsize == 5

        # Heartbeat should be dropped
        result = await buf.enqueue(make_event("heartbeat", session_id="h1"))
        assert result is False
        assert buf.stats["dropped_total"] == 1

    @pytest.mark.asyncio
    async def test_drop_medium_when_full(self):
        """MEDIUM events are dropped when queue is at capacity."""
        cfg = small_config(max_queue_size=5)
        buf = AnalyticsBuffer(config=cfg)

        # Fill to capacity
        for i in range(5):
            await buf.enqueue(make_event("session_start", session_id=f"s{i}"))

        # Medium event should be dropped
        result = await buf.enqueue(make_event("page_view", session_id="m1"))
        assert result is False

    @pytest.mark.asyncio
    async def test_critical_accepted_when_full(self):
        """CRITICAL events are still accepted when queue is at capacity (up to headroom)."""
        cfg = small_config(max_queue_size=5, critical_overflow_headroom=3)
        buf = AnalyticsBuffer(config=cfg)

        # Fill to capacity
        for i in range(5):
            await buf.enqueue(make_event("page_view", session_id=f"s{i}"))

        # Critical events should still be accepted
        result = await buf.enqueue(make_event("session_start", session_id="c1"))
        assert result is True
        assert buf.qsize == 6  # Over capacity, using headroom

    @pytest.mark.asyncio
    async def test_critical_dropped_when_headroom_exhausted(self):
        """CRITICAL events are dropped when both capacity AND headroom are exhausted."""
        cfg = small_config(max_queue_size=5, critical_overflow_headroom=2)
        buf = AnalyticsBuffer(config=cfg)

        # Fill to capacity + headroom = 7
        for i in range(5):
            await buf.enqueue(make_event("session_start", session_id=f"s{i}"))
        for i in range(2):
            await buf.enqueue(make_event("session_start", session_id=f"h{i}"))
        assert buf.qsize == 7

        # Next critical event should be dropped
        result = await buf.enqueue(make_event("session_start", session_id="overflow"))
        assert result is False

    @pytest.mark.asyncio
    async def test_soft_pressure_drops_heartbeat(self):
        """Heartbeats are dropped when queue is >80% full (soft pressure)."""
        cfg = small_config(max_queue_size=10, drop_heartbeat_on_overflow=True)
        buf = AnalyticsBuffer(config=cfg)

        # Fill to 9/10 = 90% (above 80% threshold)
        for i in range(9):
            await buf.enqueue(make_event("page_view", session_id=f"s{i}"))

        # Heartbeat should be dropped at soft pressure
        result = await buf.enqueue(make_event("heartbeat", session_id="hb1"))
        assert result is False

    @pytest.mark.asyncio
    async def test_soft_pressure_allows_medium(self):
        """MEDIUM events pass through even at >80% (only heartbeats are soft-dropped)."""
        cfg = small_config(max_queue_size=10, drop_heartbeat_on_overflow=True)
        buf = AnalyticsBuffer(config=cfg)

        # Fill to 9/10 = 90%
        for i in range(9):
            await buf.enqueue(make_event("session_start", session_id=f"s{i}"))

        # Medium event should still be accepted
        result = await buf.enqueue(make_event("page_view", session_id="m1"))
        assert result is True

    # ── Drain Blocking ────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_drain_blocking_timeout(self, buf):
        """drain_blocking returns empty list after timeout when queue is empty."""
        start = time.monotonic()
        batch = await buf.drain_blocking(max_items=5, timeout=0.1)
        elapsed = time.monotonic() - start
        assert len(batch) == 0
        assert elapsed >= 0.08  # Allow small jitter

    @pytest.mark.asyncio
    async def test_drain_blocking_immediate(self, buf):
        """drain_blocking returns immediately when events are available."""
        await buf.enqueue(make_event("page_view"))
        await buf.enqueue(make_event("hotel_view"))

        batch = await buf.drain_blocking(max_items=5, timeout=1.0)
        assert len(batch) == 2

    # ── Flush Remaining ───────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_flush_remaining_drains_all(self, buf):
        """flush_remaining drains all events and sets shutdown flag."""
        for i in range(8):
            await buf.enqueue(make_event("page_view", session_id=f"s{i}"))

        remaining = await buf.flush_remaining()
        assert len(remaining) == 8
        assert buf.qsize == 0
        assert buf.stats["shutdown"] is True


# ═══════════════════════════════════════════════════════════════════════════════
# Unit Tests — AnalyticsWorker
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsWorker:
    """Tests for the background bulk-insert worker."""

    @pytest.fixture
    def worker_with_buffer(self):
        """Create a worker with a fresh buffer and small config."""
        cfg = small_config()
        buf = AnalyticsBuffer(config=cfg)
        worker = AnalyticsWorker(buffer=buf, config=cfg)
        return worker, buf

    @pytest.mark.asyncio
    async def test_bulk_insert_success(self, worker_with_buffer):
        """Bulk insert writes events to the database (mocked)."""
        worker, buf = worker_with_buffer

        for i in range(3):
            await buf.enqueue(make_event("page_view", session_id=f"s{i}"))
        batch = await buf.drain(10)

        with patch.object(worker, "_sync_bulk_insert_with_retry", return_value=True) as mock_insert:
            await worker._bulk_insert(batch)
            mock_insert.assert_called_once()
            args = mock_insert.call_args[0]
            assert len(args[0]) == 3  # 3 row dicts
            assert worker._total_inserted == 3

    @pytest.mark.asyncio
    async def test_bulk_insert_failure_dead_letters(self, worker_with_buffer):
        """Permanent failure triggers dead-lettering."""
        worker, buf = worker_with_buffer

        for i in range(3):
            await buf.enqueue(make_event("page_view", session_id=f"s{i}"))
        batch = await buf.drain(10)

        with patch.object(worker, "_sync_bulk_insert_with_retry", return_value=False):
            with patch.object(worker, "_dead_letter") as mock_dl:
                await worker._bulk_insert(batch)
                mock_dl.assert_called_once_with(batch)
                assert worker._total_dead_lettered == 3

    @pytest.mark.asyncio
    async def test_sync_retry_succeeds_on_second_attempt(self, worker_with_buffer):
        """Retry logic succeeds after an initial failure."""
        worker, _ = worker_with_buffer

        mock_session = MagicMock()
        call_count = 0

        def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Connection refused")

        mock_session.execute = mock_execute
        mock_session.commit = MagicMock()
        mock_session.rollback = MagicMock()
        mock_session.close = MagicMock()

        rows = [{"user_id": 1, "event_type": "page_view", "session_id": "s1"}]

        with patch("backend.services.analytics_worker.SessionLocal", return_value=mock_session):
            result = worker._sync_bulk_insert_with_retry(rows)
            assert result is True
            assert call_count == 2  # First failed, second succeeded

    @pytest.mark.asyncio
    async def test_sync_retry_exhausts_retries(self, worker_with_buffer):
        """After max_retries, returns False for dead-lettering."""
        worker, _ = worker_with_buffer

        mock_session = MagicMock()
        mock_session.execute = MagicMock(side_effect=Exception("DB down"))
        mock_session.rollback = MagicMock()
        mock_session.close = MagicMock()

        rows = [{"user_id": 1, "event_type": "page_view", "session_id": "s1"}]

        with patch("backend.services.analytics_worker.SessionLocal", return_value=mock_session):
            result = worker._sync_bulk_insert_with_retry(rows)
            assert result is False
            # max_retries=2 means 3 total attempts (initial + 2 retries)
            assert mock_session.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_dead_letter_writes_file(self, worker_with_buffer):
        """Dead-letter writes events to a JSON Lines file."""
        worker, buf = worker_with_buffer

        await buf.enqueue(make_event("page_view", session_id="s1"))
        batch = await buf.drain(10)

        with tempfile.TemporaryDirectory() as tmpdir:
            dead_letter_file = Path(tmpdir) / "test_dead_letter.jsonl"
            with patch("backend.services.analytics_worker.DEAD_LETTER_DIR", Path(tmpdir)):
                with patch("backend.services.analytics_worker.DEAD_LETTER_FILE", dead_letter_file):
                    await worker._dead_letter(batch)

            assert dead_letter_file.exists()
            lines = dead_letter_file.read_text().strip().split("\n")
            assert len(lines) == 1
            payload = json.loads(lines[0])
            assert payload["count"] == 1
            assert len(payload["events"]) == 1
            assert payload["events"][0]["event_type"] == "page_view"

    # ── Worker Lifecycle ──────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_worker_start_stop(self, worker_with_buffer):
        """Worker starts background task and shuts down cleanly."""
        worker, buf = worker_with_buffer

        # Enqueue some events
        for i in range(3):
            await buf.enqueue(make_event("page_view", session_id=f"s{i}"))

        # Mock DB to succeed
        mock_session = MagicMock()
        mock_session.execute = MagicMock()
        mock_session.commit = MagicMock()
        mock_session.close = MagicMock()

        with patch("backend.services.analytics_worker.SessionLocal", return_value=mock_session):
            worker.start()
            assert worker._running is True
            assert worker._task is not None

            # Give the worker time to process
            await asyncio.sleep(0.5)

            await worker.stop()
            assert worker._running is False

    @pytest.mark.asyncio
    async def test_worker_idempotent_start(self, worker_with_buffer):
        """Calling start() twice doesn't create duplicate tasks."""
        worker, _ = worker_with_buffer

        mock_session = MagicMock()
        mock_session.execute = MagicMock()
        mock_session.commit = MagicMock()
        mock_session.close = MagicMock()

        with patch("backend.services.analytics_worker.SessionLocal", return_value=mock_session):
            worker.start()
            task1 = worker._task
            worker.start()
            task2 = worker._task
            assert task1 is task2  # Same task, not duplicated

            await worker.stop()

    @pytest.mark.asyncio
    async def test_worker_stats(self, worker_with_buffer):
        """Stats dict includes both worker and buffer metrics."""
        worker, _ = worker_with_buffer
        stats = worker.stats
        assert "running" in stats
        assert "flush_count" in stats
        assert "total_inserted" in stats
        assert "total_dead_lettered" in stats
        assert "queue_size" in stats  # From buffer
        assert "enqueued_total" in stats  # From buffer

    @pytest.mark.asyncio
    async def test_shutdown_flushes_remaining(self, worker_with_buffer):
        """On stop(), remaining buffered events are flushed to DB."""
        worker, buf = worker_with_buffer

        mock_session = MagicMock()
        mock_session.execute = MagicMock()
        mock_session.commit = MagicMock()
        mock_session.close = MagicMock()

        # Don't start the worker loop — we want events to remain in buffer
        # until stop() is called
        for i in range(4):
            await buf.enqueue(make_event("hotel_view", session_id=f"s{i}"))

        assert buf.qsize == 4

        with patch("backend.services.analytics_worker.SessionLocal", return_value=mock_session):
            worker.start()
            # Stop immediately — worker may not have had time to drain
            await worker.stop()

        # Either the worker loop processed them or stop() flushed them
        # Either way, nothing should remain in the buffer
        assert buf.qsize == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Integration-Style Tests — Buffer + Worker Together
# ═══════════════════════════════════════════════════════════════════════════════

class TestBufferWorkerIntegration:
    """Test the buffer → worker pipeline end-to-end (DB mocked)."""

    @pytest.mark.asyncio
    async def test_full_pipeline_enqueue_to_insert(self):
        """Events enqueued via buffer are bulk-inserted by worker."""
        cfg = small_config(batch_size=3, flush_interval_seconds=0.2)
        buf = AnalyticsBuffer(config=cfg)
        worker = AnalyticsWorker(buffer=buf, config=cfg)

        inserted_rows = []

        def capture_insert(rows):
            inserted_rows.extend(rows)
            return True

        with patch.object(worker, "_sync_bulk_insert_with_retry", side_effect=capture_insert):
            worker.start()

            # Enqueue 6 events (should result in 2 batches of 3)
            for i in range(6):
                await buf.enqueue(make_event("page_view", session_id=f"s{i}"))

            # Wait for worker to process both batches
            await asyncio.sleep(1.0)
            await worker.stop()

        assert len(inserted_rows) == 6

    @pytest.mark.asyncio
    async def test_mixed_priority_backpressure(self):
        """Under load, heartbeats are dropped but critical events survive."""
        cfg = small_config(max_queue_size=10, critical_overflow_headroom=3)
        buf = AnalyticsBuffer(config=cfg)

        # Fill queue to capacity
        for i in range(10):
            await buf.enqueue(make_event("page_view", session_id=f"s{i}"))
        assert buf.qsize == 10

        # Try to add heartbeats — should be dropped
        hb_result = await buf.enqueue(make_event("heartbeat", session_id="hb"))
        assert hb_result is False

        # Try to add critical — should succeed (headroom)
        crit_result = await buf.enqueue(make_event("session_start", session_id="c1"))
        assert crit_result is True
        assert buf.qsize == 11

        # Verify dropped count
        assert buf.stats["dropped_total"] >= 1
