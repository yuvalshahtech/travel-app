import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_FILE = os.path.join(BASE_DIR, "auth.db")

def get_db_connection():
    """Create and return a database connection"""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize the database and create tables if they don't exist"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Extra safety: ensure unique index exists even if schema was created differently before
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique ON users(email);
    """)
    
    # Create email_verifications table for OTP verification
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            otp TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create hotels table for travel discovery
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hotels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            city TEXT NOT NULL,
            country TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            price REAL NOT NULL,
            room_type TEXT NOT NULL,
            rating REAL DEFAULT 4.5,
            guests INTEGER DEFAULT 2,
            description TEXT,
            image_url TEXT,
            amenities TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create bookings table for reservations
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
            hotel_id INTEGER NOT NULL,
            check_in_date TEXT NOT NULL,
            check_out_date TEXT NOT NULL,
            guests INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'confirmed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (hotel_id) REFERENCES hotels(id)
        )
    """)

    # Indexes for faster availability checks
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_bookings_hotel_id ON bookings(hotel_id);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_bookings_dates ON bookings(check_in_date, check_out_date);
    """)
    
    # Add guests column to existing tables (for backwards compatibility)
    try:
        cursor.execute("ALTER TABLE hotels ADD COLUMN guests INTEGER DEFAULT 2")
        conn.commit()
    except sqlite3.OperationalError:
        # Column already exists, skip
        pass
    
    # Add amenities column to existing tables (for backwards compatibility)
    try:
        cursor.execute("ALTER TABLE hotels ADD COLUMN amenities TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        # Column already exists, skip
        pass
    
    # Add user_id column to bookings table (for user-specific booking history)
    try:
        cursor.execute("ALTER TABLE bookings ADD COLUMN user_id INTEGER")
        conn.commit()
    except sqlite3.OperationalError:
        # Column already exists, skip
        pass
    
    # Add price column to bookings table
    try:
        cursor.execute("ALTER TABLE bookings ADD COLUMN price REAL")
        conn.commit()
    except sqlite3.OperationalError:
        # Column already exists, skip
        pass
    
    conn.commit()
    conn.close()

def get_user_by_email(email):
    """Get user by email"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    return user

def create_user(email, password_hash):
    """Create a new user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email, password_hash)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return user_id
    except sqlite3.IntegrityError:
        conn.close()
        return None

def user_exists(email):
    """Check if user exists"""
    user = get_user_by_email(email)
    return user is not None

def create_email_verification(email, password_hash, otp, expires_at):
    """Store email verification record"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO email_verifications (email, password_hash, otp, expires_at)
            VALUES (?, ?, ?, ?)
        """, (email, password_hash, otp, expires_at))
        conn.commit()
        verification_id = cursor.lastrowid
        conn.close()
        return verification_id
    except sqlite3.IntegrityError:
        # Email already in verification, delete old one and create new
        cursor.execute("DELETE FROM email_verifications WHERE email = ?", (email,))
        conn.commit()
        cursor.execute("""
            INSERT INTO email_verifications (email, password_hash, otp, expires_at)
            VALUES (?, ?, ?, ?)
        """, (email, password_hash, otp, expires_at))
        conn.commit()
        verification_id = cursor.lastrowid
        conn.close()
        return verification_id

def get_email_verification(email):
    """Get email verification record"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM email_verifications WHERE email = ?", (email,))
    record = cursor.fetchone()
    conn.close()
    return record

