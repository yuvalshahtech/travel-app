from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
from datetime import date
from pathlib import Path
import random
from sqlalchemy.orm import Session
import json
from backend.schemas.hotel import (
    HotelDetails,
    AvailabilityRequest,
    AvailabilityResponse,
    BookingRequest,
    BookingResponse,
    UserBooking,
    UserBookingListResponse
)
from backend.config.database import get_db
from backend.models.models import Hotel, Booking, User as UserModel
from backend.services.hotel_service import HotelService
from backend.services.booking_service import BookingService
from backend.services.auth_service import AuthService
from backend.utils.email import send_booking_confirmation_email
from backend.utils.jwt_auth import get_current_user_id, get_optional_user_id
from backend.utils.activity_logger import log_user_activity

router = APIRouter(prefix="/hotels", tags=["hotels"])

UPLOADS_DIR = Path(__file__).resolve().parents[1] / "uploads" / "hotels"


def _hget(hotel, key, default=None):
    if isinstance(hotel, dict):
        return hotel.get(key, default)
    return getattr(hotel, key, default)


def _parse_amenities(raw_amenities):
    if raw_amenities is None:
        return []
    if isinstance(raw_amenities, list):
        return raw_amenities
    if isinstance(raw_amenities, str):
        try:
            return json.loads(raw_amenities)
        except Exception:
            return []
    return []


def _serialize_hotel_summary(hotel):
    return {
        "id": _hget(hotel, "id"),
        "name": _hget(hotel, "name"),
        "city": _hget(hotel, "city"),
        "country": _hget(hotel, "country"),
        "latitude": _hget(hotel, "latitude"),
        "longitude": _hget(hotel, "longitude"),
        "price": _hget(hotel, "price"),
        "room_type": _hget(hotel, "room_type"),
        "rating": _hget(hotel, "rating"),
        "guests": _hget(hotel, "guests") if _hget(hotel, "guests") is not None else 2,
        "image_url": _hget(hotel, "image_url"),
        "amenities": _parse_amenities(_hget(hotel, "amenities")),
    }


def _merge_date_ranges(ranges):
    if not ranges:
        return []
    sorted_ranges = sorted(ranges, key=lambda item: item[0])
    merged = [list(sorted_ranges[0])]
    for start, end in sorted_ranges[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1][1] = max(last_end, end)
        else:
            merged.append([start, end])
    return [(start, end) for start, end in merged]

