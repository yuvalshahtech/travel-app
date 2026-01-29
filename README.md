# Travel App – Hotel Booking & Analytics

A hotel search and discovery app with map-based browsing, multi-filter search, and basic authentication. Built with a FastAPI backend and a vanilla HTML/JS frontend to demonstrate hotel discovery, filtering, and location-based UX.

## Project Structure

```
Travel-App/
├─ backend/
│  ├─ main.py              # FastAPI app
│  ├─ requirements.txt     # Python dependencies
│  ├─ models/              # Pydantic models
│  ├─ routes/              # API routes (auth, hotels)
│  ├─ schemas/             # Request/response schemas
│  ├─ utils/               # Auth, database, email utilities
│  ├─ load_hotels.py       # Sample data seeder
│  └─ uploads/             # Hotel images used by sample data
│
├─ src/
│  ├─ login.html           # Email/password login page
│  ├─ signup.html          # User registration page
│  ├─ home.html            # Featured hotels grid (dashboard)
│  ├─ search.html          # Hotel search with map and filters
│  ├─ hotel-details.html   # Individual hotel details page
│  ├─ dashboard.html       # Post-login welcome page
│  └─ services/
│     └─ api.js            # API fetch wrapper (ES module)
│
├─ .env                    # Environment variables (email service config)
└─ README.md
```

## Tech Stack

- **Backend:** Python, FastAPI, SQLite, Uvicorn
- **Frontend:** Vanilla HTML/CSS/JavaScript
- **Maps:** Leaflet.js
- **Icons:** Lucide (CDN)

## Installation

### Backend (Python)

```bash
cd backend
pip install -r requirements.txt
```

Create `.env` in project root:

```
BREVO_API_KEY=xkeysib-your-api-key
SENDER_EMAIL=your-verified-sender@example.com
DEV_MODE=false
```

### Frontend (Node/JS – optional)

You can run the frontend with Python’s built-in server or a Node static server.

**Option A: Python server**

```bash
cd src
python -m http.server 3000
```

**Option B: Node static server**

```bash
npm install -g http-server
cd src
http-server -p 3000
```

## Run Locally

1. Initialize the database (auto-creates tables):

```bash
cd backend
python load_hotels.py
```

2. Start backend API:

```bash
cd backend
uvicorn main:app --reload --port 8000
```

3. Start frontend (choose one):

```bash
cd src
python -m http.server 3000
```

Open http://localhost:3000 and start from `home.html`.

## Usage

### Filters

On the search page, filters apply instantly and use AND logic:

- **Price** (min/max)
- **Guests** (minimum capacity)
- **Property Type** (room_type)
- **Amenities** (Wi-Fi, Pool, Beach access, AC, Kitchen)

Selecting multiple amenities requires each hotel to include **all** selected amenities.

### Map Pins

- **No filters active:** branded browse pin
- **Filters active:** pin shows summary info (price/guests/property + amenities badge)
- **Hover/Active states:** maintain brand color, scale, and shadow
- **Zero results:** pins disappear and count shows 0

## Database Seeding

Run `backend/load_hotels.py` to create and seed the SQLite database (`backend/auth.db`) with sample hotels and amenities.

## API Overview

- `GET /hotels/search?q=city` – search hotels
- `GET /hotels/search?q=city&min_price=X&max_price=Y&guests=Z&min_rating=R&property_types=A,B&amenities=Wi-Fi,Pool` – search with filters
- `GET /hotels/{id}` – hotel details

All responses return `amenities` as an array for UI rendering.

## Screenshot

_Add screenshots of the search page, filters, and map pins here._

## License

_Add license information here._
