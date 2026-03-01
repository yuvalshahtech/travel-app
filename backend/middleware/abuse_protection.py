"""
Abuse Protection Dependencies for FastAPI Routes

Provides injectable FastAPI dependencies that enforce rate limits
on login, signup, and activity tracking endpoints.

These are NOT middleware (which runs on every request). They are
Depends() callables attached only to the endpoints that need them,
keeping unprotected endpoints fast and unaffected.

Design decisions:
  - Dependencies raise HTTPException(429) with a Retry-After header.
  - Login uses BOTH per-IP and per-email limits (dual-layer).
  - Signup uses per-IP + per-email to prevent OTP spam.
  - Activity uses per-session-id burst + sustained limits.
  - All limits are configurable via .env variables.
  - Structured logging marks every blocked request for SIEM/alerting.
  - Timing-attack protection: login always takes ≥ 200ms regardless of result.
"""

import asyncio
import logging
import os
import time
from typing import Optional, Tuple

from fastapi import HTTPException, Request

from backend.middleware.rate_limiter import (
    SlidingWindowStore,
    _parse_rate,
    activity_session_minute_key,
    activity_session_second_key,
    extract_client_ip,
    login_email_key,
    login_ip_key,
    signup_email_key,
    signup_ip_key,
    store,
)

logger = logging.getLogger(__name__)

# ─── Structured abuse logger ─────────────────────────────────────────────────
# Separate logger for security events — can be routed to a SIEM in production
abuse_logger = logging.getLogger("heavenly.abuse")


def _raise_429(retry_after: int, detail: str = "Too many requests. Please try again later."):
    """
    Raise a 429 with Retry-After header.
    Uses a generic message to avoid leaking information about which limit was hit.
    """
    raise HTTPException(
        status_code=429,
        detail=detail,
        headers={"Retry-After": str(retry_after)},
    )


# ─── Parse rate limits from env (once at import time) ────────────────────────

LOGIN_MAX, LOGIN_WINDOW = _parse_rate("LOGIN_RATE_LIMIT", "5/15minutes")
SIGNUP_MAX, SIGNUP_WINDOW = _parse_rate("SIGNUP_RATE_LIMIT", "3/1hour")
SIGNUP_EMAIL_MAX, SIGNUP_EMAIL_WINDOW = _parse_rate("SIGNUP_EMAIL_RATE_LIMIT", "3/1hour")
ACTIVITY_PER_SECOND_MAX = 1
ACTIVITY_PER_SECOND_WINDOW = 1
_act_max, _act_window = _parse_rate("ACTIVITY_RATE_LIMIT", "60/1minute")
ACTIVITY_PER_MINUTE_MAX = _act_max
ACTIVITY_PER_MINUTE_WINDOW = _act_window

# Excessive-attempt threshold: log a security warning after this many blocked requests
ABUSE_LOG_THRESHOLD = int(os.getenv("ABUSE_LOG_THRESHOLD", "10"))


# ═══════════════════════════════════════════════════════════════════════════════
# LOGIN RATE LIMITING
# ═══════════════════════════════════════════════════════════════════════════════