def generate_reviews(hotel):
    amenities = _parse_amenities(_hget(hotel, "amenities"))

    rating = float(_hget(hotel, "rating", 4.2) or 4.2)
    price = float(_hget(hotel, "price", 0) or 0)
    room_type = (_hget(hotel, "room_type", "") or "").lower()
    city = _hget(hotel, "city", "") or ""
    description = (_hget(hotel, "description", "") or "").lower()

    rng = random.Random(int(_hget(hotel, "id")))

    if rating >= 4.5:
        review_count = rng.randint(6, 8)
    elif rating >= 4.0:
        review_count = rng.randint(4, 6)
    else:
        review_count = rng.randint(3, 4)

    name_pool = [
        "Aarav · India", "Diya · India", "Kabir · India", "Ishita · India",
        "Ananya · India", "Nikhil · India", "Meera · India", "Arjun · India",
        "Sofia · UAE", "Liam · UK", "Mia · USA", "Ethan · Canada",
        "Ava · Australia", "Noah · Germany", "Elena · Spain", "Hana · Japan",
        "Oliver · France", "Lucas · Brazil", "Layla · Singapore", "Zara · South Africa"
    ]

    amenity_mentions = []
    if "Pool" in amenities:
        amenity_mentions.append("the pool")
    if "Wi-Fi" in amenities:
        amenity_mentions.append("the Wi-Fi")
    if "AC" in amenities:
        amenity_mentions.append("the AC")
    if "Kitchen" in amenities:
        amenity_mentions.append("the kitchen")
    if "Beach access" in amenities:
        amenity_mentions.append("the beach access")

    location_terms = []
    if any(k in description for k in ["beach", "beachfront", "sea", "ocean"]):
        location_terms.append("sea views")
    if any(k in description for k in ["central", "downtown", "city center"]):
        location_terms.append("central location")
    if "quiet" in description or "peace" in description:
        location_terms.append("quiet surroundings")
    if "luxury" in description or "premium" in description:
        location_terms.append("premium feel")

    price_note = None
    if price >= 6500:
        price_note = "premium but worth it"
    elif price <= 3000:
        price_note = "great value for money"
    else:
        price_note = "priced fairly for the area"

    room_context = "entire place" if "entire" in room_type else "room"

    positives = [
        "Spotless and well maintained",
        "Check-in was smooth",
        "Comfortable stay overall",
        "Exactly as described",
        "Felt safe and welcoming",
    ]

    small_issues = [
        "Wi-Fi dipped once",
        "Slight street noise at night",
        "Hot water took a minute",
        "AC could be cooler",
        "Power backup kicked in briefly",
    ]

    templates = {
        "very_positive": [
            "{pos}. Loved {amenity} and the {location}.",
            "{pos}. The {amenity} was excellent and it felt like a {room_context} with great privacy.",
            "{pos}. {price_note}.",
            "{pos}. {location} made it memorable."
        ],
        "positive": [
            "{pos}. {amenity} was solid, though {issue}.",
            "{pos}. {location} and {amenity} were highlights. {price_note}.",
            "{pos}. Comfortable {room_context}, but {issue}.",
        ],
        "mixed": [
            "Decent stay overall. {amenity} helped, but {issue}.",
            "Nice {room_context} and {location}, yet {issue}.",
            "Okay experience. {price_note}, though {issue}.",
        ],
    }

    def pick_amenity_text():
        if amenity_mentions:
            return rng.choice(amenity_mentions)
        return "the basics"

    def pick_location_text():
        if location_terms:
            return rng.choice(location_terms)
        return f"{city.lower()} location" if city else "location"

    reviews = []
    target_rating = max(1.0, min(5.0, rating))
    
    # Step 1: Generate initial review ratings with small variance around target
    initial_ratings = []
    for idx in range(review_count):
        variance = rng.uniform(-0.4, 0.4)
        initial_rating = target_rating + variance
        initial_rating = max(1.0, min(5.0, initial_rating))
        initial_ratings.append(initial_rating)
    
    # Step 2: Calculate current average and delta
    current_avg = sum(initial_ratings) / len(initial_ratings)
    delta = target_rating - current_avg
    
    # Step 3: Distribute delta evenly across all reviews
    adjusted_ratings = []
    for rating_val in initial_ratings:
        adjusted = rating_val + (delta / len(initial_ratings))
        adjusted = max(1.0, min(5.0, adjusted))
        adjusted_ratings.append(adjusted)
    
    # Step 4: Final verification and adjustment
    final_avg = sum(adjusted_ratings) / len(adjusted_ratings)
    if abs(final_avg - target_rating) > 0.05 and len(adjusted_ratings) > 0:
        # Adjust the last review to compensate
        correction = target_rating - final_avg
        adjusted_ratings[-1] = max(1.0, min(5.0, adjusted_ratings[-1] + correction))
    
    # Generate review content
    for idx in range(review_count):
        name = name_pool[(int(_hget(hotel, "id")) + idx * 3) % len(name_pool)]
        score = adjusted_ratings[idx]

        if score >= 4.5:
            tone = "very_positive"
        elif score >= 4.0:
            tone = "positive"
        else:
            tone = "mixed"

        template = rng.choice(templates[tone])
        comment = template.format(
            pos=rng.choice(positives),
            amenity=pick_amenity_text(),
            location=pick_location_text(),
            price_note=price_note,
            room_context=room_context,
            issue=rng.choice(small_issues)
        )

        reviews.append({
            "user": name,
            "rating": round(score, 1),
            "comment": comment,
        })

    return reviews

