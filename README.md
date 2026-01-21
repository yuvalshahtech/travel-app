# Authentication System

A complete authentication system with FastAPI backend and vanilla JavaScript frontend.

## Project Structure

```
Travel-App/
├── backend/
│   ├── main.py           # FastAPI application
│   ├── requirements.txt  # Python dependencies
│   ├── models/
│   │   └── user.py      # User models
│   ├── routes/
│   │   └── auth.py      # Authentication endpoints
│   └── utils/
│       ├── auth.py      # Password hashing (bcrypt)
│       ├── database.py  # Database operations
│       ├── otp.py       # OTP generation and validation
│       └── email.py     # Email sending
└── src/
    ├── login.html       # Login page
    ├── signup.html      # Signup + OTP verification page
    └── dashboard.html   # Dashboard page
```

## Setup Instructions

### Backend Setup

1. Navigate to the backend directory:
   ```
   cd backend
   ```

2. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the FastAPI server:
   ```
   python main.py
   ```

   The server will start at `http://localhost:8000`

### Frontend Setup

1. Open the HTML files directly in your browser, or use a simple HTTP server:
   
   From the `src` directory:
   ```
   python -m http.server 3000
   ```

2. Access the application:
   - Signup: `http://localhost:3000/signup.html`
   - Login: `http://localhost:3000/login.html`

## Features

### Signup Flow (Email OTP Verification)
- User enters email and password
- OTP (6-digit code) is generated and sent to email
- User must verify OTP before account is created
- Pending OTP signups do not block re-signup attempts
- On successful verification, user is redirected to login

### Login Flow
- Credentials prefilled if redirected from signup
- On successful login, shows "Login Successful" message
- Redirects to dashboard

### Security
- Passwords hashed using bcrypt (72-byte max length)
- OTP valid for 10 minutes; expires and requires new signup
- No plain text passwords stored
- Email uniqueness enforced at database level
- CORS enabled for frontend-backend communication

## API Endpoints

### POST /signup
Initiates signup and sends OTP.

Request:
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

Response (success):
```json
{
  "message": "Signup prepared. Check your email for OTP.",
  "email": "user@example.com"
}
```

### POST /verify-otp
Verifies OTP and creates account.

Request:
```json
{
  "email": "user@example.com",
  "otp": "123456"
}
```

Response (success):
```json
{
  "message": "Email verified. Account created successfully.",
  "user_id": 1,
  "email": "user@example.com"
}
```

### POST /login
Request:
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

Response (success):
```json
{
  "id": 1,
  "email": "user@example.com",
  "message": "Login successful"
}
```

## Database

SQLite database (`auth.db`) is created automatically on first run.

**users table:** Stores verified accounts
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**email_verifications table:** Temporary OTP records (deleted after verification)
```sql
CREATE TABLE email_verifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    otp TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Technologies Used

### Frontend
- Plain HTML5
- CSS3 (no frameworks)
- Vanilla JavaScript (ES6+)
- Fetch API for HTTP requests
- LocalStorage for temporary credential storage

### Backend
- FastAPI (Python web framework)
- SQLite (database)
- Pydantic (data validation)
- Uvicorn (ASGI server)

## Notes

- This is a basic authentication system for learning purposes
- No JWT tokens or session management implemented
- LocalStorage is used only for temporary credential prefilling
- Database file is created in the backend directory
