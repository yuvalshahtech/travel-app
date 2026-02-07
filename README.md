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
- **Transparent Price Breakdown** - Clear cost breakdown with no hidden fees
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

## Price Breakdown Feature

Heavenly features a transparent price breakdown system that shows users exactly how their final booking cost is calculated—no hidden fees, no surprises.

### Custom Fee Structure

The platform applies a fair, transparent fee model:

1. **Base Stay Price**: ₹[price_per_night] × [nights] = ₹[total]
   - The actual cost of the room based on nightly rate and number of nights

2. **Platform Maintenance Fee** (2% of base stay)
   - Covers platform operations, maintenance, and continuous improvements

3. **Host Service Support** (2% of base stay)
   - Dedicated support team for hosts and customer service

4. **Local Taxes & Regulations** (5% of subtotal)
   - Government-mandated taxes applied at checkout

### How It Works for Users

1. Users select check-in and check-out dates on the hotel detail page
2. The booking summary automatically calculates and displays the price breakdown
3. A **"Price Breakdown"** card appears showing:
   - Collapsed view: Total payable amount with a toggle button
   - Expanded view: Detailed line-by-line breakdown with explanations
4. The breakdown updates **dynamically** as users change dates or guest count
5. A trust signal assures: **"No hidden charges — this is the final amount you pay"**

### Code Structure for Future Customization

The fee configuration is modular and easy to adjust (`src/hotel-details.html`):

```javascript
const FEES = {
  platformMaintenance: { percent: 2 },  // 2% of base stay
  hostSupport: { percent: 2 },          // 2% of base stay
  taxRate: 0.05                         // 5% tax on subtotal
};

function calculateBreakdown(basePrice, nights) {
  // Returns object with all components needed for display
  return {
    baseStayPrice,
    platformFee,
    hostSupportFee,
    taxAmount,
    total
  };
}
```

**For Version 2**: This structure allows hosts to:
- Set custom platform fees per property
- View their earnings vs platform costs
- Experiment with pricing strategies

### Key Design Decisions

- ✅ **No rounding tricks**: Each component rounded; total verified as sum
- ✅ **Human-readable labels**: "Platform Maintenance Fee" not "PMF" or technical jargon
- ✅ **Expandable details**: Users can see full breakdown without overwhelming them by default
- ✅ **Trust signal**: Green checkmark and reassurance message build confidence
- ✅ **Dynamic updates**: Breakdown recalculates instantly as dates change

## Maintenance and Version Notes

### Current Version: Heavenly v1
- Stable booking flow with single entry point (hotel-details.html)
- No booking buttons on listing pages (home.html, search.html)
- No "Share Property" button anywhere in the app
- "Become a Host" is a global header CTA, not part of booking confirmation
- Transparent price breakdown with no hidden fees
- All Python cache and local files properly ignored by git

### Version 2 (Planned)
- Host onboarding and property listing flow
- Guest checkout without account creation
- Direct booking capabilities for hosts
- Customizable platform fees per host/property
- Host earnings dashboard with fee comparison