@router.get("/recent")
async def get_recent(db: Session = Depends(get_db)):
    """Get recently listed hotels"""
    hotels = HotelService.get_recent_hotels(db=db, limit=10)
    if not hotels:
        return []
    
    return [_serialize_hotel_summary(hotel) for hotel in hotels]

@router.get("/city/{city}")
async def get_by_city(city: str, db: Session = Depends(get_db)):
    """Get hotels in a specific city"""
    hotels = HotelService.get_hotels_by_city(db=db, city=city)
    if not hotels:
        return []
    
    return [_serialize_hotel_summary(hotel) for hotel in hotels]

@router.get("/search")
async def search(
    q: str = "", 
    min_price: float = Query(None, ge=0), 
    max_price: float = Query(None, ge=0),
    guests: int = Query(None, ge=1),
    min_rating: float = Query(None, ge=0, le=5),
    property_types: str = Query(None),
    amenities: str = Query(None),
    current_user_id: Optional[int] = Depends(get_optional_user_id),
    db: Session = Depends(get_db)
):
    """
    Search hotels by name, city, or country with optional filters.
    
    Query Parameters:
    - q: Search query (minimum 2 characters)
    - min_price: Minimum price in INR (optional, >= 0)
    - max_price: Maximum price in INR (optional, >= 0)
    - guests: Minimum guest capacity (optional, >= 1)
    - min_rating: Minimum rating filter 0-5 stars (optional)
    - property_types: Comma-separated property types (Villa,Apartment,Room,Resort)
    - amenities: Comma-separated amenities (Wi-Fi,Pool,Beach access,AC,Kitchen)
    
    If no filter parameters provided, all hotels matching the search query are returned.
    Filters are applied as: price >= min_price, price <= max_price, guests >= requested value, rating >= min_rating
    """
    if not q or len(q) < 2:
        return []
    
    # Parse property types from comma-separated string
    property_types_list = None
    if property_types:
        property_types_list = [pt.strip() for pt in property_types.split(',') if pt.strip()]
    
    # Parse amenities from comma-separated string
    amenities_list = None
    if amenities:
        amenities_list = [am.strip() for am in amenities.split(',') if am.strip()]
    
    # Use filtered search function
    hotels = HotelService.search_hotels_with_filters(
        db=db,
        query_text=q,
        min_price=min_price, 
        max_price=max_price,
        guests=guests,
        min_rating=min_rating,
        property_types=property_types_list,
        amenities=amenities_list
    )
    if not hotels:
        return []
    
    # Log search activity (authenticated or anonymous)
    log_user_activity(
        user_id=current_user_id,  # None for anonymous, user_id for authenticated
        action_type="search",
        activity_event={
            "query": q,
            "results_count": len(hotels)
        },
        db=db
    )
    
    return [_serialize_hotel_summary(hotel) for hotel in hotels]

@router.get("/{hotel_id}", response_model=HotelDetails)
async def get_hotel(
    hotel_id: int,
    current_user_id: Optional[int] = Depends(get_optional_user_id),
    db: Session = Depends(get_db)
):
    """Get hotel details by ID"""
    hotel = HotelService.get_hotel_by_id(db=db, hotel_id=hotel_id)
    
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    
    # Log hotel view activity (authenticated or anonymous)
    log_user_activity(
        user_id=current_user_id,  # None for anonymous, user_id for authenticated
        action_type="view",
        activity_event={
            "hotel_id": hotel_id,
            "hotel_name": hotel.name
        },
        db=db
    )

    return {
        "id": hotel.id,
        "name": hotel.name,
        "city": hotel.city,
        "description": hotel.description,
        "price": hotel.price,
        "room_type": hotel.room_type,
        "max_guests": hotel.guests if hotel.guests is not None else 2,
        "rating": hotel.rating,
        "amenities": _parse_amenities(hotel.amenities),
        "image": hotel.image_url,
        "latitude": hotel.latitude,
        "longitude": hotel.longitude,
        "reviews": generate_reviews(hotel),
    }