async def check_login_rate_limit(request: Request) -> None:
    """
    FastAPI dependency that enforces login rate limits.

    Dual-layer protection:
      Layer 1 — Per-IP: Prevents a single source from brute-forcing any account.
                Also catches multiple users behind the same NAT, but the limit
                (5/15min default) is generous enough for legitimate shared IPs.
      Layer 2 — Per-email: Prevents distributed attacks targeting one account
                (rotating IPs but same email). The email is hashed (SHA-256)
                before storage to avoid keeping PII in memory.

    Exponential backoff: Enabled on per-email rate limiting. If someone hits
    the limit repeatedly, the block time doubles each time (2s → 4s → 8s → …
    up to 30 minutes). This defeats slow brute-force attacks (1 attempt every
    2 minutes would eventually trigger backoff after 5 attempts).

    Usage:
        @router.post("/login")
        async def login(
            ...,
            _rate_check: None = Depends(check_login_rate_limit),
        ):

    The body of the login route must call `on_login_success(request, email)`
    after a successful login to reset counters.
    """
    ip = extract_client_ip(request)

    # Layer 1: Per-IP
    limited, remaining, retry_after = await store.is_rate_limited(
        key=login_ip_key(ip),
        max_requests=LOGIN_MAX,
        window_seconds=LOGIN_WINDOW,
        enable_backoff=False,  # No backoff on IP level (protects NAT users)
    )
    if limited:
        abuse_logger.warning(
            "Login rate limit (IP) triggered",
            extra={
                "ip": ip,
                "limit": f"{LOGIN_MAX}/{LOGIN_WINDOW}s",
                "retry_after": retry_after,
                "layer": "ip",
            },
        )
        _raise_429(retry_after)

    # Layer 2: Per-email — we need the email from the request body.
    # FastAPI hasn't parsed the body yet when dependencies run.
    # We'll read the raw body and extract the email field.
    # NOTE: This consumes the body stream. We store it on request.state
    # so the route handler can re-read it.
    email = await _extract_email_from_body(request)
    if email:
        limited, remaining, retry_after = await store.is_rate_limited(
            key=login_email_key(email),
            max_requests=LOGIN_MAX,
            window_seconds=LOGIN_WINDOW,
            enable_backoff=True,  # Exponential backoff on per-email
        )
        if limited:
            abuse_logger.warning(
                "Login rate limit (email) triggered",
                extra={
                    "ip": ip,
                    "email_hash": login_email_key(email),
                    "limit": f"{LOGIN_MAX}/{LOGIN_WINDOW}s",
                    "retry_after": retry_after,
                    "layer": "email",
                },
            )
            _raise_429(retry_after)


async def on_login_success(request: Request, email: str) -> None:
    """
    Reset rate-limit counters after a successful login.

    This is critical: without it, a legitimate user who mistyped their
    password 4 times would be blocked on the 5th attempt even with the
    correct password and would have to wait 15 minutes.

    Call this from the login route AFTER verifying credentials.
    """
    ip = extract_client_ip(request)
    await store.reset(login_ip_key(ip))
    await store.reset(login_email_key(email))
    logger.debug(f"Login rate limit counters reset for IP {ip}")


