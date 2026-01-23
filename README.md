# Authentication API (FastAPI + Brevo OTP)

Production-ready email OTP signup flow with FastAPI backend and simple HTML frontend.

## Project Structure

```
Travel-App/
├─ backend/
│  ├─ main.py              # FastAPI app entry
│  ├─ requirements.txt     # Python deps
│  ├─ routes/auth.py       # /signup, /verify-otp, /login
│  └─ utils/               # auth, database, otp, email
└─ src/
   ├─ signup.html          # Signup + OTP form
   ├─ login.html           # Login
   └─ dashboard.html       # Placeholder
```

## Quick Start (Windows + PowerShell)

1) Install dependencies
```
cd backend
pip install -r requirements.txt
```

2) Configure environment variables (root .env or session)
- Create `.env` in project root (Travel-App/.env):
```
BREVO_API_KEY=xkeysib-your-api-key
SENDER_EMAIL=your-verified-sender@example.com
SENDER_NAME=Travel App
DEV_MODE=false
```
  or set for current session:
```
$env:BREVO_API_KEY="xkeysib-your-api-key"
$env:SENDER_EMAIL="your-verified-sender@example.com"
$env:SENDER_NAME="Travel App"
$env:DEV_MODE="false"
```

3) Verify env vars are visible to Python
```
cd backend
python -c "import os;print('BREVO_API_KEY:', 'SET' if os.getenv('BREVO_API_KEY') else 'NOT SET');print('SENDER_EMAIL:', os.getenv('SENDER_EMAIL','NOT SET'))"
```

4) Start the API server
```
cd ..
uvicorn backend.main:app --reload
```
Runs at http://localhost:8000

5) Test signup (no frontend)
```
$body = @{ email = "test@example.com"; password = "Pass123!" } | ConvertTo-Json
curl -X POST http://localhost:8000/signup -H "Content-Type: application/json" -d $body
```
Expected (success): `{ "message": "Signup prepared. Check your email for OTP.", "email": "..." }`

## OTP & Email Flow (High Level)
- User submits email + password to `/signup`.
- Backend generates a 6‑digit OTP, stores a pending record, and emails the OTP via Brevo.
- User calls `/verify-otp` with the code to create the account.
- OTP expires in 10 minutes. OTP is never returned by the API.
- If email sending fails, the API returns a clean error (HTTP 503).

## Environment Variables
- `BREVO_API_KEY` (required): Brevo transactional API key (starts with `xkeysib-`).
- `SENDER_EMAIL` (required): Must be verified in Brevo dashboard (Settings → Senders).
- `SENDER_NAME` (optional): Friendly sender name. Default: "Travel App".
- `DEV_MODE` (optional): `true/1/yes` logs OTP on failure for local debugging.

## Common Blockers (Fix First)
- Sender not verified in Brevo → Verify at https://app.brevo.com/settings/senders.
- Env vars not loaded → Ensure they show as SET via the Python check above.
- 401 from Brevo → Wrong/expired `BREVO_API_KEY`.

## Minimal Frontend (optional)
Serve static files to use the HTML pages:
```
cd src
python -m http.server 3000
```
Open: http://localhost:3000/signup.html

That’s it. You can sign up, receive the OTP by email, verify, and log in.
