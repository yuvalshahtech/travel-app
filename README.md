# Heavenly – Hotel Booking Web Application

Heavenly is a modern hotel booking web application that lets users search and discover hotels, then book stays directly from hotel detail pages. The app features an availability calendar with real-time blocking, user authentication, booking history, and email confirmations.

## Booking Flow

The booking experience is streamlined and focused:
1. **Browse Hotels**: Users explore hotels on the home page or via search/filters
2. **View Details**: Clicking a hotel card navigates to the hotel detail page
3. **Book**: Booking is **only available on the hotel detail page** with the availability calendar
4. **Confirmation**: Users receive an email and can view booking in their profile

Listing pages (home and search) contain only read-only hotel cards—no booking buttons. This keeps the UX clean and guides users to the full detail experience before booking.

## Key Features
- Hotel search with advanced filtering (price, rating, property type, amenities)
- Interactive map with custom location markers
- Hotel detail pages with real-time availability calendar
- Blocked date visualization for booked dates
- Single booking entry point (hotel-details page)
- User authentication with email verification
- Booking history in user profile
- Email confirmations for successful bookings
- Global "Become a Host" CTA (header button, non-intrusive)
- Responsive design optimized for mobile and desktop

## Tech Stack
- Frontend: HTML, CSS, Vanilla JavaScript
- Backend: Python + FastAPI
- Database: SQLite

## Project Structure
```
travel-app/
├── backend/            # FastAPI app, routes, schemas, utils, database scripts
├── src/                # Frontend pages and JS API client
├── .gitignore          # Git ignore rules
├── .env                # Local environment variables (not committed)
└── README.md           # Project documentation
```

## Environment Setup

Before running the application, you need to configure environment variables in a `.env` file in the project root. This file contains sensitive credentials and **should never be committed to git**.

### Generating the JWT Secret

The JWT secret is a base64-encoded cryptographically secure string used to sign authentication tokens (HS256 algorithm). Generate it using Python:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

This will output a 44-character string like: `AbCdEfGhIjKlMnOpQrStUvWxYz0123456789-_`

### Required Environment Variables

Create a `.env` file in the project root with the following variables:

```
# JWT Authentication
JWT_SECRET_KEY=<your-generated-secret-here>

# Email Service (Brevo/Sendinblue)
BREVO_API_KEY=<your-brevo-api-key>
SENDER_EMAIL=<your-sender-email@example.com>
SENDER_NAME=Heavenly

# Development/Production
DEV_MODE=True
```

**Where to get these values:**
- **JWT_SECRET_KEY**: Generate using the command above
- **BREVO_API_KEY**: Get from your Brevo account dashboard (https://app.brevo.com/settings/keys/api)
- **SENDER_EMAIL**: Email address authorized to send from your Brevo account
- **SENDER_NAME**: Display name for emails (default: "Heavenly")
- **DEV_MODE**: Set to `True` for local development, `False` for production

### Security Best Practices

⚠️ **Critical**: Never hardcode secrets or commit `.env` to git. The `.gitignore` file already excludes it. 
- Each environment (local, staging, production) should have different secrets
- Rotate JWT secrets periodically in production
- Keep BREVO_API_KEY private and never share it
- For production deployment, use environment variable injection instead of `.env` files

## First-Time Setup (Developers)

1) Clone the repo
```
git clone <repo-url>
cd travel-app
```

2) Create and activate a virtual environment
```
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

3) Install backend dependencies
```
cd backend
pip install -r requirements.txt
```

4) Start the backend server
```
uvicorn main:app --reload --port 8000
```

5) Start the frontend

Option A - Simple local server:
```
cd ../src
python -m http.server 3000
```

Option B - Open directly:
Open `src/home.html` in your browser.

## Running the Project Again (Returning Developers)

1) Activate the virtual environment
2) Start the backend server
3) Open the frontend (local server or `src/home.html`)

## For Other Users / Contributors

- Clone the repo
- Install backend dependencies
- Start the backend
- Open the frontend

No special configuration is required to run locally.

## Maintenance and Version Notes

### Current Version: Heavenly v1
- Stable booking flow with single entry point (hotel-details.html)
- No booking buttons on listing pages (home.html, search.html)
- No "Share Property" button anywhere in the app
- "Become a Host" is a global header CTA, not part of booking confirmation
- All Python cache and local files properly ignored by git

### Version 2 (Planned)
- Host onboarding and property listing flow
- Guest checkout without account creation
- Direct booking capabilities for hosts
