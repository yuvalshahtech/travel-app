# Travel App – Hotel Search & Discovery

A modern hotel search and booking platform with interactive map-based browsing, real-time filtering, and user authentication. Built with FastAPI backend and vanilla JavaScript frontend, featuring single high-quality images per hotel, intelligent review systems, and location-based discovery.

## Features

✨ **Core Features:**
- 🏨 **Single Image Per Hotel** – Clean, focused UI with one optimized image per property
- 🗺️ **Interactive Map Integration** – Leaflet.js powered map with custom pins and popups
- 🔍 **Advanced Search & Filters** – Price range, guest capacity, property types, and amenities
- ⭐ **Smart Review System** – Reviews automatically calibrated to match hotel ratings
- 🔐 **Secure Authentication** – Email/password signup with OTP verification
- 📍 **Location-Based Discovery** – City search with real-time results
- 💳 **Booking Interface** – Clean reservation UI with pricing details

## Project Structure

```
Travel-App/
├─ backend/
│  ├─ main.py              # FastAPI application entry point
│  ├─ requirements.txt     # Python dependencies
│  ├─ auth.db              # SQLite database (auto-generated)
│  ├─ models/              # Pydantic data models
│  ├─ routes/              # API routes (auth, hotels)
│  │  ├─ auth.py           # Authentication endpoints
│  │  └─ hotels.py         # Hotel search & details
│  ├─ schemas/             # Request/response schemas
│  │  └─ hotel.py          # Hotel & review schemas
│  ├─ utils/               # Utilities
│  │  ├─ auth.py           # JWT & password hashing
│  │  ├─ database.py       # SQLite operations
│  │  ├─ email.py          # Email service (Brevo)
│  │  └─ otp.py            # OTP generation/validation
│  ├─ load_hotels.py       # Database seeder script
│  ├─ clear_hotels.py      # Database cleanup utility
│  └─ uploads/
│     └─ hotels/           # Hotel images (single per hotel)
│
├─ src/
│  ├─ login.html           # User login page
│  ├─ signup.html          # User registration with OTP
│  ├─ home.html            # Featured hotels dashboard
│  ├─ search.html          # Hotel search with map & filters
│  ├─ hotel-details.html   # Detailed hotel view with reviews
│  ├─ dashboard.html       # User dashboard
│  └─ services/
│     └─ api.js            # API client (ES modules)
│
├─ .env                    # Environment configuration
├─ .gitignore              # Git ignore rules
└─ README.md               # This file
```

## Tech Stack

**Backend:**
- Python 3.10+
- FastAPI – Modern async web framework
- SQLite – Embedded database
- Pydantic – Data validation
- Uvicorn – ASGI server
- Passlib – Password hashing (bcrypt)
- Brevo API – Email service

**Frontend:**
- Vanilla HTML/CSS/JavaScript (ES6 modules)
- Leaflet.js 1.9.4 – Interactive maps
- No build tools required

## Installation

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Setup

1. **Clone the repository:**

```bash
git clone <repository-url>
cd Travel-App
```

2. **Install backend dependencies:**

```bash
cd backend
pip install -r requirements.txt
```

3. **Configure environment variables:**

Create `.env` in the project root:

```env
BREVO_API_KEY=xkeysib-your-api-key-here
SENDER_EMAIL=your-verified-sender@example.com
DEV_MODE=false
```

> **Note:** Get your Brevo API key from [Brevo Dashboard](https://app.brevo.com/) after creating a free account.

4. **Initialize database with sample data:**

```bash
cd backend
python load_hotels.py
```

This creates `auth.db` and seeds it with 15 sample hotels.

## Running the App

### Start Backend Server

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Backend API will be available at `http://localhost:8000`

### Start Frontend Server

**Option A: Python HTTP Server (Recommended)**

```bash
cd src
python -m http.server 3000
```

**Option B: Node.js http-server**

```bash
npm install -g http-server
cd src
http-server -p 3000
```

Open your browser and navigate to:
- **Home:** http://localhost:3000/home.html
- **Search:** http://localhost:3000/search.html
- **Login:** http://localhost:3000/login.html

## Usage

### Search & Filtering

The search page supports multiple simultaneous filters with AND logic:

- **City Search** – Type city name (e.g., "Mumbai", "Dubai")
- **Price Range** – Min/max price sliders
- **Guest Capacity** – Minimum guests filter
- **Property Types** – Entire place, private room, shared room
- **Amenities** – Wi-Fi, Pool, Beach access, AC, Kitchen
- **Star Rating** – Minimum rating filter (1-5 stars)

> Hotels must match **all** selected criteria to appear in results.

### Map Interaction

- **Browse Mode** – Red map pins when no filters active
- **Filter Mode** – Info-rich pins showing price, guests, amenities
- **Click Pin** – Opens popup with hotel card
- **View Hotel** – Click popup button to see full details

### Reviews System

Reviews are intelligently generated to match hotel ratings:
- Review ratings mathematically average to hotel's overall rating
- Maintains realistic variance within [1.0, 5.0] range
- Preserves floating-point precision (e.g., 4.2★, 3.8★)
- Filter reviews by star rating (1-5 stars)
- Displays maximum 3 reviews per filter

## Database Management

### Add New Hotels

Edit `backend/load_hotels.py` and run:

```bash
cd backend
python load_hotels.py
```

### Clear All Hotels

```bash
cd backend
python clear_hotels.py
```

### Database Schema

The app uses SQLite with the following key tables:
- `users` – User accounts and authentication
- `hotels` – Hotel listings with single image URL
- `otps` – Email verification codes

## API Endpoints

### Hotels

- `GET /hotels/search?q={city}` – Search hotels by city
- `GET /hotels/search?q={city}&min_price={X}&max_price={Y}&guests={Z}&min_rating={R}&property_types={A,B}&amenities={Wi-Fi,Pool}` – Advanced search with filters
- `GET /hotels/{id}` – Get hotel details with reviews
- `GET /hotels/recent` – Get recently added hotels

### Authentication

- `POST /auth/signup` – Create new user account
- `POST /auth/verify-otp` – Verify email OTP
- `POST /auth/login` – User login (returns JWT)

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is available for educational and personal use.
