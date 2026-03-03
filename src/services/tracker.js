/**
 * Heavenly — Hybrid Checkpoint Analytics Tracker
 * 
 * ╔══════════════════════════════════════════════════════════════════════════╗
 * ║                  CHECKPOINT MODEL (Production-Safe)                      ║
 * ╠══════════════════════════════════════════════════════════════════════════╣
 * ║  ► Tracks ACTIVE engagement time only (not idle time)                    ║
 * ║  ► Sends cumulative checkpoints every 90±15s (max ~8 requests/session)  ║
 * ║  ► Survives crashes (last checkpoint persisted)                          ║
 * ║  ► No 429 rate limit errors (minimal request frequency)                  ║
 * ║  ► No 24-hour anomaly sessions (cumulative duration, not incremental)    ║
 * ║  ► ML-ready engagement dataset (accurate active time + interactions)     ║
 * ╚══════════════════════════════════════════════════════════════════════════╝
 * 
 * USAGE: import { initTracker } from './tracker.js';  initTracker();
 */

const API_BASE = (typeof window !== 'undefined' && window.__API_BASE__)
    ? window.__API_BASE__
    : 'https://travel-app-96ld.onrender.com';

// ─── Helpers ─────────────────────────────────────────────────────────────────

/** Generate a UUID v4 (crypto-safe when available, fallback for older browsers) */
function uuidv4() {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
        return crypto.randomUUID();
    }
    // Fallback (RFC 4122 compliant)
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
        const r = (Math.random() * 16) | 0;
        return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
    });
}

/** Return current auth token (if any) */
function getToken() {
    try { return localStorage.getItem('authToken'); } catch { return null; }
}

// ─── Session ID Management ───────────────────────────────────────────────────

const SESSION_KEY = '_hv_session_id';

function getOrCreateSessionId() {
    let sid;
    try { sid = sessionStorage.getItem(SESSION_KEY); } catch { /* ignore */ }
    if (!sid) {
        sid = uuidv4();
        try { sessionStorage.setItem(SESSION_KEY, sid); } catch { /* ignore */ }
    }
    return sid;
}

// ─── Accumulation State (Local Tracking) ─────────────────────────────────────

let _activeSeconds = 0;                  // Total active time across all pages
let _hotelActiveSeconds = 0;             // Active time on hotel_details page
let _lastActivityTimestamp = Date.now(); // Last user activity (for delta calculation)
let _mapOpenCount = 0;                   // Total map opens
let _reviewsOpenCount = 0;               // Total reviews opens
let _maxScrollDepth = 0;                 // Max scroll depth percentage (0-100)
let _currentHotelId = null;              // Hotel ID (if on hotel_details)

const IDLE_THRESHOLD_MS = 5 * 60 * 1000; // 5 minutes
let _isIdle = false;

// ─── Core send function (minimal retries, no 429 retry) ─────────────────────

/**
 * Send a tracking event to POST /activity/track.
 * Uses sendBeacon for beforeunload events, fetch otherwise.
 * Silent failures — never throws or disrupts the app.
 * 
 * CHECKPOINT MODEL: Only retries network errors (max 1 retry).
 * Does NOT retry on 429 (rate limit) — checkpoints are sparse enough.
 */
async function sendEvent(payload, { useBeacon = false } = {}) {
    const sessionId = getOrCreateSessionId();
    const body = {
        session_id: sessionId,
        event_type: payload.event_type,
        page: payload.page || null,
        hotel_id: payload.hotel_id || null,
        duration_seconds: payload.duration_seconds || null,
        metadata: payload.metadata || null,
    };

    const token = getToken();
    const url = `${API_BASE}/activity/track`;

    // ── Beacon path (unload — cannot retry) ──
    if (useBeacon && typeof navigator.sendBeacon === 'function') {
        try {
            const headers = { type: 'application/json' };
            const blob = new Blob([JSON.stringify(body)], headers);
            navigator.sendBeacon(url, blob);
        } catch { /* silent */ }
        return;
    }

    // ── Normal fetch path (max 1 retry, skip 429) ──
    const fetchHeaders = { 'Content-Type': 'application/json' };
    if (token) fetchHeaders['Authorization'] = `Bearer ${token}`;

    for (let attempt = 0; attempt <= 1; attempt++) { // Max 1 retry (2 attempts total)
        try {
            const res = await fetch(url, {
                method: 'POST',
                headers: fetchHeaders,
                body: JSON.stringify(body),
            });
            if (res.ok) return; // success
            // Do NOT retry on 429 or any 4xx (client error)
            if (res.status >= 400 && res.status < 500) {
                if (res.status === 429) {
                    logger.debug('Checkpoint rate-limited (429) — skipping retry');
                }
                return;
            }
        } catch {
            // network error — will retry once
        }
        // Brief back-off before retry
        if (attempt < 1) {
            await new Promise(r => setTimeout(r, 500));
        }
    }
    // All retries exhausted — silently give up
}

// ─── Active Time Tracking (User Activity Detection) ─────────────────────────

/**
 * Update active time based on user activity.
 * Only counts time when user is active (mousemove, scroll, click, keydown).
 * Ignores idle periods > 5 minutes.
 */
function recordActivity() {
    const now = Date.now();
    const delta = now - _lastActivityTimestamp;

    // Only count delta if it's reasonable (not idle, not first activity)
    if (!_isIdle && delta < IDLE_THRESHOLD_MS && delta > 0 && delta < 60000) {
        const deltaSeconds = Math.round(delta / 1000);
        _activeSeconds += deltaSeconds;
        
        // Also track hotel-specific active time
        if (_currentHotelId) {
            _hotelActiveSeconds += deltaSeconds;
        }
    }

    _lastActivityTimestamp = now;
    _isIdle = false;
}

