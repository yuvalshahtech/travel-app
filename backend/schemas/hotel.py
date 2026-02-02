from typing import List
from datetime import date
from pydantic import BaseModel, EmailStr

class HotelReview(BaseModel):
    user: str
    rating: float
    comment: str

class HotelDetails(BaseModel):
    id: int
    name: str
    city: str
    description: str | None = None
    price: float
    room_type: str
    max_guests: int
    rating: float
    amenities: List[str]
    image: str | None = None
    latitude: float
    longitude: float
    reviews: List[HotelReview]

class AvailabilityRequest(BaseModel):
    hotel_id: int
    check_in_date: date
    check_out_date: date
    number_of_guests: int

class AvailabilityResponse(BaseModel):
    available: bool
    message: str

class BookingRequest(BaseModel):
    hotel_id: int
    user_email: EmailStr
    user_name: str
    user_id: int | None = None  # Optional for backwards compatibility
    check_in_date: date
    check_out_date: date
    number_of_guests: int

class BookingResponse(BaseModel):
    booking_id: int
    message: str

class UserBooking(BaseModel):
    id: str  # booking_id as string
    hotel_id: int
    hotel_name: str
    check_in: str  # ISO date string
    check_out: str  # ISO date string
    guests: int
    total_price: float
    status: str  # "upcoming", "completed", "cancelled"

class UserBookingListResponse(BaseModel):
    bookings: List[UserBooking]
