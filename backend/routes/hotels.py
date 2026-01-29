from fastapi import APIRouter, HTTPException, Query
from backend.utils.database import (
    get_hotel_by_id,
    get_recent_hotels,
    get_hotels_by_city,
    search_hotels,
    search_hotels_with_filters
)

router = APIRouter(prefix="/hotels", tags=["hotels"])

@router.get("/recent")
async def get_recent():
    """Get recently listed hotels"""
    import json
    hotels = get_recent_hotels(limit=10)
    if not hotels:
        return []
    
    return [
        {
            "id": hotel["id"],
            "name": hotel["name"],
            "city": hotel["city"],
            "country": hotel["country"],
            "latitude": hotel["latitude"],
            "longitude": hotel["longitude"],
            "price": hotel["price"],
            "room_type": hotel["room_type"],
            "rating": hotel["rating"],
            "guests": hotel["guests"] if hotel["guests"] is not None else 2,
            "image_url": hotel["image_url"],
            "amenities": json.loads(hotel["amenities"]) if hotel["amenities"] else [],
        }
        for hotel in hotels
    ]

@router.get("/city/{city}")
async def get_by_city(city: str):
    """Get hotels in a specific city"""
    import json
    hotels = get_hotels_by_city(city, limit=50)
    if not hotels:
        return []
    
    return [
        {
            "id": hotel["id"],
            "name": hotel["name"],
            "city": hotel["city"],
            "country": hotel["country"],
            "latitude": hotel["latitude"],
            "longitude": hotel["longitude"],
            "price": hotel["price"],
            "room_type": hotel["room_type"],
            "rating": hotel["rating"],
            "guests": hotel["guests"] if hotel["guests"] is not None else 2,
            "image_url": hotel["image_url"],
            "amenities": json.loads(hotel["amenities"]) if hotel["amenities"] else [],
        }
        for hotel in hotels
    ]

@router.get("/search")
async def search(
    q: str = "", 
    min_price: float = Query(None, ge=0), 
    max_price: float = Query(None, ge=0),
    guests: int = Query(None, ge=1),
    min_rating: float = Query(None, ge=0, le=5),
    property_types: str = Query(None),
    amenities: str = Query(None)
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
    import json
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
    hotels = search_hotels_with_filters(
        q, 
        limit=50, 
        min_price=min_price, 
        max_price=max_price,
        guests=guests,
        min_rating=min_rating,
        property_types=property_types_list,
        amenities=amenities_list
    )
    if not hotels:
        return []
    
    return [
        {
            "id": hotel["id"],
            "name": hotel["name"],
            "city": hotel["city"],
            "country": hotel["country"],
            "latitude": hotel["latitude"],
            "longitude": hotel["longitude"],
            "price": hotel["price"],
            "room_type": hotel["room_type"],
            "rating": hotel["rating"],
            "guests": hotel["guests"] if hotel["guests"] is not None else 2,
            "image_url": hotel["image_url"],
            "amenities": json.loads(hotel["amenities"]) if hotel["amenities"] else [],
        }
        for hotel in hotels
    ]

@router.get("/{hotel_id}")
async def get_hotel(hotel_id: int):
    """Get hotel details by ID"""
    import json
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
        "amenities": json.loads(hotel["amenities"]) if hotel["amenities"] else [],
    }
