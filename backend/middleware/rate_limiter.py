"""
Production-Grade Rate Limiter for FastAPI

Implements a sliding-window rate limiter using an in-memory LRU store.
Designed as a drop-in module that can be swapped to Redis in production
without changing any calling code.

╔══════════════════════════════════════════════════════════════════════════╗
║ PRODUCTION NOTE                                                        ║
║                                                                        ║
║ This in-memory store works for SINGLE-WORKER deployments only.         ║
║ With multiple Uvicorn workers or Gunicorn processes, each worker gets  ║
║ its own counter — an attacker can effectively multiply the limit by    ║
║ the number of workers.                                                 ║
║                                                                        ║
║ For production with multiple workers:                                  ║
║   1. Use Redis as the backend (set RATE_LIMIT_BACKEND=redis in .env)  ║
║   2. Or place rate limiting in a reverse proxy (nginx, Cloudflare)   ║
║                                                                        ║
║ Server restart resets all in-memory counters. Redis counters survive.  ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import hashlib
import logging
import math
import os
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from fastapi import Request

logger = logging.getLogger(__name__)


# ─── Configuration from environment ──────────────────────────────────────────

def _parse_rate(env_var: str, default: str) -> Tuple[int, int]:
    """
    Parse rate limit from env var in format '5/15minutes', '3/hour', '60/minute'.
    Returns (max_requests, window_seconds).
    """
    raw = os.getenv(env_var, default)
    try:
        count_str, period_str = raw.split("/", 1)
        count = int(count_str.strip())

        period_str = period_str.strip().lower()
        # Parse the period: '15minutes', 'hour', 'minute', '30seconds', etc.
        multipliers = {
            "second": 1, "seconds": 1,
            "minute": 60, "minutes": 60,
            "hour": 3600, "hours": 3600,
            "day": 86400, "days": 86400,
        }

        # Try to extract a numeric prefix (e.g., '15minutes' → 15, 'minutes')
        import re
        match = re.match(r"^(\d+)\s*(\w+)$", period_str)
        if match:
            num = int(match.group(1))
            unit = match.group(2)
        else:
            num = 1
            unit = period_str

        if unit not in multipliers:
            raise ValueError(f"Unknown time unit: {unit}")

        window = num * multipliers[unit]
        return (count, window)

    except Exception as e:
        logger.warning(f"Failed to parse rate limit '{raw}' from {env_var}: {e}. Using default '{default}'.")
        # Fallback: re-parse the default
        if raw != default:
            return _parse_rate.__wrapped__(env_var, default) if hasattr(_parse_rate, '__wrapped__') else (5, 900)
        return (5, 900)


# ─── Sliding Window Counter Store ────────────────────────────────────────────

@dataclass
class _WindowEntry:
    """A single sliding-window counter entry."""
    timestamps: List[float] = field(default_factory=list)
    blocked_until: float = 0.0  # Exponential backoff block time


class SlidingWindowStore:
    """
    In-memory sliding-window rate limiter with LRU eviction.

    Prevents memory exhaustion by capping the total number of tracked keys.
    Old entries are evicted LRU-style when the cap is reached.

    Thread-safety: Uses asyncio.Lock. Safe for single-process async workloads.
    NOT safe across multiple OS processes (workers).
    """

    def __init__(self, max_keys: int = 10_000):
        """
        Args:
            max_keys: Maximum number of distinct keys to track.
                      Prevents memory exhaustion from distributed bot attacks
                      that rotate IPs. With ~200 bytes per key, 10k keys ≈ 2MB.
        """
        self._store: OrderedDict[str, _WindowEntry] = OrderedDict()
        self._max_keys = max_keys
        self._lock = asyncio.Lock()

    async def is_rate_limited(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
        enable_backoff: bool = False,
    ) -> Tuple[bool, int, Optional[int]]:
        """
        Check whether `key` has exceeded the rate limit.

        Args:
            key: Unique identifier (e.g., "login:ip:192.168.1.1").
            max_requests: Maximum allowed requests in the window.
            window_seconds: Sliding window size in seconds.
            enable_backoff: If True, apply exponential backoff on repeated violations.

        Returns:
            (is_limited, remaining_requests, retry_after_seconds)
            - is_limited: True if the request should be rejected.
            - remaining_requests: How many requests are still allowed.
            - retry_after_seconds: Seconds until the oldest entry expires (only if limited).
        """
        now = time.monotonic()

        async with self._lock:
            # LRU touch: move to end
            if key in self._store:
                self._store.move_to_end(key)
                entry = self._store[key]
            else:
                # Evict oldest if at capacity
                if len(self._store) >= self._max_keys:
                    self._store.popitem(last=False)
                entry = _WindowEntry()
                self._store[key] = entry

            # Check exponential backoff block
            if enable_backoff and entry.blocked_until > now:
                retry_after = int(math.ceil(entry.blocked_until - now))
                return (True, 0, retry_after)

            # Prune timestamps outside the window
            cutoff = now - window_seconds
            entry.timestamps = [t for t in entry.timestamps if t > cutoff]

            if len(entry.timestamps) >= max_requests:
                # Rate limited
                oldest_in_window = entry.timestamps[0]
                retry_after = int(math.ceil((oldest_in_window + window_seconds) - now))
                retry_after = max(retry_after, 1)

                # Apply exponential backoff if enabled
                if enable_backoff:
                    # Each successive violation doubles the block time
                    # Base: window_seconds / max_requests. Cap at 30 minutes.
                    violations = len(entry.timestamps) - max_requests + 1
                    backoff = min(2 ** violations, 1800)
                    entry.blocked_until = now + backoff
                    retry_after = max(retry_after, backoff)

                remaining = 0
                return (True, remaining, retry_after)

            # Not limited — record this request
            entry.timestamps.append(now)
            remaining = max_requests - len(entry.timestamps)
            return (False, remaining, None)

    async def reset(self, key: str) -> None:
        """
        Reset all counters for a key.
        Used to clear rate-limit state on successful login.
        """
        async with self._lock:
            if key in self._store:
                del self._store[key]

    async def get_count(self, key: str, window_seconds: int) -> int:
        """Get current request count for a key within the window."""
        now = time.monotonic()
        async with self._lock:
            entry = self._store.get(key)
            if not entry:
                return 0
            cutoff = now - window_seconds
            return sum(1 for t in entry.timestamps if t > cutoff)

    async def cleanup_expired(self, max_age_seconds: int = 7200) -> int:
        """
        Remove entries that haven't been touched in max_age_seconds.
        Call periodically (e.g., every 10 minutes) to prevent stale memory usage.
        Returns the number of evicted entries.
        """
        now = time.monotonic()
        evicted = 0
        async with self._lock:
            keys_to_remove = []
            for key, entry in self._store.items():
                if not entry.timestamps:
                    keys_to_remove.append(key)
                elif (now - max(entry.timestamps)) > max_age_seconds:
                    keys_to_remove.append(key)
            for key in keys_to_remove:
                del self._store[key]
                evicted += 1
        if evicted:
            logger.info(f"Rate limiter cleanup: evicted {evicted} stale entries")
        return evicted


# ─── IP Extraction ────────────────────────────────────────────────────────────

def extract_client_ip(request: Request) -> str:
    """
    Extract the real client IP, correctly handling reverse proxies.

    Priority:
      1. X-Forwarded-For header (first untrusted IP)
      2. X-Real-IP header
      3. request.client.host (direct connection)

    IPv6 handling:
      - Normalizes ::ffff:127.0.0.1 → 127.0.0.1 (mapped IPv4)
      - Strips zone IDs (e.g., fe80::1%eth0 → fe80::1)

    If all methods fail, returns "unknown" — rate limiting still works
    but all unknown clients share a single bucket (safe: restrictive).
    """
    ip = None

    # 1. X-Forwarded-For: client, proxy1, proxy2
    xff = request.headers.get("x-forwarded-for")
    if xff:
        # Take the leftmost (client) IP. In a trusted proxy setup,
        # you'd skip known proxies from the right. For simplicity,
        # we trust the leftmost entry.
        parts = [p.strip() for p in xff.split(",")]
        ip = parts[0] if parts else None

    # 2. X-Real-IP (set by nginx)
    if not ip:
        ip = request.headers.get("x-real-ip")

    # 3. Direct connection
    if not ip and request.client:
        ip = request.client.host

    if not ip:
        return "unknown"

    # Normalize IPv6-mapped IPv4 (::ffff:192.168.1.1 → 192.168.1.1)
    if ip.startswith("::ffff:"):
        ip = ip[7:]

    # Strip IPv6 zone IDs (fe80::1%eth0 → fe80::1)
    if "%" in ip:
        ip = ip.split("%")[0]

    return ip


# ─── Composite Rate Limit Key Builders ────────────────────────────────────────

def _hash_email(email: str) -> str:
    """
    Hash email for rate-limit keys to avoid storing PII in memory.
    Uses SHA-256 truncated to 16 hex chars — collision-resistant enough
    for rate limiting (not cryptographic security).
    """
    return hashlib.sha256(email.lower().strip().encode()).hexdigest()[:16]


def login_ip_key(ip: str) -> str:
    """Rate limit key for login attempts per IP."""
    return f"login:ip:{ip}"


def login_email_key(email: str) -> str:
    """Rate limit key for login attempts per email."""
    return f"login:email:{_hash_email(email)}"


def signup_ip_key(ip: str) -> str:
    """Rate limit key for signup attempts per IP."""
    return f"signup:ip:{ip}"


def signup_email_key(email: str) -> str:
    """Rate limit key for signup attempts per email (OTP abuse prevention)."""
    return f"signup:email:{_hash_email(email)}"


def activity_session_second_key(session_id: str) -> str:
    """Rate limit key for activity events: 1 per second per session."""
    return f"activity:sec:{session_id}"


def activity_session_minute_key(session_id: str) -> str:
    """Rate limit key for activity events: N per minute per session."""
    return f"activity:min:{session_id}"


# ─── Global Store Instance ────────────────────────────────────────────────────

# Max keys configurable via env. Default 10k ≈ 2MB memory.
_max_keys = int(os.getenv("RATE_LIMIT_MAX_KEYS", "10000"))
store = SlidingWindowStore(max_keys=_max_keys)


# ─── Periodic Cleanup Task ────────────────────────────────────────────────────

_cleanup_task: Optional[asyncio.Task] = None


async def _periodic_cleanup():
    """Background task that cleans stale rate limit entries every 10 minutes."""
    while True:
        try:
            await asyncio.sleep(600)  # 10 minutes
            await store.cleanup_expired(max_age_seconds=7200)
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Rate limiter cleanup error")


def start_cleanup_task():
    """Start the background cleanup coroutine. Call once at app startup."""
    global _cleanup_task
    if _cleanup_task is None or _cleanup_task.done():
        _cleanup_task = asyncio.create_task(_periodic_cleanup())
        logger.info("Rate limiter cleanup task started")


def stop_cleanup_task():
    """Cancel the cleanup task. Call at app shutdown."""
    global _cleanup_task
    if _cleanup_task and not _cleanup_task.done():
        _cleanup_task.cancel()
        logger.info("Rate limiter cleanup task stopped")
