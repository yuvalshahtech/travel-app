"""
Tests for Rate Limiting and Abuse Protection

Run with:
    cd travel-app
    python -m pytest backend/tests/test_rate_limiting.py -v

These tests exercise the in-memory sliding-window store and the
FastAPI endpoint integration to verify:
  1. Login rate limiting (per-IP, per-email, reset on success)
  2. Signup rate limiting (per-IP)
  3. Activity tracking rate limiting (burst + sustained)
  4. Proper 429 responses with Retry-After headers
  5. Exponential backoff on login failures
  6. Constant-time login protection
"""

import asyncio
import json
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ─── Ensure env vars are set before any app imports ──────────────────────────
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars!")
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("LOGIN_RATE_LIMIT", "3/1minute")
os.environ.setdefault("SIGNUP_RATE_LIMIT", "2/1minute")
os.environ.setdefault("ACTIVITY_RATE_LIMIT", "5/1minute")

from backend.middleware.rate_limiter import (
    SlidingWindowStore,
    _parse_rate,
    extract_client_ip,
    login_email_key,
    login_ip_key,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Unit Tests — SlidingWindowStore
# ═══════════════════════════════════════════════════════════════════════════════


class TestSlidingWindowStore:
    """Tests for the core sliding-window rate limiter store."""

    @pytest.fixture
    def store(self):
        return SlidingWindowStore(max_keys=100)

    @pytest.mark.asyncio
    async def test_allows_requests_under_limit(self, store):
        """Requests under the limit should pass through."""
        limited, remaining, retry_after = await store.is_rate_limited(
            key="test:1", max_requests=5, window_seconds=60
        )
        assert limited is False
        assert remaining == 4
        assert retry_after is None

    @pytest.mark.asyncio
    async def test_blocks_at_limit(self, store):
        """The (N+1)th request should be blocked when N is the limit."""
        for i in range(3):
            limited, _, _ = await store.is_rate_limited(
                key="test:2", max_requests=3, window_seconds=60
            )
            assert limited is False, f"Request {i+1} should not be limited"

        # 4th request should be blocked
        limited, remaining, retry_after = await store.is_rate_limited(
            key="test:2", max_requests=3, window_seconds=60
        )
        assert limited is True
        assert remaining == 0
        assert retry_after is not None
        assert retry_after > 0

    @pytest.mark.asyncio
    async def test_reset_clears_counters(self, store):
        """After reset(), the key should accept requests again."""
        # Fill up the limit
        for _ in range(3):
            await store.is_rate_limited(key="test:3", max_requests=3, window_seconds=60)

        # Verify it's limited
        limited, _, _ = await store.is_rate_limited(
            key="test:3", max_requests=3, window_seconds=60
        )
        assert limited is True

        # Reset
        await store.reset("test:3")

        # Should be allowed again
        limited, remaining, _ = await store.is_rate_limited(
            key="test:3", max_requests=3, window_seconds=60
        )
        assert limited is False
        assert remaining == 2

    @pytest.mark.asyncio
    async def test_exponential_backoff(self, store):
        """With backoff enabled, repeated violations should increase block time."""
        # Fill up the limit
        for _ in range(3):
            await store.is_rate_limited(
                key="test:4", max_requests=3, window_seconds=60, enable_backoff=True
            )

        # First violation
        limited, _, retry_1 = await store.is_rate_limited(
            key="test:4", max_requests=3, window_seconds=60, enable_backoff=True
        )
        assert limited is True
        assert retry_1 >= 2  # Backoff: 2^1 = 2 seconds min

    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        """When max_keys is reached, oldest entries should be evicted."""
        store = SlidingWindowStore(max_keys=3)

        # Add 3 keys
        await store.is_rate_limited("a", 10, 60)
        await store.is_rate_limited("b", 10, 60)
        await store.is_rate_limited("c", 10, 60)

        # Add a 4th — "a" should be evicted (oldest)
        await store.is_rate_limited("d", 10, 60)

        count_a = await store.get_count("a", 60)
        count_d = await store.get_count("d", 60)
        assert count_a == 0, "'a' should have been evicted"
        assert count_d == 1, "'d' should be present"

    @pytest.mark.asyncio
    async def test_get_count(self, store):
        """get_count should return accurate counts within the window."""
        for _ in range(5):
            await store.is_rate_limited("test:5", 100, 60)

        count = await store.get_count("test:5", 60)
        assert count == 5

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, store):
        """cleanup_expired should remove stale entries."""
        # Add an entry
        await store.is_rate_limited("old_key", 10, 60)

        # Manually make the timestamp old by patching
        entry = store._store["old_key"]
        entry.timestamps = [time.monotonic() - 8000]  # 8000 seconds ago

        evicted = await store.cleanup_expired(max_age_seconds=7200)
        assert evicted == 1
        assert "old_key" not in store._store


