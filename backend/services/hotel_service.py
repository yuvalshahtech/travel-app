"""
Hotel service - business logic for hotel operations
Separated from routes for better maintainability
"""
import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from models.models import Hotel, Booking, UserActivity
from datetime import datetime

logger = logging.getLogger(__name__)


class HotelService:
    """Hotel business logic"""
    
    @staticmethod
    def get_recent_hotels(db: Session, limit: int = 8) -> List[Hotel]:
        """Get recently added hotels"""
        try:
            hotels = db.query(Hotel).order_by(desc(Hotel.created_at)).limit(limit).all()
            logger.info(f"Retrieved {len(hotels)} recent hotels")
            return hotels
        except Exception as e:
            logger.error(f"Error fetching recent hotels: {e}", exc_info=True)
            raise
    
    @staticmethod
    def get_hotels_by_city(db: Session, city: str) -> List[Hotel]:
        """Get all hotels in a city"""
        try:
            hotels = db.query(Hotel).filter(
                Hotel.city.ilike(f"%{city}%")
            ).all()
            logger.info(f"Found {len(hotels)} hotels in {city}")
            return hotels
        except Exception as e:
            logger.error(f"Error fetching hotels by city: {e}", exc_info=True)
            raise
    
    @staticmethod
    def search_hotels(db: Session, query: str) -> List[Hotel]:
        """Search hotels by keyword"""
        try:
            search_term = f"%{query}%"
            hotels = db.query(Hotel).filter(
                or_(
                    Hotel.name.ilike(search_term),
                    Hotel.city.ilike(search_term),
                    Hotel.description.ilike(search_term)
                )
            ).all()
            logger.info(f"Search '{query}' returned {len(hotels)} results")
            return hotels
        except Exception as e:
            logger.error(f"Error searching hotels: {e}", exc_info=True)
            raise
    
    @staticmethod
    def search_hotels_with_filters(
        db: Session,
        query_text: str,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_rating: Optional[float] = None,
        guests: Optional[int] = None,
        property_types: Optional[List[str]] = None,
        amenities: Optional[List[str]] = None
    ) -> List[Hotel]:
        """Advanced hotel search with filters"""
        try:
            query = db.query(Hotel)
            
            # Multi-field search filter (city, name, description)
            if query_text:
                # Special case: "india" returns all hotels (all hotels are in India)
                if query_text.lower() != "india":
                    search_term = f"%{query_text}%"
                    query = query.filter(
                        or_(
                            Hotel.city.ilike(search_term),
                            Hotel.name.ilike(search_term),
                            Hotel.description.ilike(search_term)
                        )
                    )
            
            # Price filters
            if min_price is not None:
                query = query.filter(Hotel.price >= min_price)
            if max_price is not None:
                query = query.filter(Hotel.price <= max_price)
            
            # Rating filter
            if min_rating is not None:
                query = query.filter(Hotel.rating >= min_rating)
            
            # Guest capacity filter
            if guests is not None:
                query = query.filter(Hotel.guests >= guests)
            
            # Property type filter (partial match for flexible frontend values)
            # Frontend sends simplified values like "Villa", "Apartment", "Room"
            # DB stores descriptive values like "Entire villa", "Private room"
            if property_types:
                property_conditions = [
                    Hotel.room_type.ilike(f"%{ptype}%") for ptype in property_types
                ]
                query = query.filter(or_(*property_conditions))
            
            # Amenities filter (JSON array contains)
            if amenities:
                for amenity in amenities:
                    # PostgreSQL JSON array contains
                    query = query.filter(Hotel.amenities.op('?')(amenity))
            
            results = query.all()
            logger.info(f"Advanced search returned {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Error in advanced hotel search: {e}", exc_info=True)
            raise
    
    @staticmethod
    def get_hotel_by_id(db: Session, hotel_id: int) -> Optional[Hotel]:
        """Get hotel by ID"""
        try:
            hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
            if not hotel:
                logger.warning(f"Hotel {hotel_id} not found")
            return hotel
        except Exception as e:
            logger.error(f"Error fetching hotel {hotel_id}: {e}", exc_info=True)
            raise