async def on_login_failure(request: Request, email: Optional[str] = None) -> None:
    """
    Record a failed login attempt in the rate limiter.
    
    This is called AFTER the login attempt fails. The check_login_rate_limit
    dependency already recorded the attempt in the sliding window, so this
    function is primarily for logging excessive failures.
    
    We do NOT give different error messages for "user not found" vs
    "wrong password" — both return the same generic message to prevent
    user enumeration.
    """
    ip = extract_client_ip(request)

    # Check if this IP is approaching the limit
    count = await store.get_count(login_ip_key(ip), LOGIN_WINDOW)
    if count >= ABUSE_LOG_THRESHOLD:
        abuse_logger.error(
            "Excessive login failures detected",
            extra={
                "ip": ip,
                "failed_attempts": count,
                "window_seconds": LOGIN_WINDOW,
                "email_hash": login_email_key(email) if email else None,
            },
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SIGNUP RATE LIMITING
# ═══════════════════════════════════════════════════════════════════════════════

async def check_signup_rate_limit(request: Request) -> None:
    """
    FastAPI dependency that enforces signup rate limits.

    Dual-layer:
      Layer 1 — Per-IP: Prevents mass account creation from a single source.
                Default: 3 signups per hour per IP.
      Layer 2 — Per-email: Prevents OTP spam to a single email address.
                Even if the attacker rotates IPs, the email is rate-limited.

    Race condition handling: If two simultaneous POST /signup arrive for
    the same email, the database UNIQUE constraint on email_verifications.email
    will reject the second one. The rate limiter here catches the common case
    before it even hits the DB.

    Information leakage prevention: The signup route MUST return the same
    response shape and status code regardless of whether the email already
    exists or a new OTP was sent. (See the updated route.)
    """
    ip = extract_client_ip(request)

    # Layer 1: Per-IP
    limited, remaining, retry_after = await store.is_rate_limited(
        key=signup_ip_key(ip),
        max_requests=SIGNUP_MAX,
        window_seconds=SIGNUP_WINDOW,
        enable_backoff=False,
    )
    if limited:
        abuse_logger.warning(
            "Signup rate limit (IP) triggered",
            extra={
                "ip": ip,
                "limit": f"{SIGNUP_MAX}/{SIGNUP_WINDOW}s",
                "retry_after": retry_after,
            },
        )
        _raise_429(retry_after)

    # Layer 2: Per-email
    email = await _extract_email_from_body(request)
    if email:
        limited, remaining, retry_after = await store.is_rate_limited(
            key=signup_email_key(email),
            max_requests=SIGNUP_EMAIL_MAX,
            window_seconds=SIGNUP_EMAIL_WINDOW,
            enable_backoff=False,
        )
        if limited:
            abuse_logger.warning(
                "Signup rate limit (email/OTP) triggered",
                extra={
                    "ip": ip,
                    "email_hash": signup_email_key(email),
                    "limit": f"{SIGNUP_EMAIL_MAX}/{SIGNUP_EMAIL_WINDOW}s",
                    "retry_after": retry_after,
                },
            )
            _raise_429(retry_after)


# ═══════════════════════════════════════════════════════════════════════════════
# ACTIVITY TRACKING RATE LIMITING
# ═══════════════════════════════════════════════════════════════════════════════

async def check_activity_rate_limit(request: Request, session_id: str) -> None:
    """
    Enforce rate limits on the activity tracking endpoint.

    Two tiers:
      Tier 1 — Burst: Max 1 event per second per session_id.
               Prevents replay spam (same event fired rapidly).
      Tier 2 — Sustained: Max 60 events per minute per session_id (configurable).
               Prevents sustained flooding.

    session_id is used instead of IP because:
      - Multiple tabs from the same browser each have their own session_id
        (stored in sessionStorage, not shared across tabs)
      - A NAT IP could have many legitimate sessions from different users
      - session_id is already validated as a UUID v4 by the schema

    The 2KB payload limit and event_type allow-list are enforced in the
    Pydantic schema (TrackEventRequest), not here.
    """
    # Tier 1: Burst limit (1/second)
    limited, remaining, retry_after = await store.is_rate_limited(
        key=activity_session_second_key(session_id),
        max_requests=ACTIVITY_PER_SECOND_MAX,
        window_seconds=ACTIVITY_PER_SECOND_WINDOW,
        enable_backoff=False,
    )
    if limited:
        abuse_logger.info(
            "Activity burst rate limit triggered",
            extra={
                "session_id": session_id,
                "limit": "1/1s",
                "retry_after": retry_after,
            },
        )
        _raise_429(retry_after or 1, detail="Too many events. Slow down.")

    # Tier 2: Sustained limit (60/minute default)
    limited, remaining, retry_after = await store.is_rate_limited(
        key=activity_session_minute_key(session_id),
        max_requests=ACTIVITY_PER_MINUTE_MAX,
        window_seconds=ACTIVITY_PER_MINUTE_WINDOW,
        enable_backoff=False,
    )
    if limited:
        abuse_logger.warning(
            "Activity sustained rate limit triggered",
            extra={
                "session_id": session_id,
                "limit": f"{ACTIVITY_PER_MINUTE_MAX}/{ACTIVITY_PER_MINUTE_WINDOW}s",
                "retry_after": retry_after,
            },
        )
        _raise_429(retry_after or 1, detail="Too many events. Please try again later.")


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _extract_email_from_body(request: Request) -> Optional[str]:
    """
    Extract the 'email' field from the JSON request body without consuming it.

    FastAPI dependency injection runs before the route handler parses the body.
    Starlette's Request.body() caches the result, so reading it here does NOT
    prevent the route from reading it again.

    Returns None if the body can't be parsed or has no email field.
    This is intentional — we still want the route to execute and return
    its own validation errors, not a rate-limiter error.
    """
    try:
        body = await request.body()
        if not body:
            return None
        import json
        data = json.loads(body)
        email = data.get("email")
        if isinstance(email, str) and "@" in email:
            return email.lower().strip()
    except Exception:
        pass
    return None


# ─── Timing Attack Protection ────────────────────────────────────────────────

async def constant_time_login(start_time: float, min_duration: float = 0.2) -> None:
    """
    Ensure the login endpoint always takes at least `min_duration` seconds.

    Without this, an attacker can distinguish:
      - "User not found" (fast — no bcrypt) vs
      - "Wrong password" (slow — bcrypt verify ran)

    By padding the response time to a minimum of 200ms, both cases
    take the same wall-clock time from the client's perspective.

    Call at the END of the login route, even on failure paths:
        start = time.monotonic()
        ... (login logic) ...
        await constant_time_login(start)
    """
    elapsed = time.monotonic() - start_time
    if elapsed < min_duration:
        await asyncio.sleep(min_duration - elapsed)