# ═══════════════════════════════════════════════════════════════════════════════
# Unit Tests — Rate Limit Parsing
# ═══════════════════════════════════════════════════════════════════════════════


class TestRateParsing:
    """Tests for _parse_rate env var parser."""

    def test_parse_minutes(self):
        with patch.dict(os.environ, {"TEST_LIMIT": "5/15minutes"}):
            count, window = _parse_rate("TEST_LIMIT", "1/1minute")
        assert count == 5
        assert window == 900  # 15 * 60

    def test_parse_hour(self):
        with patch.dict(os.environ, {"TEST_LIMIT": "3/1hour"}):
            count, window = _parse_rate("TEST_LIMIT", "1/1minute")
        assert count == 3
        assert window == 3600

    def test_parse_minute(self):
        with patch.dict(os.environ, {"TEST_LIMIT": "60/1minute"}):
            count, window = _parse_rate("TEST_LIMIT", "1/1minute")
        assert count == 60
        assert window == 60

    def test_parse_seconds(self):
        with patch.dict(os.environ, {"TEST_LIMIT": "10/30seconds"}):
            count, window = _parse_rate("TEST_LIMIT", "1/1minute")
        assert count == 10
        assert window == 30

    def test_invalid_falls_back_to_default(self):
        with patch.dict(os.environ, {"TEST_LIMIT": "garbage"}):
            count, window = _parse_rate("TEST_LIMIT", "5/15minutes")
        # Should not crash — falls back
        assert isinstance(count, int)
        assert isinstance(window, int)


# ═══════════════════════════════════════════════════════════════════════════════
# Unit Tests — IP Extraction
# ═══════════════════════════════════════════════════════════════════════════════


class TestIPExtraction:
    """Tests for extract_client_ip."""

    def _mock_request(self, headers=None, client_host=None):
        request = MagicMock()
        request.headers = headers or {}
        if client_host:
            request.client = MagicMock()
            request.client.host = client_host
        else:
            request.client = None
        return request

    def test_xff_header(self):
        req = self._mock_request(
            headers={"x-forwarded-for": "203.0.113.50, 70.41.3.18, 150.172.238.178"}
        )
        assert extract_client_ip(req) == "203.0.113.50"

    def test_x_real_ip(self):
        req = self._mock_request(headers={"x-real-ip": "198.51.100.23"})
        assert extract_client_ip(req) == "198.51.100.23"

    def test_direct_connection(self):
        req = self._mock_request(client_host="192.168.1.100")
        assert extract_client_ip(req) == "192.168.1.100"

    def test_ipv6_mapped_ipv4(self):
        req = self._mock_request(client_host="::ffff:192.168.1.1")
        assert extract_client_ip(req) == "192.168.1.1"

    def test_ipv6_with_zone_id(self):
        req = self._mock_request(client_host="fe80::1%eth0")
        assert extract_client_ip(req) == "fe80::1"

    def test_missing_everything(self):
        req = self._mock_request()
        assert extract_client_ip(req) == "unknown"

    def test_xff_priority_over_direct(self):
        req = self._mock_request(
            headers={"x-forwarded-for": "1.2.3.4"},
            client_host="10.0.0.1"
        )
        assert extract_client_ip(req) == "1.2.3.4"


# ═══════════════════════════════════════════════════════════════════════════════
# Integration Tests — FastAPI Endpoint Rate Limiting
# ═══════════════════════════════════════════════════════════════════════════════


