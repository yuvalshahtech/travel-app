from typing import List
from pydantic import BaseModel

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