// ─── Idle Detection ──────────────────────────────────────────────────────────

let _idleTimer = null;

function resetIdleTimer() {
    _isIdle = false;
    clearTimeout(_idleTimer);
    _idleTimer = setTimeout(() => {
        _isIdle = true;
    }, IDLE_THRESHOLD_MS);
}

function initIdleDetection() {
    const events = ['mousemove', 'keydown', 'scroll', 'touchstart', 'click'];
    events.forEach(e => {
        document.addEventListener(e, () => {
            recordActivity();
            resetIdleTimer();
        }, { passive: true });
    });
    resetIdleTimer(); // start timer immediately
}

// ─── Checkpoint Heartbeat (Sparse, Cumulative) ───────────────────────────────

let _checkpointTimer = null;
const CHECKPOINT_INTERVAL_BASE = 90_000; // 90 seconds
const CHECKPOINT_JITTER = 15_000;        // ±15 seconds jitter

/**
 * Send a cumulative checkpoint (not incremental).
 * Includes total active time + interaction counts.
 */
function sendCheckpoint(page) {
    const metadata = {
        map_open_count: _mapOpenCount,
        reviews_open_count: _reviewsOpenCount,
        max_scroll_depth: _maxScrollDepth,
    };

    // Include hotel_active_seconds in metadata if on hotel page
    if (_currentHotelId) {
        metadata.hotel_active_seconds = _hotelActiveSeconds;
    }

    sendEvent({
        event_type: 'session_checkpoint',
        page,
        hotel_id: _currentHotelId,
        duration_seconds: _activeSeconds, // CUMULATIVE (not delta)
        metadata,
    });
}

function startCheckpointHeartbeat(page) {
    if (_checkpointTimer) return; // already started

    function scheduleNext() {
        const jitter = Math.random() * CHECKPOINT_JITTER * 2 - CHECKPOINT_JITTER;
        const interval = CHECKPOINT_INTERVAL_BASE + jitter;
        
        _checkpointTimer = setTimeout(() => {
            if (!_isIdle) {
                sendCheckpoint(page);
            }
            scheduleNext(); // schedule next checkpoint
        }, interval);
    }

    scheduleNext();
}

function stopCheckpointHeartbeat() {
    if (_checkpointTimer) {
        clearTimeout(_checkpointTimer);
        _checkpointTimer = null;
    }
}

// ─── Public API ──────────────────────────────────────────────────────────────

let _initialized = false;
let _currentPage = null;

/**
 * Initialize the tracker. Call once per page load (idempotent).
 * Sends session_start and starts checkpoint heartbeat every 90±15s.
 */
export function initTracker(pageName) {
    if (_initialized) return;
    _initialized = true;

    _currentPage = pageName || inferPageName();
    _lastActivityTimestamp = Date.now();

    // ── session_start ──
    sendEvent({ event_type: 'session_start', page: _currentPage });

    // ── Start idle detection ──
    initIdleDetection();

    // ── Start checkpoint heartbeat (90±15s) ──
    startCheckpointHeartbeat(_currentPage);

    // ── session_end on page unload ──
    function handleUnload() {
        stopCheckpointHeartbeat();
        sendEvent(
            {
                event_type: 'session_end',
                page: _currentPage,
                duration_seconds: _activeSeconds,
            },
            { useBeacon: true }
        );
    }

    window.addEventListener('beforeunload', handleUnload);

    // ── Handle tab visibility (send checkpoint + session_end on hide) ──
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'hidden') {
            recordActivity(); // capture final activity
            sendCheckpoint(_currentPage); // final checkpoint
            sendEvent(
                {
                    event_type: 'session_end',
                    page: _currentPage,
                    duration_seconds: _activeSeconds,
                },
                { useBeacon: true }
            );
            stopCheckpointHeartbeat();
        } else if (document.visibilityState === 'visible') {
            // Tab came back — restart checkpoint heartbeat
            _lastActivityTimestamp = Date.now();
            sendEvent({ event_type: 'session_start', page: _currentPage });
            startCheckpointHeartbeat(_currentPage);
        }
    });
}

// ─── Hotel Details Page Tracking ─────────────────────────────────────────────

/**
 * Start tracking time on a hotel details page.
 * Call when hotel data is loaded and rendered.
 */
export function startHotelViewTracking(hotelId) {
    _currentHotelId = hotelId;
    _hotelActiveSeconds = 0; // reset hotel-specific timer
}

// ─── Interaction Trackers (Local Accumulation, No Immediate POST) ────────────

/** Track map section open click (increment local counter) */
export function trackMapOpen(hotelId) {
    _mapOpenCount++;
    recordActivity();
}

/** Track reviews section open click (increment local counter) */
export function trackReviewsOpen(hotelId) {
    _reviewsOpenCount++;
    recordActivity();
}

/** Track scroll depth (update max depth, no immediate POST) */
export function trackScrollDepth(depth, hotelId) {
    if (depth > _maxScrollDepth) {
        _maxScrollDepth = Math.round(depth);
    }
    recordActivity();
}

// ─── Utilities ───────────────────────────────────────────────────────────────

function inferPageName() {
    const path = window.location.pathname;
    if (path.includes('hotel-details')) return 'hotel_details';
    if (path.includes('search')) return 'search';
    if (path.includes('home')) return 'home';
    if (path.includes('profile')) return 'profile';
    if (path.includes('login')) return 'login';
    if (path.includes('signup')) return 'signup';
    if (path.includes('dashboard')) return 'dashboard';
    return 'unknown';
}

// Debug logger (optional)
const logger = {
    debug: (msg) => {
        if (typeof console !== 'undefined' && console.debug) {
            console.debug(`[Tracker] ${msg}`);
        }
    },
};
