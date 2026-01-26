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
            description TEXT,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    print("Database initialized successfully")

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
def create_hotel(name, city, country, latitude, longitude, price, room_type, rating=4.5, description=None, image_url=None):
    """Create a new hotel"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO hotels (name, city, country, latitude, longitude, price, room_type, rating, description, image_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, city, country, latitude, longitude, price, room_type, rating, description, image_url))
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