def delete_email_verification(email):
    """Delete email verification record after successful verification"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM email_verifications WHERE email = ?", (email,))
    conn.commit()
    conn.close()
    
def email_verification_exists(email):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM email_verifications WHERE email = ?",
        (email,)
    )
    exists = cursor.fetchone() is not None
    conn.close()
    return exists
# Hotel-related functions
def create_hotel(name, city, country, latitude, longitude, price, room_type, rating=4.5, guests=2, description=None, image_url=None, amenities=None):
    """Create a new hotel with guest capacity and amenities"""
    import json
    
    # Convert amenities list to JSON string
    amenities_json = None
    if amenities:
        amenities_json = json.dumps(amenities)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO hotels (name, city, country, latitude, longitude, price, room_type, rating, guests, description, image_url, amenities)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, city, country, latitude, longitude, price, room_type, rating, guests, description, image_url, amenities_json))
    conn.commit()
    hotel_id = cursor.lastrowid
    conn.close()
    return hotel_id

def get_hotel_by_id(hotel_id):
    """Get hotel by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hotels WHERE id = ?", (hotel_id,))
    hotel = cursor.fetchone()
    conn.close()
    return hotel

def get_recent_hotels(limit=10):
    """Get recently listed hotels ordered by creation date"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM hotels ORDER BY created_at DESC LIMIT ?
    """, (limit,))
    hotels = cursor.fetchall()
    conn.close()
    return hotels

def get_hotels_by_city(city, limit=50):
    """Get hotels filtered by city"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM hotels WHERE city = ? ORDER BY created_at DESC LIMIT ?
    """, (city, limit))
    hotels = cursor.fetchall()
    conn.close()
    return hotels

def search_hotels(query, limit=50):
    """Search hotels by name, city, or country"""
    conn = get_db_connection()
    cursor = conn.cursor()
    search_term = f"%{query}%"
    cursor.execute("""
        SELECT * FROM hotels 
        WHERE name LIKE ? OR city LIKE ? OR country LIKE ?
        ORDER BY created_at DESC LIMIT ?
    """, (search_term, search_term, search_term, limit))
    hotels = cursor.fetchall()
    conn.close()
    return hotels

def search_hotels_with_filters(query, limit=50, min_price=None, max_price=None, guests=None, min_rating=None, property_types=None, amenities=None):
    """
    Search hotels by name, city, or country with optional filters.
    
    Args:
        query: Search term (required)
        limit: Maximum results to return (default 50)
        min_price: Minimum price filter in INR (optional, None = no minimum)
        max_price: Maximum price filter in INR (optional, None = no maximum)
        guests: Minimum guest capacity (optional, None = no filter)
        min_rating: Minimum rating filter (0-5 stars) (optional, None = no filter)
        property_types: List of property types to filter by (optional, matches against room_type field)
        amenities: List of amenities to filter by (optional, matches against amenities JSON field)
    
    Returns:
        List of hotel records matching search and filter criteria
    """
    import json
    conn = get_db_connection()
    cursor = conn.cursor()
    search_term = f"%{query}%"
    
    # Build WHERE clause dynamically for extensibility
    where_clauses = [
        "(name LIKE ? OR city LIKE ? OR country LIKE ?)"
    ]
    params = [search_term, search_term, search_term]
    
    # Add price filtering if provided
    if min_price is not None:
        where_clauses.append("price >= ?")
        params.append(min_price)
    
    if max_price is not None:
        where_clauses.append("price <= ?")
        params.append(max_price)
    
    # Add guest capacity filtering if provided
    if guests is not None:
        where_clauses.append("guests >= ?")
        params.append(guests)
    
    # Add rating filtering if provided
    if min_rating is not None:
        where_clauses.append("rating >= ?")
        params.append(min_rating)
    
    # Add property type filtering if provided (match against room_type field)
    if property_types is not None and len(property_types) > 0:
        # Use OR logic to match any of the selected property types
        # Match: "Entire villa" contains "Villa", "Private room" contains "Room", etc.
        property_conditions = []
        for prop_type in property_types:
            property_conditions.append("room_type LIKE ?")
            params.append(f"%{prop_type}%")
        where_clauses.append(f"({' OR '.join(property_conditions)})")
    
    # Construct final query
    where_clause = " AND ".join(where_clauses)
    query_str = f"""
        SELECT * FROM hotels 
        WHERE {where_clause}
        ORDER BY created_at DESC LIMIT ?
    """
    params.append(limit)
    
    cursor.execute(query_str, params)
    hotels = cursor.fetchall()
    conn.close()
    
    # Post-filter by amenities (AND logic - hotel must have ALL selected amenities)
    if amenities is not None and len(amenities) > 0:
        filtered_hotels = []
        for hotel in hotels:
            hotel_amenities = []
            if hotel["amenities"]:
                try:
                    hotel_amenities = json.loads(hotel["amenities"])
                except:
                    hotel_amenities = []
            
            # Check if hotel has all required amenities
            if all(amenity in hotel_amenities for amenity in amenities):
                filtered_hotels.append(hotel)
        return filtered_hotels
    
    return hotels

