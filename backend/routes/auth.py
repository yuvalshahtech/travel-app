from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from passlib.exc import UnknownHashError
from backend.models.user import User
from backend.utils.database import (
    user_exists, create_user, get_user_by_email,
    create_email_verification, get_email_verification, delete_email_verification, email_verification_exists
)
from backend.utils.auth import hash_password, verify_password
from backend.utils.otp import generate_otp, get_otp_expiry, is_otp_expired
from backend.utils.email import send_otp_email
from backend.utils.jwt_auth import create_access_token
import sqlite3

router = APIRouter()

@router.post("/signup")
async def signup(user: User):
    """
    Sign up a new user
    Step 1: Store email, hashed password, OTP
    Step 2: Send OTP to email
    Does NOT create user in users table yet
    """
    
# Case 1: Account already fully created
    if user_exists(user.email):
        raise HTTPException(
            status_code=409,
            detail="Account already exists. Please log in."
        )

    # Case 2: OTP already pending
    if email_verification_exists(user.email):
        raise HTTPException(
            status_code=409,
            detail="OTP already sent. Please verify your email."
        )

    # Hash the password (truncated to 72 bytes internally)
    password_hash = hash_password(user.password)
    
    # Generate OTP
    otp = generate_otp()
    expires_at = get_otp_expiry()
    
    # Store in email_verifications table
    try:
        verification_id = create_email_verification(
            user.email,
            password_hash,
            otp,
            expires_at.isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to prepare verification.")
    
    # Send OTP to email (MUST succeed in production - no fallback)
    email_sent = send_otp_email(user.email, otp)

    if not email_sent:
        return JSONResponse(
            status_code=503,
            content={
                "message": "Failed to send OTP email. Please try again.",
                "email": user.email,
                "error": "email_send_failed"
            }
        )
    
    return {
        "message": "Signup prepared. Check your email for OTP.",
        "email": user.email
    }

@router.post("/verify-otp")
async def verify_otp(data: dict):
    """
    Verify OTP and create user account
    Step 2: User provides OTP
    Step 3: Create user in users table if OTP is valid
    """
    email = data.get("email")
    otp = data.get("otp")
    
    if not email or not otp:
        raise HTTPException(status_code=400, detail="Email and OTP required.")
    
    # Get verification record
    verification = get_email_verification(email)
    
    if not verification:
        raise HTTPException(status_code=404, detail="No pending verification for this email.")
    
    # Check if OTP is expired
    if is_otp_expired(verification['expires_at']):
        delete_email_verification(email)
        raise HTTPException(status_code=410, detail="OTP has expired. Please sign up again.")
    
    # Verify OTP
    if verification['otp'] != otp:
        raise HTTPException(status_code=401, detail="Incorrect OTP.")
    
    # OTP is valid, create user
    try:
        user_id = create_user(email, verification['password_hash'])
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Account already exists. Please log in.")
    
    if not user_id:
        raise HTTPException(status_code=500, detail="Failed to create user.")
    
    # Delete verification record
    delete_email_verification(email)
    
    return {
        "message": "Email verified. Account created successfully.",
        "user_id": user_id,
        "email": email
    }

@router.post("/login")
async def login(user: User):
    """
    Login user - Returns JWT access token
    Validates email and password
    """
    # Get user from database
    db_user = get_user_by_email(user.email)
    
    if not db_user:
        raise HTTPException(status_code=404, detail="No account found. Please sign up.")
    
    stored_hash = db_user['password_hash']
    if not stored_hash:
        raise HTTPException(status_code=400, detail="Stored password hash is invalid.")
    
    try:
        if not verify_password(user.password, stored_hash):
            raise HTTPException(status_code=401, detail="Incorrect password.")
    except UnknownHashError:
        raise HTTPException(status_code=400, detail="Stored password hash is invalid.")
    
    # Generate JWT token with user_id and email
    # JWT spec requires 'sub' claim to be a STRING
    access_token = create_access_token(
        data={"sub": str(db_user['id']), "email": db_user['email']}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "email": db_user['email'],
        "message": "Login successful"
    }

