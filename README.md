# Heavenly — Hotel Booking Platform

A full-stack hotel search and booking application with interactive map browsing, real-time filtering, JWT authentication, and OTP email verification.

**Live:** [heavenly-travel.netlify.app](https://heavenly-travel.netlify.app)

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11, FastAPI, Uvicorn |
| Database | PostgreSQL, SQLAlchemy 2.0, Alembic |
| Auth | JWT (python-jose), Argon2 (passlib) |
| Email | Brevo Transactional API |
| Frontend | Vanilla HTML/CSS/JS, Leaflet.js |

---

## Architecture

```
Frontend (Netlify)          Backend (Render)
     │                           │
     │  REST API                 │
     └──────────────────────────►│ FastAPI
                                 │   ├── routes/
                                 │   ├── services/
                                 │   └── middleware/
                                 │           │
                                 │           ▼
                                 │      PostgreSQL
                                 │           │
                                 └───────────┘
```

---

## Project Structure

```
travel-app/
├── backend/
│   ├── main.py              # FastAPI entrypoint
│   ├── requirements.txt     # Dependencies
│   ├── runtime.txt          # Python version
│   ├── load_hotels.py       # DB seeder
│   ├── alembic.ini          # Migrations config
│   ├── alembic/             # Migration scripts
│   ├── config/              # Settings, DB, logging
│   ├── models/              # SQLAlchemy ORM
│   ├── routes/              # API endpoints
│   ├── schemas/             # Pydantic models
│   ├── services/            # Business logic
│   ├── middleware/          # Rate limiting
│   ├── utils/               # JWT, email, OTP
│   └── tests/               # pytest suite
├── src/                     # Frontend HTML/JS
│   ├── home.html
│   ├── search.html
│   ├── hotel-details.html
│   ├── profile.html
│   ├── login.html
│   ├── signup.html
│   └── services/            # JS modules
└── .env                     # Environment vars
```

---

## Environment Variables

### Required

```env
DATABASE_URL=postgresql://user:pass@host:5432/dbname
JWT_SECRET_KEY=your-32-char-secret
BREVO_API_KEY=xkeysib-...
SENDER_EMAIL=noreply@domain.com
ENVIRONMENT=production
CORS_ORIGINS=https://your-frontend.com
```

### Optional

```env
SENDER_NAME=Heavenly
LOG_LEVEL=INFO
LOGIN_RATE_LIMIT=5/15minutes
SIGNUP_RATE_LIMIT=3/1hour
```

---

## Local Setup

```bash
# Clone and setup
git clone <repo>
cd travel-app

# Virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r backend/requirements.txt

# Create .env with required variables
# Run migrations
cd backend
alembic upgrade head

# Seed sample data (optional)
python load_hotels.py
```

---

## Running

### Backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

API: http://localhost:8000  
Docs: http://localhost:8000/docs (dev only)

### Frontend

```bash
cd src
python -m http.server 3000
```

App: http://localhost:3000

### Tests

```bash
pytest backend/tests/ -v
```

---

## API Overview

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/signup` | No | Register new user |
| POST | `/verify-otp` | No | Verify email OTP |
| POST | `/login` | No | Login, get JWT |
| GET | `/hotels/recent` | No | Recent hotels |
| GET | `/hotels/search` | No | Search with filters |
| GET | `/hotels/{id}` | No | Hotel details |
| POST | `/hotels/availability` | Yes | Check dates |
| POST | `/hotels/bookings` | Yes | Create booking |
| GET | `/hotels/bookings/my` | Yes | User's bookings |
| POST | `/activity/track` | No | Analytics event |

---

## Authentication Flow

1. **Signup** — User submits email + password
2. **OTP Sent** — 6-digit code sent via Brevo
3. **Verify** — User submits OTP within 5 minutes
4. **Account Created** — User record created, JWT returned
5. **Login** — Returns JWT on valid credentials

Passwords hashed with Argon2. JWT expires in 24 hours.

---

## Search & Filters

The `/hotels/search` endpoint supports:

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Search name, city, description |
| `min_price` | float | Minimum price |
| `max_price` | float | Maximum price |
| `min_rating` | float | Minimum rating |
| `guests` | int | Guest capacity |
| `property_types` | string | Comma-separated (Villa, Apartment, Room) |
| `amenities` | string | Comma-separated (Wi-Fi, Pool, AC) |

Property types use ILIKE partial matching for flexibility.

---

## Security

- Argon2 password hashing
- JWT with HS256, 24h expiry
- Per-IP and per-email rate limiting
- SQL injection prevention via ORM
- CORS restricted to configured origins
- Generic error responses (no stack traces)
- Swagger docs disabled in production

---

## Deployment

**Backend:** Deploy to Render/Railway with PostgreSQL. Set environment variables and run `alembic upgrade head`.

**Frontend:** Deploy `src/` folder to Netlify/Vercel as static site.

---

## Future Improvements

- [ ] Payment integration (Stripe/Razorpay)
- [ ] Redis-backed rate limiting
- [ ] Image upload with CDN
- [ ] Booking cancellation
- [ ] Email notifications
- [ ] Admin dashboard
- [ ] OAuth (Google, Facebook)

---

## License

Educational and personal use only.
