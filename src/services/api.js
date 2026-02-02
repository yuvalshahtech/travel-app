// Frontend API service for Travel Explorer
// Vanilla JavaScript fetch wrapper for backend endpoints

const API_BASE = (typeof window !== 'undefined' && window.__API_BASE__) ? window.__API_BASE__ : 'http://localhost:8000';

// Export API_BASE for use in other modules
export { API_BASE };

/**
 * Fetch recent hotels (limited set for homepage)
 */
export async function getRecentHotels() {
  try {
    const response = await fetch(`${API_BASE}/hotels/recent`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    return Array.isArray(data) ? data.map(normalizeHotel) : [];
  } catch (error) {
    console.error('Error fetching recent hotels:', error);
    return [];
  }
}

/**
 * Fetch hotels by city
 */
export async function getHotelsByCity(city) {
  try {
    const response = await fetch(`${API_BASE}/hotels/city/${encodeURIComponent(city)}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    return Array.isArray(data) ? data.map(normalizeHotel) : [];
  } catch (error) {
    console.error(`Error fetching hotels for city "${city}":`, error);
    return [];
  }
}

/**
 * Search hotels by query string
 */
export async function searchHotels(query) {
  try {
    const response = await fetch(`${API_BASE}/hotels/search?q=${encodeURIComponent(query)}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    return Array.isArray(data) ? data.map(normalizeHotel) : [];
  } catch (error) {
    console.error('Error searching hotels:', error);
    throw error;
  }
}

/**
 * Search hotels with filters
 */
export async function searchHotelsWithFilters(query, filters) {
  try {
    let url = `${API_BASE}/hotels/search?q=${encodeURIComponent(query)}`;
    
    if (filters.minPrice !== undefined && filters.minPrice !== '') {
      url += `&min_price=${parseFloat(filters.minPrice)}`;
    }
    if (filters.maxPrice !== undefined && filters.maxPrice !== '') {
      url += `&max_price=${parseFloat(filters.maxPrice)}`;
    }
    if (filters.guests !== undefined && filters.guests !== '') {
      url += `&guests=${parseInt(filters.guests)}`;
    }
    if (filters.minRating !== undefined && filters.minRating !== '') {
      url += `&min_rating=${parseFloat(filters.minRating)}`;
    }
    if (filters.propertyTypes !== undefined && Array.isArray(filters.propertyTypes) && filters.propertyTypes.length > 0) {
      // Send as comma-separated list
      url += `&property_types=${filters.propertyTypes.join(',')}`;
    }
    if (filters.amenities !== undefined && Array.isArray(filters.amenities) && filters.amenities.length > 0) {
      // Send as comma-separated list
      url += `&amenities=${filters.amenities.join(',')}`;
    }

    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    return Array.isArray(data) ? data.map(normalizeHotel) : [];
  } catch (error) {
    console.error('Error applying filters:', error);
    throw error;
  }
}

/**
 * Get single hotel by ID
 */
export async function getHotelById(hotelId) {
  try {
    const response = await fetch(`${API_BASE}/hotels/${hotelId}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    return normalizeHotel(data);
  } catch (error) {
    console.error(`Error fetching hotel ${hotelId}:`, error);
    throw error;
  }
}

/**
 * Check hotel availability
 */
export async function checkHotelAvailability(payload) {
  try {
    const response = await fetch(`${API_BASE}/hotels/availability`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `HTTP ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error checking availability:', error);
    throw error;
  }
}

/**
 * Create a booking and trigger confirmation email
 */
export async function createBooking(payload) {
  try {
    const response = await fetch(`${API_BASE}/hotels/bookings`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `HTTP ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error creating booking:', error);
    throw error;
  }
}

/**
 * Normalize hotel data from backend
 */
function normalizeHotel(raw) {
  // Convert relative image paths to absolute backend URLs
  let imageUrl = raw.image_url || 'https://via.placeholder.com/400x300?text=Hotel';
  
  // If image_url is a relative path (starts with /), prepend backend URL
  if (imageUrl.startsWith('/')) {
    imageUrl = `${API_BASE}${imageUrl}`;
  }

  const amenities = Array.isArray(raw.amenities) ? raw.amenities : [];
  const reviews = Array.isArray(raw.reviews) ? raw.reviews : [];
  let detailImage = raw.image || raw.image_url || imageUrl;
  if (typeof detailImage === 'string' && detailImage.startsWith('/')) {
    detailImage = `${API_BASE}${detailImage}`;
  }
  
  return {
    id: Number(raw.id),
    name: String(raw.name ?? ''),
    city: String(raw.city ?? ''),
    country: String(raw.country ?? ''),
    price: Number(raw.price ?? 0),
    rating: Number(raw.rating ?? 0),
    guests: Number(raw.guests ?? 2),
    image_url: imageUrl,
    amenities,
    image: detailImage,
    reviews,
    max_guests: Number(raw.max_guests ?? raw.guests ?? 2),
    latitude: raw.latitude != null ? Number(raw.latitude) : null,
    longitude: raw.longitude != null ? Number(raw.longitude) : null,
    description: raw.description ?? '',
    room_type: raw.room_type ?? '',
  };
}
