# Travel Explorer - Hotel Booking System

A modern, full-featured hotel booking application with user authentication, interactive calendar UI, real-time availability checking, user-specific booking history, and email confirmation system.

## 🚀 Features

### Core Functionality
- **User Authentication**: Secure signup/login with OTP email verification
- **Hotel Search & Filtering**: Search by city, price range, rating, amenities, and guest capacity
- **Interactive Calendar Booking**: Date range picker with visual availability indicators
- **Real-time Availability**: Check hotel availability before booking with conflict detection
- **User Booking History**: Personal booking dashboard with status tracking
- **Email Confirmations**: Automatic booking confirmation via Brevo API
- **Responsive Design**: Seamless experience on desktop, tablet, and mobile

### UI Enhancements
- **Blocked Dates Display**: 
  - Soft pink background (#ffe5e5) for unavailable dates
  - Subtle lock icon with hover tooltip: "Hotel not available"
  - Clear distinction from past dates (gray) and available dates (white)
  
- **Smart Price Filter**:
  - Validation triggers only on "Apply Filters" button click
  - Real-time Apply button visibility when typing
  - Min/Max validation with helpful error messages

- **User Profile Page**:
  - View all bookings with hotel details
  - Status badges (Upcoming, Completed, Cancelled)
  - Total price and guest count per booking
  - Empty state handling with demo fallback

- **Consistent Button Styling**:
  - Unified design language across all buttons
  - Smooth hover/active transitions with shadows
  - Accessible focus indicators for keyboard navigation
  - Responsive layouts for mobile devices

## 🛠️ Tech Stack

**Backend**: FastAPI (Python 3.8+)  
**Frontend**: Vanilla JavaScript (ES6 modules)  
**Database**: SQLite with row factory for dict-like access  
**Email**: Brevo Transactional Email API  
**Maps**: Leaflet.js for interactive location display  
**Validation**: Pydantic v2 for request/response schemas  

## 📁 Project Structure

```
travel-app/
├── backend/
│   ├── main.py                 # FastAPI app entry point
│   ├── requirements.txt        # Python dependencies
│   ├── load_hotels.py         # Database seeding script (REQUIRED)
│   ├── clear_hotels.py        # Database reset utility
│   ├── models/
│   │   └── user.py           # User database model
│   ├── routes/
│   │   ├── auth.py           # Authentication endpoints
│   │   └── hotels.py         # Hotel & booking endpoints
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── hotel.py          # Pydantic validation schemas
│   └── utils/
│       ├── database.py       # Database operations & queries
│       ├── email.py          # Email sending logic
│       ├── auth.py           # Password hashing & verification
│       └── otp.py            # OTP generation
├── src/
│   ├── home.html             # Homepage with recent hotels
│   ├── search.html           # Hotel search with filters
│   ├── hotel-details.html    # Booking interface with calendar
│   ├── profile.html          # User booking history
│   ├── signup.html           # User registration
│   ├── login.html            # User login
│   ├── dashboard.html        # Admin dashboard
│   └── services/
│       └── api.js            # Frontend API client
├── .env                      # Environment variables (not in git)
├── .gitignore                # Git ignore rules
└── README.md                 # This file
```

## 🎯 First-Time Setup

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Installation Steps

**1. Clone the repository**
```bash
git clone <repo-url>
cd travel-app
```

**2. Create and activate virtual environment**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

**3. Install Python dependencies**
```bash
cd backend
pip install -r requirements.txt
```

**4. Set up environment variables**

Create a `.env` file in the `backend/` directory:

```env
BREVO_API_KEY=your_brevo_api_key_here
SENDER_EMAIL=noreply@yourdomain.com
SENDER_NAME=Travel Explorer
```

To get a Brevo API key:
1. Sign up at https://www.brevo.com/
2. Go to Settings → API Keys
3. Generate a new API key
4. Copy and paste into `.env`

**5. Initialize the database with sample hotels** (REQUIRED)
```bash
# From backend/ directory
python load_hotels.py
```

This creates:
- `auth.db` database file
- `users` table (for authentication)
- `hotels` table with 6 sample hotels
- `bookings` table (for reservations)
- `email_verifications` table (for OTP)

**6. Start the backend server**
```bash
# From backend/ directory
uvicorn main:app --reload --port 8000
```

Server will run at: http://127.0.0.1:8000

**7. Start the frontend**

Option A - Using Python's built-in server:
```bash
# From project root
cd src
python -m http.server 3000
```

Option B - Using Node.js http-server:
```bash
# From project root
npx http-server src -p 3000 --cors
```

**8. Open your browser**

Navigate to: http://localhost:3000

## 🗄️ Database Management

### Load Sample Hotels (First-time setup)
```bash
python backend/load_hotels.py
```
- Creates database schema if it doesn't exist
- Populates hotels table with 6 diverse properties
- Includes hotels in Mumbai, Goa, Jaipur, Delhi, Bangalore, Udaipur
- Each hotel has unique amenities, ratings, and pricing

### Reset Hotels Table (Optional)
```bash
python backend/clear_hotels.py
python backend/load_hotels.py
```
- `clear_hotels.py` removes all hotels (preserves users and bookings)
- Useful for database cleanup or fresh hotel data

**Note**: These are essential setup scripts, not test files. Keep them in production.

## 📚 Key Features Documentation

### 1. Blocked Dates Calendar

**Visual Design**:
- **Available dates**: White background, clickable
- **Past dates**: Light gray (#f0f0f0), disabled
- **Blocked dates**: Soft pink (#ffe5e5) with subtle border (#ff9999)
- Lock icon (8px, opacity 0.4) indicates unavailability
- Hover tooltip: "Hotel not available" in soft red

**Backend Logic**:
- Queries confirmed bookings for the hotel
- Merges overlapping and adjacent date ranges
- O(n log n) complexity with efficient sorting
- Prevents double-booking automatically

### 2. Price Filter Validation

**User Experience**:
- Type freely in Min/Max price fields
- No validation errors while typing
- Click "Apply Filters" to validate and filter
- Clear error message if min > max
- Apply button shows immediately when typing

### 3. User Booking History

**Features**:
- Personal booking dashboard at `/profile.html`
- User identification via localStorage (userId)
- Multi-user support on same PC (separate histories)
- Real-time status calculation:
  - **Upcoming**: check-in date is in the future
  - **Completed**: check-in date has passed
  - **Cancelled**: explicitly marked as cancelled

**API Endpoint**:
```http
GET /hotels/users/{user_id}/bookings
```

Response:
```json
{
  "bookings": [
    {
      "id": "123",
      "hotel_id": 1,
      "hotel_name": "Luxury Beachfront Villa Mumbai",
      "check_in": "2026-03-01",
      "check_out": "2026-03-05",
      "guests": 2,
      "total_price": 28000.0,
      "status": "upcoming"
    }
  ]
}
```

## 🎨 Styling & Design

**Color Palette**:
- Brand Red: `#d90429` (primary actions)
- Brand Red Dark: `#b50321` (hover states)
- Soft Pink: `#ffe5e5` (blocked dates background)
- Gray: `#6b7280` (secondary text)
- Light Gray: `#f7f7f7` (page backgrounds)

**Responsive Breakpoints**:
- Desktop: > 900px (full 2-column layout)
- Tablet: 768px - 900px (adjusted spacing)
- Mobile: < 768px (stacked, full-width buttons)
- Small Mobile: < 480px (optimized touch targets)

## 🔐 Security Features

- Password hashing with bcrypt (Passlib)
- OTP-based email verification (6 digits, 10-minute expiry)
- User session management via localStorage
- SQL injection protection (parameterized queries)
- CORS configuration for cross-origin requests
- Environment variables for sensitive data (.env)

## 🚀 Production Deployment

### Pre-Deployment Checklist

1. **Environment Variables**
   ```bash
   # Ensure .env contains:
   BREVO_API_KEY=<production_key>
   SENDER_EMAIL=<verified_email>
   SENDER_NAME=Travel Explorer
   ```

2. **Database Setup**
   ```bash
   python backend/load_hotels.py  # Initialize database
   ```

3. **Update CORS Settings**
   
   In `backend/main.py`, update allowed origins:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=[
           "https://yourdomain.com",
           "https://www.yourdomain.com"
       ],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

4. **Use Production ASGI Server**
   ```bash
   # Install Gunicorn
   pip install gunicorn

   # Run with multiple workers
   gunicorn backend.main:app \
     --workers 4 \
     --worker-class uvicorn.workers.UvicornWorker \
     --bind 0.0.0.0:8000
   ```

5. **Frontend Deployment**
   - Deploy `src/` folder to static hosting (Netlify, Vercel, Cloudflare Pages)
   - Update `API_BASE` in `src/services/api.js` to production backend URL
   - Enable HTTPS for secure connections

## 🐛 Troubleshooting

**Backend won't start**:
- Check Python version: `python --version` (needs 3.8+)
- Verify dependencies: `pip install -r requirements.txt`
- Check port 8000 is available

**Database errors**:
- Run `python load_hotels.py` to initialize
- Check `auth.db` exists in `backend/` directory
- Verify write permissions

**Email not sending**:
- Verify Brevo API key in `.env`
- Check sender email is verified in Brevo
- Review backend logs for error messages

**Frontend can't connect to backend**:
- Ensure backend is running on port 8000
- Check `API_BASE` in `src/services/api.js`
- Verify CORS settings in `backend/main.py`

**Booking history not showing**:
- Ensure user is logged in (check localStorage)
- Verify `user_id` is stored: `localStorage.getItem('userId')`
- Check backend endpoint: `GET /hotels/users/{user_id}/bookings`

## 📄 License

This project is for educational/demonstration purposes.

---

**Version**: 2.0.0  
**Last Updated**: February 3, 2026  
**Status**: Production Ready ✅