def get_overlapping_bookings(hotel_id, check_in_date, check_out_date):
    """Get overlapping confirmed bookings for a hotel within a date range"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM bookings
        WHERE hotel_id = ?
          AND status = 'confirmed'
          AND check_in_date < ?
          AND check_out_date > ?
        """,
        (hotel_id, check_out_date, check_in_date)
    )
    bookings = cursor.fetchall()
    conn.close()
    return bookings

def create_booking(hotel_id, check_in_date, check_out_date, guests, status="confirmed", user_id=None, price=None):
    """Create a booking record and return booking_id"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO bookings (hotel_id, check_in_date, check_out_date, guests, status, user_id, price)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (hotel_id, check_in_date, check_out_date, guests, status, user_id, price)
    )
    conn.commit()
    booking_id = cursor.lastrowid
    conn.close()
    return booking_id

def get_hotel_bookings(hotel_id):
    """Get all confirmed bookings for a hotel, sorted by check_in_date"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT check_in_date, check_out_date
        FROM bookings
        WHERE hotel_id = ? AND status = 'confirmed'
        ORDER BY check_in_date ASC
        """,
        (hotel_id,)
    )
    bookings = cursor.fetchall()
    conn.close()
    return bookings

def merge_date_ranges(ranges):
    """
    Merge overlapping or adjacent date ranges.
    
    Input: List of tuples [(start_date_str, end_date_str), ...]
    Output: List of merged tuples with no overlaps
    
    Algorithm:
    1. Sort ranges by start date
    2. Iterate through and merge adjacent/overlapping ranges
    3. Return merged list
    
    Example:
    - Input: [('2026-02-10', '2026-02-12'), ('2026-02-11', '2026-02-15')]
    - Output: [('2026-02-10', '2026-02-15')]
    """
    if not ranges:
        return []
    
    # Sort ranges by start date
    sorted_ranges = sorted(ranges, key=lambda x: x[0])
    
    merged = [sorted_ranges[0]]
    
    for current_start, current_end in sorted_ranges[1:]:
        last_start, last_end = merged[-1]
        
        # Check if current range overlaps or is adjacent to the last merged range
        # Adjacent means: last_end equals current_start (no gap between them)
        # Overlapping means: current_start <= last_end (current starts before or when last ends)
        if current_start <= last_end:
            # Merge by extending the end date if current_end is later
            merged[-1] = (last_start, max(last_end, current_end))
        else:
            # No overlap, add as new range
            merged.append((current_start, current_end))
    
    return merged

def get_user_bookings(user_id):
    """Get all bookings for a specific user with hotel details"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            b.booking_id,
            b.hotel_id,
            h.name as hotel_name,
            b.check_in_date,
            b.check_out_date,
            b.guests,
            b.status,
            b.price,
            h.price as hotel_nightly_rate,
            b.created_at
        FROM bookings b
        JOIN hotels h ON b.hotel_id = h.id
        WHERE b.user_id = ?
        ORDER BY b.check_in_date DESC
    """, (user_id,))
    bookings = cursor.fetchall()
    conn.close()
    return bookings
