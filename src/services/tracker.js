/**
 * Heavenly — User Engagement Tracker
 * 
 * Tracks session lifecycle, page views, hotel detail interactions (map, reviews),
 * and page duration. Works for both authenticated and anonymous users.
 * 
 * USAGE — import { initTracker } from './tracker.js';  initTracker();
 */

const API_BASE = (typeof window !== 'undefined' && window.__API_BASE__)
    ? window.__API_BASE__
    : 'http://localhost:8000';

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

// ─── Core send function (fire-and-forget, retry up to 2×) ───────────────────

const MAX_RETRIES = 2;

/**
 * Send a tracking event to POST /activity/track.
 * Uses sendBeacon for beforeunload events, fetch otherwise.
 * Silent failures — never throws or disrupts the app.
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
            // sendBeacon cannot send custom headers, but the endpoint accepts
            // anonymous users too so user_id will be NULL on those.
            // We build a Blob with Content-Type so FastAPI can parse the JSON body.
            const blob = new Blob([JSON.stringify(body)], headers);
            navigator.sendBeacon(url, blob);
        } catch { /* silent */ }
        return;
    }

    // ── Normal fetch path (with retry) ──
    const fetchHeaders = { 'Content-Type': 'application/json' };
    if (token) fetchHeaders['Authorization'] = `Bearer ${token}`;

    for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
        try {
            const res = await fetch(url, {
                method: 'POST',
                headers: fetchHeaders,
                body: JSON.stringify(body),
            });
            if (res.ok) return; // success
            // Non-retryable status (validation error, etc.)
            if (res.status >= 400 && res.status < 500) return;
        } catch {
            // network error — will retry
        }
        // Brief back-off before retry
        if (attempt < MAX_RETRIES) {
            await new Promise(r => setTimeout(r, 500 * (attempt + 1)));
        }
    }
    // All retries exhausted — silently give up
}

// ─── Idle Detection ──────────────────────────────────────────────────────────

const IDLE_THRESHOLD_MS = 5 * 60 * 1000; // 5 minutes

/** Returns a controller that tracks mouse/keyboard to detect idle */
function createIdleDetector(onIdle, onResume) {
    let idleTimer = null;
    let isIdle = false;

    function resetTimer() {
        if (isIdle) {
            isIdle = false;
            onResume();
        }
        clearTimeout(idleTimer);
        idleTimer = setTimeout(() => {
            isIdle = true;
            onIdle();
        }, IDLE_THRESHOLD_MS);
    }

    const events = ['mousemove', 'keydown', 'scroll', 'touchstart', 'click'];
    events.forEach(e => document.addEventListener(e, resetTimer, { passive: true }));
    resetTimer(); // start timer immediately

    return {
        destroy() {
            clearTimeout(idleTimer);
            events.forEach(e => document.removeEventListener(e, resetTimer));
        },
        get idle() { return isIdle; },
    };
}

// ─── Public API ──────────────────────────────────────────────────────────────

let _initialized = false;
let _heartbeatTimer = null;
let _sessionStartTime = null;
let _idleDetector = null;
let _isIdle = false;

/**
 * Initialize the tracker. Call once per page load (idempotent).
 * Sends session_start, sets up heartbeat every 15 s, and registers
 * beforeunload/visibilitychange handlers for session_end.
 */
export function initTracker(pageName) {
    if (_initialized) return;
    _initialized = true;

    _sessionStartTime = Date.now();
    const page = pageName || inferPageName();

    // ── session_start ──
    sendEvent({ event_type: 'session_start', page });

    // ── page_view ──
    sendEvent({ event_type: 'page_view', page });

    // ── Heartbeat every 15 s (paused while idle) ──
    _heartbeatTimer = setInterval(() => {
        if (!_isIdle) {
            sendEvent({ event_type: 'heartbeat', page });
        }
    }, 15_000);

    // ── Idle detection ──
    _idleDetector = createIdleDetector(
        () => { _isIdle = true; },
        () => { _isIdle = false; },
    );

    // ── session_end on page unload ──
    function handleUnload() {
        const duration = Math.round((Date.now() - _sessionStartTime) / 1000);
        sendEvent({ event_type: 'session_end', page, duration_seconds: duration }, { useBeacon: true });
        clearInterval(_heartbeatTimer);
        _idleDetector?.destroy();
    }

    window.addEventListener('beforeunload', handleUnload);

    // ── Handle tab visibility (pause heartbeats, send session_end on hide) ──
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'hidden') {
            const duration = Math.round((Date.now() - _sessionStartTime) / 1000);
            sendEvent({ event_type: 'session_end', page, duration_seconds: duration }, { useBeacon: true });
            clearInterval(_heartbeatTimer);
        } else if (document.visibilityState === 'visible') {
            // Tab came back — start new session segment
            _sessionStartTime = Date.now();
            sendEvent({ event_type: 'session_start', page });
            _heartbeatTimer = setInterval(() => {
                if (!_isIdle) {
                    sendEvent({ event_type: 'heartbeat', page });
                }
            }, 15_000);
        }
    });
}

// ─── Hotel Details Page Tracking ─────────────────────────────────────────────

let _hotelViewStart = null;
let _currentHotelId = null;

/**
 * Start tracking time on a hotel details page.
 * Call when hotel data is loaded and rendered.
 */
export function startHotelViewTracking(hotelId) {
    _currentHotelId = hotelId;
    _hotelViewStart = Date.now();

    // Send hotel_view end on tab hide / navigation
    function handleEnd() {
        flushHotelView();
    }

    window.addEventListener('beforeunload', handleEnd);
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'hidden') {
            flushHotelView();
        } else if (document.visibilityState === 'visible') {
            // User returned — restart timer
            _hotelViewStart = Date.now();
        }
    });
}

/**
 * Flush hotel_view duration event (idempotent — clears start time after sending).
 */
function flushHotelView() {
    if (_hotelViewStart && _currentHotelId) {
        const duration = Math.round((Date.now() - _hotelViewStart) / 1000);
        if (duration > 0) {
            sendEvent(
                { event_type: 'hotel_view', page: 'hotel_details', hotel_id: _currentHotelId, duration_seconds: duration },
                { useBeacon: true },
            );
        }
        _hotelViewStart = null;
    }
}

// ─── Interaction Trackers ────────────────────────────────────────────────────

/** Track map section open click */
export function trackMapOpen(hotelId) {
    sendEvent({ event_type: 'map_open', page: 'hotel_details', hotel_id: hotelId });
}

/** Track reviews section open click */
export function trackReviewsOpen(hotelId) {
    sendEvent({ event_type: 'reviews_open', page: 'hotel_details', hotel_id: hotelId });
}

/** Track scroll depth (optional, call with percentage 0–100) */
export function trackScrollDepth(depth, hotelId) {
    sendEvent({
        event_type: 'scroll_depth',
        page: hotelId ? 'hotel_details' : inferPageName(),
        hotel_id: hotelId || null,
        metadata: { depth_percent: depth },
    });
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
