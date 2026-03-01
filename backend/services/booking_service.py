"""
Booking service - business logic for booking operations
Handles transactions, race condition prevention, and pricing calculations
"""
import logging
from typing import Optional, Dict, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
import json
from models.models import Booking, Hotel, UserActivity

logger = logging.getLogger(__name__)


class BookingService:
    """Booking business logic with production-grade features"""
    
    # Pricing constants
    CLEANING_FEE = 500
    PLATFORM_FEE_PERCENT = 0.10
    GST_PERCENT = 0.18
    
    @staticmethod
    def check_availability(
        db: Session,
        hotel_id: int,
        check_in_date: str,
        check_out_date: str,
        guest_count: int
    ) -> Dict[str, any]:
        """
        Check if hotel is available for dates
        Prevents race conditions using database-level locks
        """
        try:
            # Get hotel
            hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
            if not hotel:
                logger.warning(f"Hotel {hotel_id} not found")
                return {"available": False, "message": "Hotel not found"}
            
            # Check guest capacity
            if guest_count > hotel.guests:
                logger.info(f"Guest count {guest_count} exceeds capacity {hotel.guests}")
                return {
                    "available": False,
                    "message": f"Maximum capacity is {hotel.guests} guests"
                }
            
            # Check for overlapping bookings (with FOR UPDATE lock for race condition prevention)
            overlapping = db.query(Booking).filter(
                and_(
                    Booking.hotel_id == hotel_id,
                    Booking.status != 'cancelled',
                    Booking.check_in_date < check_out_date,
                    Booking.check_out_date > check_in_date
                )
            ).with_for_update().all()
            
            if overlapping:
                logger.info(f"Hotel {hotel_id} has overlapping bookings for {check_in_date}-{check_out_date}")
                return {"available": False, "message": "Hotel not available for these dates"}
            
            logger.info(f"Hotel {hotel_id} is available for {check_in_date}-{check_out_date}")
            return {"available": True, "message": "Hotel is available"}
        
        except Exception as e:
            logger.error(f"Error checking availability: {e}", exc_info=True)
            raise
    
    @staticmethod
    def calculate_pricing(base_price: float, nights: int) -> Dict[str, float]:
        """
        Calculate transparent pricing with full breakdown
        
        Returns:
            Dict with room_charges, cleaning_fee, platform_fee, gst, total_payable
        """
        try:
            room_charges = base_price * nights
            cleaning_fee = BookingService.CLEANING_FEE
            subtotal = room_charges + cleaning_fee
            
            platform_fee = subtotal * BookingService.PLATFORM_FEE_PERCENT
            subtotal_with_platform = subtotal + platform_fee
            
            gst = subtotal_with_platform * BookingService.GST_PERCENT
            total_payable = subtotal + platform_fee + gst
            
            pricing = {
                "room_charges": round(room_charges, 2),
                "cleaning_fee": cleaning_fee,
                "platform_fee": round(platform_fee, 2),
                "gst": round(gst, 2),
                "total_payable": round(total_payable, 2),
                "nights": nights,
                "base_price_per_night": base_price
            }
            
            logger.debug(f"Calculated pricing: {pricing}")
            return pricing
        except Exception as e:
            logger.error(f"Error calculating pricing: {e}", exc_info=True)
            raise
    
    @staticmethod
    def create_booking(
        db: Session,
        hotel_id: int,
        user_id: int,
        check_in_date: str,
        check_out_date: str,
        guest_count: int
    ) -> Dict[str, any]:
        """
        Create booking with transaction and race condition prevention
        Uses database transaction for atomicity
        """
        try:
            # Double-check availability (pessimistic locking)
            availability = BookingService.check_availability(
                db, hotel_id, check_in_date, check_out_date, guest_count
            )
            
            if not availability["available"]:
                raise ValueError(availability["message"])
            
            # Get hotel details
            hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
            if not hotel:
                raise ValueError("Hotel not found")
            
            # Calculate pricing
            from datetime import datetime as dt
            check_in = dt.strptime(check_in_date, "%Y-%m-%d")
            check_out = dt.strptime(check_out_date, "%Y-%m-%d")
            nights = (check_out - check_in).days
            
            if nights <= 0:
                raise ValueError("Check-out date must be after check-in date")
            
            pricing = BookingService.calculate_pricing(hotel.price, nights)
            
            # Create booking record
            booking = Booking(
                hotel_id=hotel_id,
                user_id=user_id,
                check_in_date=check_in_date,
                check_out_date=check_out_date,
                guests=guest_count,
                price=hotel.price,
                total_price=pricing["room_charges"],
                total_payable=pricing["total_payable"],
                price_snapshot=pricing,  # Store complete breakdown
                status='confirmed'
            )
            
            # Add, commit, and refresh booking
            db.add(booking)
            db.commit()
            db.refresh(booking)
            
            logger.info(f"Booking created: booking_id={booking.booking_id}, user={user_id}, hotel={hotel_id}")
            
            return {
                "booking_id": booking.booking_id,
                "message": "Booking confirmed",
                "pricing": pricing
            }
        
        except Exception as e:
            logger.error(f"Error creating booking: {e}", exc_info=True)
            db.rollback()
            raise
    
    @staticmethod
    def get_user_booking_history(db: Session, user_id: int) -> List[Booking]:
        """Get all bookings for a user"""
        try:
            bookings = db.query(Booking).filter(
                Booking.user_id == user_id
            ).order_by(Booking.created_at.desc()).all()
            logger.info(f"Retrieved {len(bookings)} bookings for user {user_id}")
            return bookings
        except Exception as e:
            logger.error(f"Error fetching user bookings: {e}", exc_info=True)
            raise
    
    @staticmethod
    def get_booking_by_id(db: Session, booking_id: int) -> Optional[Booking]:
        """Get specific booking"""
        try:
            booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
            return booking
        except Exception as e:
            logger.error(f"Error fetching booking {booking_id}: {e}", exc_info=True)
            raise
