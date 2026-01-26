from fastapi import APIRouter, HTTPException
from backend.utils.database import (
    get_hotel_by_id,
    get_recent_hotels,
    get_hotels_by_city,
    search_hotels
)

router = APIRouter(prefix="/hotels", tags=["hotels"])

@router.get("/recent")
async def get_recent():
    """Get recently listed hotels"""
    hotels = get_recent_hotels(limit=10)
    if not hotels:
        return []
    
    return [
        {
            "id": h["id"],
            "name": h["name"],
            "city": h["city"],
            "country": h["country"],
            "latitude": h["latitude"],
            "longitude": h["longitude"],
            "price": h["price"],
            "room_type": h["room_type"],
            "rating": h["rating"],
            "image_url": h["image_url"],
        }
        for h in hotels
    ]

@router.get("/city/{city}")
async def get_by_city(city: str):
    """Get hotels in a specific city"""
    hotels = get_hotels_by_city(city, limit=50)
    if not hotels:
        return []
    
    return [
        {
            "id": h["id"],
            "name": h["name"],
            "city": h["city"],
            "country": h["country"],
            "latitude": h["latitude"],
            "longitude": h["longitude"],
            "price": h["price"],
            "room_type": h["room_type"],
            "rating": h["rating"],
            "image_url": h["image_url"],
        }
        for h in hotels
    ]

@router.get("/search")
async def search(q: str = ""):
    """Search hotels by name, city, or country"""
    if not q or len(q) < 2:
        return []
    
    hotels = search_hotels(q, limit=50)
    if not hotels:
        return []
    
    return [
        {
            "id": h["id"],
            "name": h["name"],
            "city": h["city"],
            "country": h["country"],
            "latitude": h["latitude"],
            "longitude": h["longitude"],
            "price": h["price"],
            "room_type": h["room_type"],
            "rating": h["rating"],
            "image_url": h["image_url"],
        }
        for h in hotels
    ]

@router.get("/{hotel_id}")
async def get_hotel(hotel_id: int):
    """Get hotel details by ID"""
    hotel = get_hotel_by_id(hotel_id)
    
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    
    return {
        "id": hotel["id"],
        "name": hotel["name"],
        "city": hotel["city"],
        "country": hotel["country"],
        "latitude": hotel["latitude"],
        "longitude": hotel["longitude"],
        "price": hotel["price"],
        "room_type": hotel["room_type"],
        "rating": hotel["rating"],
        "description": hotel["description"],
        "image_url": hotel["image_url"],
    }
