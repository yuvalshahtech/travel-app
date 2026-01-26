// Frontend API service for Travel Explorer
// Centralizes fetch logic with timeouts, abort support, caching, and validation
// Version: 1.1 - Updated to use backend:8000 directly

const DEFAULT_TIMEOUT_MS = 12000;
const CACHE_TTL_MS = 30000; // 30s cache for non-search endpoints

const cache = new Map();

function getBaseUrl() {
  // When served from port 3000 (Python http.server), point to backend on 8000
  // Backend must have CORS enabled
  return 'http://localhost:8000';
}

function makeCacheKey(path) {
  return path;
}

function setCache(key, data) {
  cache.set(key, { data, ts: Date.now() });
}

function getCache(key) {
  const entry = cache.get(key);
  if (!entry) return null;
  if (Date.now() - entry.ts > CACHE_TTL_MS) {
    cache.delete(key);
    return null;
  }
  return entry.data;
}

function normalizeHotel(raw) {
  // Basic shape enforcement and type normalization
  const backendUrl = 'http://localhost:8000';
  let imageUrl = raw.image_url || 'https://via.placeholder.com/400x300?text=Hotel';
  
  // Convert relative /uploads paths to absolute backend URLs
  if (imageUrl.startsWith('/uploads/')) {
    imageUrl = backendUrl + imageUrl;
  }
  
  return {
    id: Number(raw.id),
    name: String(raw.name ?? ''),
    city: String(raw.city ?? ''),
    country: String(raw.country ?? ''),
    price: Number(raw.price ?? 0),
    rating: Number(raw.rating ?? 0),
    image_url: imageUrl,
    latitude: raw.latitude != null ? Number(raw.latitude) : raw.latitude,
    longitude: raw.longitude != null ? Number(raw.longitude) : raw.longitude,
    description: raw.description ?? undefined,
    room_type: raw.room_type ?? undefined,
  };
}

async function request(path, { signal, timeoutMs = DEFAULT_TIMEOUT_MS, cacheable = false } = {}) {
  const base = getBaseUrl();
  const url = base + path;

  const cacheKey = cacheable ? makeCacheKey(url) : null;
  if (cacheable) {
    const cached = getCache(cacheKey);
    if (cached) return cached;
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  // If caller provides a signal, tie them together
  const compositeSignal = signal ? mergeSignals(signal, controller.signal) : controller.signal;

  try {
    const resp = await fetch(url, { method: 'GET', headers: { 'Accept': 'application/json' }, signal: compositeSignal });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    if (cacheable && cacheKey) setCache(cacheKey, data);
    return data;
  } finally {
    clearTimeout(timeout);
  }
}

// Utility to merge two AbortSignals (abort if either aborts)
function mergeSignals(a, b) {
  const ctrl = new AbortController();
  const onAbort = () => ctrl.abort();
  if (a) a.addEventListener('abort', onAbort);
  if (b) b.addEventListener('abort', onAbort);
  return ctrl.signal;
}

export async function getRecentHotels(options) {
  const data = await request('/hotels/recent', { cacheable: true, ...(options || {}) });
  return Array.isArray(data) ? data.map(normalizeHotel) : [];
}

export async function getHotelsByCity(city, options) {
  const data = await request(`/hotels/city/${encodeURIComponent(city)}`, { cacheable: true, ...(options || {}) });
  return Array.isArray(data) ? data.map(normalizeHotel) : [];
}

export async function searchHotels(query, options) {
  const data = await request(`/hotels/search?q=${encodeURIComponent(query)}`, { cacheable: false, ...(options || {}) });
  return Array.isArray(data) ? data.map(normalizeHotel) : [];
}

export async function getHotelById(id, options) {
  const data = await request(`/hotels/${id}`, { cacheable: true, ...(options || {}) });
  // Endpoint returns a single hotel object
  return normalizeHotel(data);
}
