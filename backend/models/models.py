"""
SQLAlchemy ORM models for PostgreSQL
Replaces simple schema definitions with full ORM models
"""
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, Text, 
    ForeignKey, JSON, Index, UniqueConstraint, Numeric, ForeignKeyConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from backend.config.database import Base


class User(Base):
    """User model with authentication and tracking"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Tracking
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime, nullable=True)
    login_count = Column(Integer, default=0)
    
    # Relationships
    bookings = relationship("Booking", back_populates="user", cascade="all, delete-orphan")
    activities = relationship("UserActivity", back_populates="user", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_users_email', 'email'),
        Index('idx_users_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


class EmailVerification(Base):
    """Temporary email verification records (OTP)"""
    __tablename__ = "email_verifications"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    otp = Column(String(6), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index('idx_email_verifications_email', 'email'),
        Index('idx_email_verifications_expires_at', 'expires_at'),
    )
    
    def __repr__(self):
        return f"<EmailVerification(email={self.email})>"


class Hotel(Base):
    """Hotel listings"""
    __tablename__ = "hotels"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    city = Column(String(100), nullable=False, index=True)
    country = Column(String(100), nullable=False)
    
    # Location (GPS coordinates)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # Pricing & basic info
    price = Column(Float, nullable=False, index=True)  # Base price per night
    room_type = Column(String(50), nullable=False)
    rating = Column(Float, default=4.5, index=True)
    guests = Column(Integer, default=2)
    
    # Content
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    amenities = Column(JSON, nullable=True)  # JSON array: ["Wi-Fi", "Pool", ...]
    
    # Audit trail
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    bookings = relationship("Booking", back_populates="hotel", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_hotels_city', 'city'),
        Index('idx_hotels_price', 'price'),
        Index('idx_hotels_rating', 'rating'),
        Index('idx_hotels_created_at', 'created_at'),
        Index('idx_hotels_location', latitude, longitude),  # Geo index
    )
    
    def __repr__(self):
        return f"<Hotel(id={self.id}, name={self.name}, city={self.city})>"


class Booking(Base):
    """Hotel bookings with full audit trail"""
    __tablename__ = "bookings"
    
    booking_id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    hotel_id = Column(Integer, ForeignKey('hotels.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    
    # Dates
    check_in_date = Column(String(10), nullable=False)  # YYYY-MM-DD format
    check_out_date = Column(String(10), nullable=False)
    
    # Guest info
    guests = Column(Integer, nullable=False)
    
    # Pricing snapshot (store price at booking time)
    price = Column(Float, nullable=True)  # Price per night (base)
    total_price = Column(Float, nullable=True)  # Total: base × nights
    total_payable = Column(Float, nullable=True)  # After fees and taxes
    price_snapshot = Column(JSON, nullable=True)  # Full price breakdown at booking time
    
    # Status & audit
    status = Column(String(20), default='confirmed', nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    hotel = relationship("Hotel", back_populates="bookings")
    user = relationship("User", back_populates="bookings")
    
    __table_args__ = (
        ForeignKeyConstraint(['hotel_id'], ['hotels.id'], ondelete='CASCADE'),
        ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        Index('idx_bookings_hotel_id', 'hotel_id'),
        Index('idx_bookings_user_id', 'user_id'),
        Index('idx_bookings_status', 'status'),
        Index('idx_bookings_dates', check_in_date, check_out_date),
        Index('idx_bookings_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Booking(id={self.booking_id}, hotel={self.hotel_id}, user={self.user_id})>"


class UserActivity(Base):
    """User behavior tracking for analytics"""
    __tablename__ = "user_activity"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # User reference (nullable for anonymous tracking)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    
    # Legacy columns (kept for backward compatibility with old records)
    action_type = Column(String(50), nullable=False, index=True)
    activity_event = Column(JSON, nullable=True)
    
    # ── New engagement-tracking columns ──
    session_id = Column(String(36), nullable=True, index=True)  # UUID v4
    page = Column(String(100), nullable=True)  # e.g. "home", "hotel_details", "search"
    hotel_id = Column(Integer, nullable=True, index=True)  # hotel context (nullable)
    event_type = Column(String(50), nullable=True, index=True)  # granular event name
    duration_seconds = Column(Integer, nullable=True)  # client-reported duration
    event_metadata = Column(JSONB, nullable=True)  # flexible JSONB payload (max 2 KB enforced in API)
    
    # Timestamp
    timestamp = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    
    # Relationship
    user = relationship("User", back_populates="activities")
    
    __table_args__ = (
        Index('idx_user_activity_user_id', 'user_id'),
        Index('idx_user_activity_action_type', 'action_type'),
        Index('idx_user_activity_timestamp', 'timestamp'),
        Index('idx_user_activity_user_action', 'user_id', 'action_type'),
        Index('idx_user_activity_session_id', 'session_id'),
        Index('idx_user_activity_event_type', 'event_type'),
        Index('idx_user_activity_session_event', 'session_id', 'event_type'),
    )
    
    def __repr__(self):
        return f"<UserActivity(id={self.id}, user={self.user_id}, action={self.action_type}, event={self.event_type})>"


# Import for convenience
__all__ = [
    'Base',
    'User',
    'EmailVerification',
    'Hotel',
    'Booking',
    'UserActivity'
]
