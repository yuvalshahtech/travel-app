"""
Data loader script: Populate SQLite with Airbnb-style hotel data
Run once after creating the database schema
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.database import create_hotel, init_database, get_db_connection
import sqlite3

def load_sample_data():
    """Load realistic Airbnb-style hotel data"""
    
    # Sample hotels with realistic prices, locations, and ratings
    hotels = [
        # Mumbai (Accurate real-world coordinates)
        {
            "name": "Luxury Beachfront Villa Mumbai",
            "city": "Mumbai",
            "country": "India",
            "latitude": 19.0612,
            "longitude": 72.8283,
            "price": 7000,
            "room_type": "Entire villa",
            "rating": 4.92,
            "description": "Stunning beachfront villa with private pool and ocean views. Located in Bandra, walking distance to restaurants and nightlife.",
            "image_url": "/uploads/hotels/hotel1.jpg"
        },
        {
            "name": "Modern 2BHK Apartment Downtown",
            "city": "Mumbai",
            "country": "India",
            "latitude": 19.0760,
            "longitude": 72.8777,
            "price": 4800,
            "room_type": "Entire apartment",
            "rating": 4.75,
            "description": "Spacious 2-bedroom apartment in heart of Mumbai. Close to metro, restaurants, and shopping malls. Perfect for families.",
            "image_url": "/uploads/hotels/hotel2.jpg"
        },
        {
            "name": "Cozy Studio in Bandra",
            "city": "Mumbai",
            "country": "India",
            "latitude": 19.0525,
            "longitude": 72.8285,
            "price": 3700,
            "room_type": "Studio",
            "rating": 4.68,
            "description": "Charming studio apartment with modern amenities. Walking distance to cafes, shops, and parks. Great location!",
            "image_url": "/uploads/hotels/hotel3.jpg"
        },
        {
            "name": "Heritage Havelit Room",
            "city": "Mumbai",
            "country": "India",
            "latitude": 18.9676,
            "longitude": 72.8227,
            "price": 3000,
            "room_type": "Private room",
            "rating": 4.60,
            "description": "Traditional heritage room in restored haveli. Experience authentic Mumbai with modern comfort.",
            "image_url": "/uploads/hotels/hotel4.jpg"
        },
        # Goa (Accurate real-world beach coordinates)
        {
            "name": "Beachfront Shack Goa",
            "city": "Goa",
            "country": "India",
            "latitude": 15.481617122777424,
            "longitude": 73.80829441183535,
            "price": 4200,
            "room_type": "Entire cottage",
            "rating": 4.84,
            "description": "Charming beachfront cottage steps away from Anjuna Beach. Perfect for relaxation with sea breeze and sunset views.",
            "image_url": "/uploads/hotels/hotel5.jpg"
        },
        {
            "name": "Luxury Resort Room Goa",
            "city": "Goa",
            "country": "India",
            "latitude": 15.369817998999148,
            "longitude": 73.8616882318267,
            "price": 7200,
            "room_type": "Entire villa",
            "rating": 4.89,
            "description": "5-star resort experience with pool, spa, and restaurant. Private beach access. Pure luxury!",
            "image_url": "/uploads/hotels/hotel6.jpg"
        },
        {
            "name": "Backpacker Hostel Goa",
            "city": "Goa",
            "country": "India",
            "latitude": 15.5580,
            "longitude": 73.8036,
            "price": 2300,
            "room_type": "Shared dorm",
            "rating": 4.45,
            "description": "Social hostel perfect for backpackers. Meet travelers, explore Goa together. Kitchen and lounge available.",
            "image_url": "/uploads/hotels/hotel7.jpg"
        },
        # Delhi (Accurate real-world coordinates)
        {
            "name": "Old Delhi Heritage Home",
            "city": "Delhi",
            "country": "India",
            "latitude": 28.6505,
            "longitude": 77.2303,
            "price": 3200,
            "room_type": "Private room",
            "rating": 4.71,
            "description": "Authentic stay in historic Old Delhi. Experience traditional hospitality with modern comfort. Walking tours available.",
            "image_url": "/uploads/hotels/hotel8.jpg"
        },
        {
            "name": "Modern Farmhouse Delhi",
            "city": "Delhi",
            "country": "India",
            "latitude": 28.4595,
            "longitude": 77.0099,
            "price": 6500,
            "room_type": "Entire villa",
            "rating": 4.80,
            "description": "Spacious farmhouse on the outskirts. Peaceful location with gardens, perfect for families and groups.",
            "image_url": "/uploads/hotels/hotel9.jpg"
        },
        {
            "name": "Business Hotel Central Delhi",
            "city": "Delhi",
            "country": "India",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "price": 4600,
            "room_type": "Entire apartment",
            "rating": 4.65,
            "description": "Convenient 1-bedroom apartment in central location. Perfect for business travelers. WiFi, AC, and kitchen included.",
            "image_url": "/uploads/hotels/hotel10.jpg"
        },
        # Bangalore (Accurate real-world coordinates)
        {
            "name": "Tech Hub Apartment Bangalore",
            "city": "Bangalore",
            "country": "India",
            "latitude": 12.9352,
            "longitude": 77.6245,
            "price": 4200,
            "room_type": "Entire apartment",
            "rating": 4.73,
            "description": "Modern apartment in IT Hub. Close to tech parks, malls, and nightlife. Fully furnished and equipped.",
            "image_url": "/uploads/hotels/hotel11.jpg"
        },
        {
            "name": "Garden Villa Bangalore",
            "city": "Bangalore",
            "country": "India",
            "latitude": 13.0845,
            "longitude": 77.5941,
            "price": 5900,
            "room_type": "Entire villa",
            "rating": 4.88,
            "description": "Spacious villa with garden, perfect for nature lovers. Quiet neighborhood with modern amenities.",
            "image_url": "/uploads/hotels/hotel12.jpg"
        },
        # Kolkata (Accurate real-world coordinates)
        {
            "name": "Heritage Mansion Kolkata",
            "city": "Kolkata",
            "country": "India",
            "latitude": 22.5726,
            "longitude": 88.3639,
            "price": 3300,
            "room_type": "Private room",
            "rating": 4.76,
            "description": "Historic colonial mansion with period furnishings. Experience old-world charm and hospitality. Literary hub!",
            "image_url": "/uploads/hotels/hotel13.jpg"
        },
        # Jaipur (Accurate real-world coordinates near City Palace)
        {
            "name": "Palace View Room Jaipur",
            "city": "Jaipur",
            "country": "India",
            "latitude": 26.9249,
            "longitude": 75.8243,
            "price": 5000,
            "room_type": "Entire apartment",
            "rating": 4.81,
            "description": "Room with views of City Palace. Walking distance to bazaars and main attractions. Royal experience!",
            "image_url": "/uploads/hotels/hotel14.jpg"
        },
        # Udaipur (Accurate real-world lakeside coordinates)
        {
            "name": "Lakeside Villa Udaipur",
            "city": "Udaipur",
            "country": "India",
            "latitude": 24.5854,
            "longitude": 73.6869,
            "price": 7400,
            "room_type": "Entire villa",
            "rating": 4.93,
            "description": "Stunning lakeside villa with boat access. Romantic getaway with sunset views over Lake Pichola.",
            "image_url": "/uploads/hotels/hotel15.jpg"
        },
    ]
    
    # Prefer uploaded images if available: assign sequential uploaded images
    # This ensures each hotel uses a unique local image uploaded to backend/uploads/hotels
    for idx, h in enumerate(hotels, start=1):
        h['image_url'] = f"/uploads/hotels/hotel{idx}.jpg"
    
    # Check if data already exists to avoid duplicates
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM hotels")
    count = cursor.fetchone()[0]
    conn.close()
    
    if count > 0:
        print(f"Database already contains {count} hotels. Skipping data load.")
        return
    
    # Insert hotels
    for hotel in hotels:
        create_hotel(
            name=hotel["name"],
            city=hotel["city"],
            country=hotel["country"],
            latitude=hotel["latitude"],
            longitude=hotel["longitude"],
            price=hotel["price"],
            room_type=hotel["room_type"],
            rating=hotel["rating"],
            description=hotel["description"],
            image_url=hotel["image_url"]
        )
    
    print(f"✓ Successfully loaded {len(hotels)} hotels into database")

if __name__ == "__main__":
    init_database()
    load_sample_data()
