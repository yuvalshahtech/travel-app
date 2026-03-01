# Heavenly — Hotel Search & Booking Platform

A production-ready hotel search and booking platform featuring interactive map-based browsing, real-time filtering, transparent pricing, JWT authentication, OTP verification, and comprehensive user activity analytics.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Features](#features)
- [Local Setup](#local-setup)
- [Running Tests](#running-tests)
- [Project Structure](#project-structure)
- [Security Features](#security-features)
- [API Endpoints](#api-endpoints)
- [Database Schema](#database-schema)
- [Known Limitations](#known-limitations)
- [Future Improvements](#future-improvements)

---

## Overview

Heavenly is a full-stack hotel booking application built with FastAPI and vanilla JavaScript. It provides a seamless booking experience with features like interactive map search, advanced filtering, transparent pricing breakdown, email verification, and real-time analytics tracking.

**Key Highlights:**
- RESTful API with FastAPI
- PostgreSQL database with SQLAlchemy ORM
- JWT-based authentication with OTP email verification
- Rate limiting and abuse protection
- Structured JSON logging
- Comprehensive test coverage (53 tests)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.10+, FastAPI 0.108, Uvicorn |
| **Database** | PostgreSQL 14+, SQLAlchemy 2.0, Alembic |
| **Authentication** | JWT (python-jose), Bcrypt (passlib) |
| **Email** | Brevo (Sendinblue) API |
| **Frontend** | Vanilla HTML/CSS/JS, Leaflet.js |
| **Testing** | pytest, pytest-asyncio, httpx |
| **Logging** | python-json-logger |

---

## Features

### Core Functionality
- ✅ **User Authentication** — Email/password signup with OTP verification
- ✅ **JWT Authorization** — Secure token-based authentication
- ✅ **Hotel Search** — Multi-field search with advanced filters
- ✅ **Interactive Map** — Leaflet.js powered map with custom markers
- ✅ **Transparent Pricing** — Complete breakdown (base + cleaning + fees + GST)
- ✅ **Booking Management** — Create, view history, track status
- ✅ **Activity Analytics** — Real-time user behavior tracking with priority-based buffering

### Security
- ✅ **Rate Limiting** — Sliding-window rate limiter with exponential backoff
- ✅ **Abuse Protection** — Per-IP and per-email rate limiting
- ✅ **Password Hashing** — Bcrypt with passlib
- ✅ **CORS Protection** — Configurable allowed origins
- ✅ **SQL Injection Prevention** — SQLAlchemy ORM parameterized queries

### Advanced Features
- ✅ **Analytics Buffer** — Asynchronous event batching with priority-based backpressure
- ✅ **Graceful Shutdown** — Flushes buffered events before exit
- ✅ **Structured Logging** — JSON logs with rotation
- ✅ **Database Migrations** — Alembic for schema versioning

---

## Local Setup

### Prerequisites

- **Python 3.10+** ([Download](https://www.python.org/downloads/))
- **PostgreSQL 14+** ([Download](https://www.postgresql.org/download/))
- **Git** ([Download](https://git-scm.com/downloads))

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd travel-app
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r backend/requirements.txt
```

### Step 4: Set Up PostgreSQL Database

```sql
-- Connect to PostgreSQL
psql -U postgres

-- Create database and user
CREATE DATABASE heavenly_db;
CREATE USER heavenly_admin WITH PASSWORD 'your_secure_password';
ALTER ROLE heavenly_admin SET client_encoding TO 'utf8';
ALTER ROLE heavenly_admin SET default_transaction_isolation TO 'read committed';
ALTER ROLE heavenly_admin SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE heavenly_db TO heavenly_admin;

-- Exit
\q
```

### Step 5: Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Database Configuration
DATABASE_URL=postgresql://heavenly_admin:your_secure_password@localhost:5432/heavenly_db

# JWT Secret (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
JWT_SECRET_KEY=your-32-character-secret-key-here

# Email Service (Brevo/Sendinblue)
BREVO_API_KEY=your-brevo-api-key
SENDER_EMAIL=noreply@yourdomain.com

# Application Settings
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
LOG_LEVEL=INFO

# Rate Limiting
LOGIN_RATE_LIMIT=5/15minutes
SIGNUP_RATE_LIMIT=3/1hour
ACTIVITY_RATE_LIMIT=60/1minute

# Analytics Configuration
ANALYTICS_BATCH_SIZE=100
ANALYTICS_FLUSH_INTERVAL=5.0
ANALYTICS_MAX_QUEUE_SIZE=5000
```

**Important:** 
- Generate a secure JWT secret key (minimum 32 characters)
- Get a free Brevo API key at [brevo.com](https://www.brevo.com)

### Step 6: Run Database Migrations

```bash
cd backend
alembic upgrade head
cd ..
```

### Step 7: Seed Hotel Data (Optional)

```bash
python -m backend.load_hotels
```

This will populate the database with 15 sample hotels across 7 Indian cities.

### Step 8: Start the Backend Server

```bash
# Development mode (with auto-reload)
uvicorn backend.main:app --reload --port 8000

# Production mode
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at: **http://localhost:8000**
API Documentation: **http://localhost:8000/docs** (development only)

### Step 9: Serve Frontend (Optional)

In a separate terminal:

```bash
cd src
python -m http.server 3000
```

Access the application at: **http://localhost:3000**

---

## Running Tests

The project includes comprehensive test coverage with 53 tests across analytics and rate limiting.

```bash
# Run all tests
pytest backend/tests/ -v

# Run with coverage
pytest backend/tests/ --cov=backend --cov-report=html

# Run specific test file
pytest backend/tests/test_analytics_buffer.py -v
pytest backend/tests/test_rate_limiting.py -v

# Quick test run
pytest backend/tests/ -q
```

**Expected Output:**
```
53 passed, 11 warnings in ~8 seconds
```

---

## Project Structure

```
travel-app/
├── backend/
│   ├── main.py                     # FastAPI application entry point
│   ├── requirements.txt            # Python dependencies
│   ├── load_hotels.py              # Database seeder (15 hotels)
│   ├── alembic.ini                 # Alembic migration config
│   │
│   ├── alembic/                    # Database migrations
│   │   ├── env.py                  # Migration environment
│   │   └── versions/               # Migration scripts
│   │       ├── de80a0d590de_*.py   # Initial schema
│   │       └── 0002_add_*.py       # Engagement tracking columns
│   │
│   ├── config/                     # Configuration
│   │   ├── settings.py             # Environment variables & app config
│   │   ├── database.py             # SQLAlchemy engine & sessions
│   │   └── logging_config.py       # JSON logging setup
│   │
│   ├── models/                     # SQLAlchemy ORM Models
│   │   └── models.py               # User, Hotel, Booking, UserActivity, EmailVerification
│   │
│   ├── routes/                     # API Endpoints
│   │   ├── auth.py                 # Signup, OTP verification, Login
│   │   ├── hotels.py               # Search, view, book, history
│   │   └── activity.py             # Analytics tracking
│   │
│   ├── schemas/                    # Pydantic Models
│   │   ├── __init__.py
│   │   ├── auth.py                 # Authentication request/response
│   │   ├── hotel.py                # Hotel & booking schemas
│   │   └── activity.py             # Activity tracking schemas
│   │
│   ├── services/                   # Business Logic
│   │   ├── __init__.py
│   │   ├── auth_service.py         # Authentication logic
│   │   ├── hotel_service.py        # Hotel search & filtering
│   │   ├── booking_service.py      # Booking management
│   │   ├── analytics_buffer.py     # Event buffering with priority queues
│   │   └── analytics_worker.py     # Background batch insertion
│   │
│   ├── middleware/                 # HTTP Middleware
│   │   ├── __init__.py
│   │   ├── rate_limiter.py         # Sliding-window rate limiter
│   │   ├── abuse_protection.py     # Rate limit dependencies
│   │   ├── request_logging.py      # HTTP request/response logging
│   │   └── activity_tracking.py    # Legacy activity tracker
│   │
│   ├── utils/                      # Utilities
│   │   ├── jwt_auth.py             # JWT creation, verification, dependencies
│   │   ├── auth.py                 # Password hashing (bcrypt)
│   │   ├── email.py                # Brevo integration
│   │   ├── otp.py                  # OTP generation & validation
│   │   └── activity_logger.py      # Activity logging helper
│   │
│   ├── tests/                      # Test Suite (53 tests)
│   │   ├── test_analytics_buffer.py    # 28 analytics tests
│   │   └── test_rate_limiting.py       # 25 rate limiting tests
│   │
│   ├── logs/                       # Application logs (auto-created)
│   └── uploads/                    # Static assets
│       └── hotels/                 # Hotel images
│
├── src/                            # Frontend
│   ├── home.html                   # Homepage with featured hotels
│   ├── search.html                 # Search with map & filters
│   ├── hotel-details.html          # Hotel details & booking
│   ├── profile.html                # User profile & booking history
│   ├── login.html                  # Login page
│   ├── signup.html                 # Signup with OTP verification
│   └── services/
│       ├── api.js                  # API client (ES6 modules)
│       └── tracker.js              # Analytics tracking
│
├── .env                            # Environment variables (create manually)
├── .gitignore                      # Git ignore patterns
└── README.md                       # This file
```

---

## Security Features

### Authentication & Authorization
- **JWT Tokens** — HS256 algorithm, 24-hour expiration
- **Password Hashing** — Bcrypt via passlib with automatic salt generation
- **OTP Verification** — Email-based 6-digit OTP with 5-minute expiration
- **Token Validation** — Middleware validates JWT on protected endpoints

### Rate Limiting
- **Sliding Window Algorithm** — Time-based request throttling
- **Per-IP & Per-Email Limits** — Dual-layer protection
- **Exponential Backoff** — Doubles wait time on repeated violations
- **Memory-Efficient** — LRU eviction after 10,000 tracked keys
- **Configurable Limits:**
  - Login: 5 requests per 15 minutes
  - Signup: 3 requests per hour
  - Activity: 60 requests per minute (per session)

### Data Protection
- **SQL Injection Prevention** — SQLAlchemy ORM with parameterized queries
- **CORS Protection** — Configurable allowed origins (no wildcards)
- **Error Masking** — Generic error messages (stack traces logged server-side only)
- **Constant-Time Login** — Minimum 200ms response to prevent timing attacks

### Best Practices
- **Environment Secrets** — Sensitive data in `.env` (not committed)
- **API Docs Disabled** — Swagger UI disabled in production
- **Database Pooling** — NullPool prevents connection exhaustion
- **Graceful Shutdown** — Flushes analytics buffer before exit

---

## API Endpoints

### Authentication

| Method | Endpoint | Auth Required | Description |
|--------|----------|---------------|-------------|
| POST | `/signup` | No | Register with email + password |
| POST | `/verify-otp` | No | Verify OTP sent to email |
| POST | `/login` | No | Login and receive JWT token |

### Hotels

| Method | Endpoint | Auth Required | Description |
|--------|----------|---------------|-------------|
| GET | `/hotels/recent` | No | Get 10 most recent hotels |
| GET | `/hotels/city/{city}` | No | Get hotels in a specific city |
| GET | `/hotels/search` | Optional | Search with filters (price, rating, guests, amenities) |
| GET | `/hotels/{id}` | Optional | Get hotel details with reviews |
| POST | `/hotels/availability` | Yes | Check room availability for dates |
| POST | `/hotels/bookings` | Yes | Create a new booking |
| GET | `/hotels/{id}/blocked-dates` | No | Get blocked dates for hotel |
| GET | `/hotels/bookings/my` | Yes | Get current user's bookings |

### Analytics

| Method | Endpoint | Auth Required | Description |
|--------|----------|---------------|-------------|
| POST | `/activity/track` | Optional | Track user activity events |
| GET | `/analytics/user/{id}` | Yes | Get user analytics summary |

**Example Request:**

```bash
# Login
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'

# Search hotels
curl http://localhost:8000/hotels/search?q=mumbai&min_price=2000&max_price=5000

# Create booking (with JWT)
curl -X POST http://localhost:8000/hotels/bookings \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "check_in_date": "2026-04-01",
    "check_out_date": "2026-04-05",
    "guests": 2
  }'
```

---

## Database Schema

### Tables

**users**
- `id` (PK), `email` (unique), `password_hash`, `created_at`, `updated_at`, `last_login`, `login_count`
- Indexes: `email`, `created_at`

**hotels**
- `id` (PK), `name`, `city`, `country`, `latitude`, `longitude`, `price`, `room_type`, `rating`, `guests`, `description`, `image_url`, `amenities` (JSON), `created_at`
- Indexes: `city`, `price`, `rating`, `created_at`, composite (`latitude`, `longitude`)

**bookings**
- `booking_id` (PK), `hotel_id` (FK), `user_id` (FK), `check_in_date`, `check_out_date`, `guests`, `price`, `total_price`, `total_payable`, `price_snapshot` (JSON), `status`, `created_at`, `updated_at`
- Foreign keys with CASCADE delete

**user_activity**
- `id` (PK), `user_id` (FK, nullable), `action_type`, `activity_event` (JSON), `session_id`, `page`, `hotel_id`, `event_type`, `duration_seconds`, `event_metadata` (JSONB), `timestamp`
- Indexes: `user_id`, `action_type`, `timestamp`, `event_type`, `session_id`, composite (`session_id`, `event_type`)

**email_verifications**
- `id` (PK), `email` (unique), `password_hash`, `otp`, `expires_at`, `created_at`
- Temporary storage for OTP verification flow

### Relationships
- `User` → `Booking` (one-to-many)
- `Hotel` → `Booking` (one-to-many)
- `User` → `UserActivity` (one-to-many, nullable for anonymous)

---

## Known Limitations

### Current Constraints
1. **Mock Hotel Data** — Uses 15 seeded hotels (not real inventory)
2. **No Payment Integration** — Bookings are created without actual payment processing
3. **In-Memory Rate Limiting** — Rate limit counters reset on server restart
4. **Single Server Deployment** — Not designed for multi-instance horizontal scaling
5. **Email Service Dependency** — Requires active Brevo API key for OTP delivery
6. **No Image Upload** — Hotel images are static files (no user upload functionality)

### Temporary Workarounds
- **Development Mode** — Set `ENVIRONMENT=development` to enable Swagger UI
- **Missing Email** — Users won't receive OTP without valid Brevo API key
- **Rate Limit Testing** — Use different IPs or wait for window expiration

---

## Future Improvements

### High Priority
- [ ] **Payment Integration** — Add Stripe/PayPal for real transactions
- [ ] **Redis Rate Limiting** — Persistent, scalable rate limiting across instances
- [ ] **Image Upload** — User-uploaded hotel images with S3/CloudFront CDN
- [ ] **Booking Cancellation** — Allow users to cancel with refund logic
- [ ] **Email Notifications** — Booking confirmations, reminders, cancellation emails
- [ ] **Advanced Search** — Geolocation-based radius search, map bounds filtering

### Medium Priority
- [ ] **Admin Dashboard** — Hotel management, user management, analytics
- [ ] **Review System** — Real user reviews and ratings
- [ ] **Pagination** — Cursor-based pagination for large result sets
- [ ] **Caching** — Redis cache for frequently accessed hotels
- [ ] **WebSocket Support** — Real-time availability updates
- [ ] **Multi-Currency Support** — Dynamic pricing in multiple currencies

### Nice to Have
- [ ] **OAuth Integration** — Google, Facebook login
- [ ] **Mobile App** — React Native or Flutter
- [ ] **Push Notifications** — Firebase Cloud Messaging
- [ ] **Multi-Language Support** — i18n for frontend
- [ ] **Dark Mode** — Theme toggle
- [ ] **Accessibility** — WCAG 2.1 compliance

---

## License

This project is for educational and personal use only.

---

## Support

For issues or questions:
- Check logs: `backend/logs/app.log`
- Run tests: `pytest backend/tests/ -v`
- Review API docs: `http://localhost:8000/docs` (development mode)

**Last Updated:** March 2026
│   │   └── booking_service.py  # Booking with transactions
│   ├── middleware/
│   │   ├── request_logging.py  # HTTP request/response logging
│   │   └── activity_tracking.py# User behavior tracking
│   ├── utils/
│   │   ├── jwt_auth.py         # JWT create, verify, dependencies
│   │   ├── activity_logger.py  # Activity insert to user_activity
│   │   ├── email.py            # Brevo email integration
│   │   └── otp.py              # OTP generation & validation
│   └── uploads/
│       ├── hotels/             # Hotel images
│       └── logo/               # App logo
├── src/
│   ├── home.html               # Homepage with featured hotels
│   ├── search.html             # Search with map & filters
│   ├── hotel-details.html      # Hotel detail + booking
│   ├── profile.html            # User profile & booking history
│   ├── login.html              # Login page
│   ├── signup.html             # Signup with OTP verification
│   └── services/
│       └── api.js              # Frontend API client (ES modules)
├── .env                        # Environment variables (not committed)
├── .gitignore
└── README.md
```

---

## Production Setup

### 1. Prerequisites

- Python 3.10+
- PostgreSQL 14+
- A Brevo (Sendinblue) account for transactional emails

### 2. Create PostgreSQL Database

```sql
-- Connect: psql -U postgres
CREATE DATABASE heavenly_db;
CREATE USER heavenly_admin WITH PASSWORD 'your_secure_password';
ALTER ROLE heavenly_admin SET client_encoding TO 'utf8';
ALTER ROLE heavenly_admin SET default_transaction_isolation TO 'read committed';
ALTER ROLE heavenly_admin SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE heavenly_db TO heavenly_admin;
```

### 3. Configure Environment

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql://heavenly_admin:your_secure_password@localhost:5432/heavenly_db

# JWT — generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_SECRET_KEY=<strong-random-key-min-32-chars>

# Email (Brevo)
BREVO_API_KEY=xkeysib-...
SENDER_EMAIL=noreply@yourdomain.com

# App
ENVIRONMENT=production
CORS_ORIGINS=https://yourdomain.com
LOG_LEVEL=INFO
```

### 4. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 5. Run Migrations

```bash
cd backend
alembic upgrade head
```

### 6. Seed Hotel Data

```bash
python -m backend.load_hotels
```

### 7. Start the Backend

```bash
# Development
uvicorn backend.main:app --reload --port 8000

# Production
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 8. Serve Frontend

Serve the `src/` directory with any static file server on port 3000:

```bash
cd src
python -m http.server 3000
```

---

## Security Configuration

| Area | Requirement |
|------|------------|
| JWT Secret | Minimum 32 characters, loaded from `JWT_SECRET_KEY` env var. App refuses to start without it. |
| JWT Expiration | 24 hours (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`) |
| JWT Algorithm | HS256, explicitly defined |
| CORS | Restricted to configured origins via `CORS_ORIGINS` env var. No wildcards. |
| Passwords | Hashed with bcrypt via passlib |
| API Docs | Disabled when `ENVIRONMENT=production` |
| Exceptions | Global handler returns generic error — no stack traces exposed |
| Optional Auth | `get_optional_user_id` returns `None` for anonymous — never bypasses protected routes |
| HTTPS | Required in production (configure at reverse proxy level) |
| Rate Limiting | Recommended — add via middleware or reverse proxy |

---

## Database

### Tables

| Table | Purpose |
|-------|---------|
| `users` | User accounts (email, password_hash, last_login, login_count) |
| `hotels` | Hotel catalog (name, city, country, price, room_type, rating, amenities JSON) |
| `bookings` | Reservations (hotel_id, user_id, dates, pricing snapshot, status) |
| `user_activity` | Analytics (user_id nullable, action_type, activity_event JSON, auto timestamp) |
| `email_verifications` | Temporary OTP storage for signup flow |

### User Activity Tracking

All search, view, and booking events are logged to `user_activity`:

```sql
SELECT id, user_id, action_type, activity_event, timestamp
FROM user_activity ORDER BY timestamp DESC;
```

- **Authenticated requests**: `user_id` populated from JWT
- **Anonymous requests**: `user_id = NULL`
- **Timestamp**: Auto-generated via `server_default=func.now()`

### Backups

```bash
# Manual dump
pg_dump -U heavenly_admin heavenly_db > backup_$(date +%Y%m%d).sql

# Cron job (daily at 2 AM)
0 2 * * * pg_dump -U heavenly_admin heavenly_db | gzip > /backups/heavenly_$(date +\%Y\%m\%d).sql.gz
```

---

## Logging & Monitoring

Structured JSON logs are written to `backend/logs/app.log` with rotation (10 MB, 5 backups).

```bash
# Follow live logs
tail -f backend/logs/app.log | jq '.'

# Filter errors
tail -f backend/logs/app.log | jq 'select(.level == "ERROR")'

# Windows PowerShell
Get-Content backend/logs/app.log -Wait
```

Error handling: all unhandled exceptions return 500 with generic message. Full traces are logged server-side only. Activity logging failures are non-blocking.

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/signup` | No | Register with email + password |
| POST | `/verify-otp` | No | Verify OTP from email |
| POST | `/login` | No | Authenticate, returns JWT |
| GET | `/hotels/recent` | No | Featured hotels for homepage |
| GET | `/hotels/city/{city}` | No | Hotels by city |
| GET | `/hotels/search?q=...` | Optional | Search with filters (price, rating, guests, amenities, property types) |
| GET | `/hotels/{id}` | Optional | Hotel detail view |
| POST | `/hotels/availability` | Yes | Check date availability |
| POST | `/hotels/bookings` | Yes | Create booking |
| GET | `/hotels/bookings/my` | Yes | Current user's booking history |
| GET | `/hotels/users/{id}/bookings` | Yes | User bookings (account-isolated) |

---

## License

This project is available for educational and personal use.
