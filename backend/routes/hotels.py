from fastapi import APIRouter, HTTPException, Query
from pathlib import Path
import random
from backend.schemas.hotel import HotelDetails
from backend.utils.database import (
    get_hotel_by_id,
    get_recent_hotels,
    get_hotels_by_city,
    search_hotels,
    search_hotels_with_filters
)

router = APIRouter(prefix="/hotels", tags=["hotels"])

UPLOADS_DIR = Path(__file__).resolve().parents[1] / "uploads" / "hotels"

def generate_reviews(hotel):
    amenities = []
    if hotel["amenities"]:
        try:
            import json
            amenities = json.loads(hotel["amenities"])
        except Exception:
            amenities = []

    rating = float(hotel["rating"] or 4.2)
    price = float(hotel["price"] or 0)
    room_type = (hotel["room_type"] or "").lower()
    city = hotel["city"] or ""
    description = (hotel["description"] or "").lower()

    rng = random.Random(int(hotel["id"]))

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
        name = name_pool[(int(hotel["id"]) + idx * 3) % len(name_pool)]
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

@router.get("/{hotel_id}", response_model=HotelDetails)
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
        "description": hotel["description"],
        "price": hotel["price"],
        "room_type": hotel["room_type"],
        "max_guests": hotel["guests"] if hotel["guests"] is not None else 2,
        "rating": hotel["rating"],
        "amenities": json.loads(hotel["amenities"]) if hotel["amenities"] else [],
        "image": hotel["image_url"],
        "latitude": hotel["latitude"],
        "longitude": hotel["longitude"],
        "reviews": generate_reviews(hotel),
    }