@router.post("/availability", response_model=AvailabilityResponse)
async def check_availability(payload: AvailabilityRequest, db: Session = Depends(get_db)):
    """Check hotel availability for a date range and guest count"""
    hotel = HotelService.get_hotel_by_id(db=db, hotel_id=payload.hotel_id)
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")

    if payload.number_of_guests < 1:
        return {"available": False, "message": "Guests must be at least 1."}

    if payload.check_out_date <= payload.check_in_date:
        return {"available": False, "message": "Checkout must be after check-in."}

    if payload.check_in_date < date.today():
        return {"available": False, "message": "Check-in date cannot be in the past."}

    max_guests = hotel.guests if hotel.guests is not None else 2
    if payload.number_of_guests > max_guests:
        return {"available": False, "message": "Selected guests exceed max capacity."}

    availability = BookingService.check_availability(
        db=db,
        hotel_id=payload.hotel_id,
        check_in_date=payload.check_in_date.isoformat(),
        check_out_date=payload.check_out_date.isoformat(),
        guest_count=payload.number_of_guests
    )
    if not availability["available"]:
        return {"available": False, "message": availability["message"]}

    return {"available": True, "message": "Hotel is available for your dates."}

@router.post("/bookings", response_model=BookingResponse)
async def create_booking_endpoint(
    payload: BookingRequest,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Create a booking and send confirmation email.
    
    SECURITY: User identity is derived from JWT token ONLY.
    Frontend sends only booking details (hotel_id, dates, guests).
    Backend extracts user_id from authenticated token.
    
    Authentication: Required (JWT token in Authorization header)
    """
    # Get user details from database using authenticated user_id
    user = AuthService.get_user_by_id(db=db, user_id=current_user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    user_email = user.email
    user_name = user_email.split('@')[0].title()  # Extract name from email
    
    hotel = HotelService.get_hotel_by_id(db=db, hotel_id=payload.hotel_id)
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")

    if payload.number_of_guests < 1:
        raise HTTPException(status_code=400, detail="Guests must be at least 1.")

    if payload.check_out_date <= payload.check_in_date:
        raise HTTPException(status_code=400, detail="Checkout must be after check-in.")

    if payload.check_in_date < date.today():
        raise HTTPException(status_code=400, detail="Check-in date cannot be in the past.")

    max_guests = hotel.guests if hotel.guests is not None else 2
    if payload.number_of_guests > max_guests:
        raise HTTPException(status_code=400, detail="Selected guests exceed max capacity.")

    # Create booking with user_id from JWT token (NOT from payload)
    booking_result = BookingService.create_booking(
        db=db,
        hotel_id=payload.hotel_id,
        user_id=current_user_id,
        check_in_date=payload.check_in_date.isoformat(),
        check_out_date=payload.check_out_date.isoformat(),
        guest_count=payload.number_of_guests
    )
    booking_id = booking_result["booking_id"]
    pricing = booking_result.get("pricing", {})
    num_nights = pricing.get("nights", (payload.check_out_date - payload.check_in_date).days)
    total_price = pricing.get("room_charges", 0)
    db_booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
    
    # Log booking activity
    print("BOOKING LOGGER CALLED - user_id:", current_user_id, "hotel:", hotel.name, "booking_id:", booking_id)
    log_result = log_user_activity(
        user_id=current_user_id,
        action_type="booking",
        activity_event={
            "message": f"Booked hotel {hotel.name} for {num_nights} nights",
            "hotel_id": payload.hotel_id,
            "hotel_name": hotel.name,
            "booking_id": booking_id,
            "check_in_date": payload.check_in_date.isoformat(),
            "check_out_date": payload.check_out_date.isoformat(),
            "num_nights": num_nights,
            "total_price": total_price
        },
        db=db
    )
    print("BOOKING LOGGER RESULT:", log_result)

    # DIAGNOSTIC TEST: Direct synchronous call (no threading)
    # This proves whether the email function works at all
    print("\n[DIAGNOSTIC] About to call email function DIRECTLY (no threading)")
    print(f"[DIAGNOSTIC] Booking ID: {booking_id}")
    print(f"[DIAGNOSTIC] User email: {user_email}")
    print(f"[DIAGNOSTIC] User name: {user_name}")
    print(f"[DIAGNOSTIC] Hotel name: {hotel.name}")
    
    try:
        email_result = send_booking_confirmation_email(
            user_email,  # From JWT authenticated user
            user_name,   # Derived from email
            hotel.name,
            payload.check_in_date.isoformat(),
            payload.check_out_date.isoformat()
        )
        print(f"[DIAGNOSTIC] Email function returned: {email_result}")
    except Exception as e:
        print(f"[DIAGNOSTIC] Email function raised exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    return {
        "booking_id": booking_id,
        "message": "Booking confirmed. Confirmation email sent."
    }


@router.get("/{hotel_id}/blocked-dates")
def get_blocked_dates(hotel_id: int, db: Session = Depends(get_db)):
    """
    Get all unavailable (blocked) date ranges for a hotel.
    
    Blocked dates are determined by confirmed bookings.
    Each booking blocks from check_in_date (inclusive) to check_out_date (exclusive).
    Overlapping and adjacent ranges are merged into single ranges.
    
    Args:
        hotel_id: The ID of the hotel
    
    Returns:
        {
            "hotel_id": int,
            "blocked_dates": [
                { "start": "2026-02-10", "end": "2026-02-12" },
                { "start": "2026-02-18", "end": "2026-02-20" }
            ]
        }
    
    Raises:
        404: If hotel does not exist
    """
    # Verify hotel exists
    hotel = HotelService.get_hotel_by_id(db=db, hotel_id=hotel_id)
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    
    # Fetch all confirmed bookings for this hotel
    bookings = db.query(Booking).filter(
        Booking.hotel_id == hotel_id,
        Booking.status == "confirmed"
    ).order_by(Booking.check_in_date.asc()).all()
    
    # If no bookings, return empty blocked_dates array
    if not bookings:
        return {
            "hotel_id": hotel_id,
            "blocked_dates": []
        }
    
    # Convert bookings to date range tuples (check_in, check_out)
    date_ranges = [
        (booking.check_in_date, booking.check_out_date)
        for booking in bookings
    ]
    
    # Merge overlapping and adjacent ranges
    merged_ranges = _merge_date_ranges(date_ranges)
    
    # Convert back to list of dicts with "start" and "end" keys
    blocked_dates = [
        {"start": start, "end": end}
        for start, end in merged_ranges
    ]
    
    return {
        "hotel_id": hotel_id,
        "blocked_dates": blocked_dates
    }

@router.get("/bookings/my", response_model=UserBookingListResponse)
def get_my_booking_history(
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get all bookings for the currently authenticated user.
    
    SECURITY: User identity is derived from JWT token ONLY.
    Frontend cannot manipulate or access other users' bookings.
    
    Returns booking history with calculated status (upcoming/completed/cancelled)
    and total price based on nightly rate and number of nights.
    
    Authentication: Required (JWT token in Authorization header)
    
    Returns:
        UserBookingListResponse with list of user's bookings
    """
    from datetime import datetime
    
    # Get bookings for the AUTHENTICATED user only
    # current_user_id comes from JWT token, not from frontend
    bookings = BookingService.get_user_booking_history(db=db, user_id=current_user_id)
    
    # Transform database records into UserBooking response format
    user_bookings = []
    today = datetime.now().date()
    
    for booking in bookings:
        # Parse dates
        check_in = datetime.strptime(booking.check_in_date, "%Y-%m-%d").date()
        check_out = datetime.strptime(booking.check_out_date, "%Y-%m-%d").date()
        
        # Calculate number of nights
        num_nights = (check_out - check_in).days
        
        # Calculate total price
        # Use booking price if stored, otherwise calculate from hotel nightly rate
        try:
            if booking.total_payable is not None:
                total_price = float(booking.total_payable)
            else:
                hotel_nightly_rate = float(booking.price or 0)
                total_price = hotel_nightly_rate * num_nights
        except (KeyError, TypeError):
            hotel_nightly_rate = float(booking.price or 0)
            total_price = hotel_nightly_rate * num_nights
        
        # Determine status
        # If booking has explicit status and it's cancelled, use that
        # Otherwise, determine based on check-in date
        if booking.status == "cancelled":
            status = "cancelled"
        elif check_in > today:
            status = "upcoming"
        else:
            status = "completed"

        hotel_name = "Unknown Hotel"
        if booking.hotel:
            hotel_name = booking.hotel.name
        else:
            hotel_obj = db.query(Hotel).filter(Hotel.id == booking.hotel_id).first()
            if hotel_obj:
                hotel_name = hotel_obj.name
        
        user_bookings.append(UserBooking(
            id=str(booking.booking_id),
            hotel_id=booking.hotel_id,
            hotel_name=hotel_name,
            check_in=booking.check_in_date,
            check_out=booking.check_out_date,
            guests=booking.guests,
            total_price=total_price,
            status=status
        ))
    
    return UserBookingListResponse(bookings=user_bookings)

@router.get("/users/{user_id}/bookings", response_model=UserBookingListResponse)
def get_user_booking_history(
    user_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get all bookings for a specific user with hotel details.
    
    Returns booking history with calculated status (upcoming/completed/cancelled)
    and total price based on nightly rate and number of nights.
    """
    from datetime import datetime, timedelta
    
    # Enforce account isolation (user_id must match authenticated user)
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Forbidden: user mismatch")

    # Get user bookings from database
    bookings = BookingService.get_user_booking_history(db=db, user_id=current_user_id)
    
    # Transform database records into UserBooking response format
    user_bookings = []
    today = datetime.now().date()
    
    for booking in bookings:
        # Parse dates
        check_in = datetime.strptime(booking.check_in_date, "%Y-%m-%d").date()
        check_out = datetime.strptime(booking.check_out_date, "%Y-%m-%d").date()
        
        # Calculate number of nights
        num_nights = (check_out - check_in).days
        
        # Calculate total price
        # Use booking price if stored, otherwise calculate from hotel nightly rate
        try:
            if booking.total_payable is not None:
                total_price = float(booking.total_payable)
            else:
                hotel_nightly_rate = float(booking.price or 0)
                total_price = hotel_nightly_rate * num_nights
        except (KeyError, TypeError):
            hotel_nightly_rate = float(booking.price or 0)
            total_price = hotel_nightly_rate * num_nights
        
        # Determine status
        # If booking has explicit status and it's cancelled, use that
        # Otherwise, determine based on check-in date
        if booking.status == "cancelled":
            status = "cancelled"
        elif check_in > today:
            status = "upcoming"
        else:
            status = "completed"

        hotel_name = "Unknown Hotel"
        if booking.hotel:
            hotel_name = booking.hotel.name
        else:
            hotel_obj = db.query(Hotel).filter(Hotel.id == booking.hotel_id).first()
            if hotel_obj:
                hotel_name = hotel_obj.name
        
        user_bookings.append(UserBooking(
            id=str(booking.booking_id),
            hotel_id=booking.hotel_id,
            hotel_name=hotel_name,
            check_in=booking.check_in_date,
            check_out=booking.check_out_date,
            guests=booking.guests,
            total_price=total_price,
            status=status
        ))
    
    return UserBookingListResponse(bookings=user_bookings)