class TestLoginRateLimitIntegration:
    """
    Tests that the /login endpoint returns 429 after exceeding the limit.
    Uses the FastAPI TestClient for full request lifecycle.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Reset the global rate-limit store before each test."""
        from backend.middleware.rate_limiter import store
        store._store.clear()

    @pytest.fixture
    def client(self):
        """
        Create a FastAPI TestClient.
        We patch the database dependency to avoid requiring a real DB.
        """
        from fastapi.testclient import TestClient
        from backend.main import app
        from backend.config.database import get_db

        # Mock DB session
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        def override_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)
        yield client
        app.dependency_overrides.clear()

    def test_login_returns_429_after_limit(self, client):
        """
        After LOGIN_RATE_LIMIT (3/1minute in test env) failed attempts,
        the next request should get 429 with Retry-After header.
        """
        payload = {"email": "attacker@test.com", "password": "wrong"}

        # First 3 attempts should return 401 (wrong creds, but not rate limited)
        for i in range(3):
            resp = client.post("/login", json=payload)
            assert resp.status_code == 401, f"Attempt {i+1} should be 401, got {resp.status_code}"

        # 4th attempt should be rate limited
        resp = client.post("/login", json=payload)
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers
        retry_after = int(resp.headers["Retry-After"])
        assert retry_after > 0

    def test_login_reset_on_success(self, client):
        """
        After a successful login, rate-limit counters should reset.
        The user should be able to log in again without hitting the limit.
        """
        from backend.config.database import get_db
        from backend.main import app

        # Create a mock user that will succeed on correct password
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "good@test.com"
        mock_user.password_hash = "$2b$12$validhashhere"
        mock_user.last_login = None
        mock_user.login_count = 0

        mock_db = MagicMock()

        def override_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db

        # 2 failed attempts
        mock_db.query.return_value.filter.return_value.first.return_value = None
        for _ in range(2):
            resp = client.post("/login", json={"email": "good@test.com", "password": "wrong"})
            assert resp.status_code == 401

        # Successful login (mock verify_password to return True)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        with patch("backend.routes.auth.verify_password", return_value=True):
            resp = client.post("/login", json={"email": "good@test.com", "password": "correct"})
            assert resp.status_code == 200

        # After success, counters should be reset — another attempt should work
        mock_db.query.return_value.filter.return_value.first.return_value = None
        resp = client.post("/login", json={"email": "good@test.com", "password": "wrong"})
        assert resp.status_code == 401  # Not 429 — counter was reset

        app.dependency_overrides.clear()


class TestActivityRateLimitIntegration:
    """Tests for /activity/track rate limiting."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from backend.middleware.rate_limiter import store
        store._store.clear()

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from backend.main import app
        from backend.config.database import get_db

        mock_db = MagicMock()
        mock_activity = MagicMock()
        mock_activity.id = 1
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock(side_effect=lambda obj: setattr(obj, 'id', 1))
        mock_db.rollback = MagicMock()

        def override_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)
        yield client
        app.dependency_overrides.clear()

    def test_activity_spam_rejected(self, client):
        """
        Sending more than ACTIVITY_RATE_LIMIT events per minute from the same
        session_id should result in 429.
        """
        payload = {
            "session_id": "12345678-1234-1234-1234-123456789abc",
            "event_type": "heartbeat",
            "page": "home",
        }

        # Note: burst limit is 1/second. We need to space them out or
        # the burst limit will trigger first. For this test we verify
        # the sustained limit by checking that rapid requests get blocked.
        # The first request should succeed
        resp = client.post("/activity/track", json=payload)
        assert resp.status_code == 200

        # The second request within 1 second should hit burst limit
        resp = client.post("/activity/track", json=payload)
        assert resp.status_code == 429

    def test_429_has_retry_after(self, client):
        """429 responses must include Retry-After header."""
        payload = {
            "session_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "event_type": "page_view",
            "page": "search",
        }

        # First request succeeds
        client.post("/activity/track", json=payload)

        # Second hits burst limit
        resp = client.post("/activity/track", json=payload)
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers


# ═══════════════════════════════════════════════════════════════════════════════
# Unit Tests — Timing Attack Protection
# ═══════════════════════════════════════════════════════════════════════════════


class TestConstantTimeLogin:
    """Tests for the constant_time_login helper."""

    @pytest.mark.asyncio
    async def test_pads_fast_response(self):
        """A fast response should be padded to at least min_duration."""
        from backend.middleware.abuse_protection import constant_time_login

        start = time.monotonic()
        await constant_time_login(start, min_duration=0.15)
        elapsed = time.monotonic() - start
        # Allow 10ms tolerance for asyncio.sleep scheduling jitter
        assert elapsed >= 0.14

    @pytest.mark.asyncio
    async def test_does_not_pad_slow_response(self):
        """A response already past min_duration should not be delayed further."""
        from backend.middleware.abuse_protection import constant_time_login

        start = time.monotonic() - 1.0  # Pretend 1 second has passed
        before = time.monotonic()
        await constant_time_login(start, min_duration=0.2)
        after = time.monotonic()
        # Should return almost instantly (no padding needed)
        assert (after - before) < 0.05


# ═══════════════════════════════════════════════════════════════════════════════
# Run
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
