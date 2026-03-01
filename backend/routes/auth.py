import time
import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from passlib.exc import UnknownHashError
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from schemas.auth import UserLogin
from models.models import User as UserModel, EmailVerification  # SQLAlchemy ORM models
from config.database import get_db
from utils.auth import hash_password, verify_password
from utils.otp import generate_otp, get_otp_expiry, is_otp_expired
from utils.email import send_otp_email
from utils.jwt_auth import create_access_token
from utils.activity_logger import log_user_activity
from middleware.abuse_protection import (
    check_login_rate_limit,
    check_signup_rate_limit,
    on_login_success,
    on_login_failure,
    constant_time_login,
)

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/signup")
async def signup(
    request: Request,
    user: UserLogin,
    db: Session = Depends(get_db),
    _rate_check: None = Depends(check_signup_rate_limit),
):
    """
    Sign up a new user
    Step 1: Store email, hashed password, OTP
    Step 2: Send OTP to email
    Does NOT create user in users table yet

    Rate limited: max 3 signups per IP per hour (configurable).
    Returns identical response shape for "already exists" and "OTP sent"
    to prevent user enumeration.
    """
    
    # Case 1: Account already fully created
    # NOTE: We do NOT reveal that the account exists to prevent enumeration.
    # The response shape is the same as the success case.
    existing_user = db.query(UserModel).filter(UserModel.email == user.email).first()
    if existing_user:
        # Return same shape as success — the user will discover the conflict
        # when they try to verify OTP (or they can try logging in).
        logger.info(f"Signup attempt for existing account: {user.email}")
        return {
            "message": "If this email is not already registered, you will receive an OTP shortly.",
            "email": user.email
        }

    # Case 2: OTP already pending
    existing_verification = db.query(EmailVerification).filter(EmailVerification.email == user.email).first()
    if existing_verification:
        # Same generic response — prevents enumeration of pending signups
        logger.info(f"Signup attempt with pending OTP: {user.email}")
        return {
            "message": "If this email is not already registered, you will receive an OTP shortly.",
            "email": user.email
        }

    # Hash the password (truncated to 72 bytes internally)
    password_hash = hash_password(user.password)
    
    # Generate OTP
    otp = generate_otp()
    expires_at = get_otp_expiry()
    
    # Store in email_verifications table
    try:
        verification = EmailVerification(
            email=user.email,
            password_hash=password_hash,
            otp=otp,
            expires_at=expires_at
        )
        db.add(verification)
        db.commit()
        db.refresh(verification)
    except Exception as e:
        db.rollback()
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
        "message": "If this email is not already registered, you will receive an OTP shortly.",
        "email": user.email
    }

@router.post("/verify-otp")
async def verify_otp(data: dict, db: Session = Depends(get_db)):
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
    verification = db.query(EmailVerification).filter(EmailVerification.email == email).first()
    
    if not verification:
        raise HTTPException(status_code=404, detail="No pending verification for this email.")
    
    # Check if OTP is expired
    if is_otp_expired(verification.expires_at.isoformat()):
        db.delete(verification)
        db.commit()
        raise HTTPException(status_code=410, detail="OTP has expired. Please sign up again.")
    
    # Verify OTP
    if verification.otp != otp:
        raise HTTPException(status_code=401, detail="Incorrect OTP.")
    
    # OTP is valid, create user
    try:
        new_user = UserModel(
            email=email,
            password_hash=verification.password_hash,
            login_count=0
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        user_id = new_user.id
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Account already exists. Please log in.")
    
    # Delete verification record
    db.delete(verification)
    db.commit()
    
    return {
        "message": "Email verified. Account created successfully.",
        "user_id": user_id,
        "email": email
    }

@router.post("/login")
async def login(
    request: Request,
    user: UserLogin,
    db: Session = Depends(get_db),
    _rate_check: None = Depends(check_login_rate_limit),
):
    """
    Login user - Returns JWT access token.

    Security measures:
      - Rate limited per IP AND per email (dual-layer, with exponential backoff)
      - Counters reset on successful login
      - Constant-time response (≥200ms) to prevent timing attacks
      - Generic error message for both "user not found" and "wrong password"
        to prevent user enumeration
      - Excessive failures logged for abuse detection
    """
    start = time.monotonic()

    # Generic error message — same for "no user" and "wrong password"
    GENERIC_AUTH_ERROR = "Invalid email or password."

    # Get user from database
    db_user = db.query(UserModel).filter(UserModel.email == user.email).first()
    
    if not db_user:
        # User not found — but we still burn time mimicking bcrypt verify
        # to prevent timing-based user enumeration.
        # hash_password() internally calls bcrypt which takes ~100ms.
        # We do a dummy verify instead of a full hash to be cheaper.
        try:
            verify_password("dummy_password", "$2b$12$LJ3m4ys3Gzl/000000000u0000000000000000000000000000000")
        except Exception:
            pass
        await on_login_failure(request, user.email)
        await constant_time_login(start)
        raise HTTPException(status_code=401, detail=GENERIC_AUTH_ERROR)
    
    stored_hash = db_user.password_hash
    if not stored_hash:
        await on_login_failure(request, user.email)
        await constant_time_login(start)
        raise HTTPException(status_code=401, detail=GENERIC_AUTH_ERROR)
    
    try:
        if not verify_password(user.password, stored_hash):
            await on_login_failure(request, user.email)
            await constant_time_login(start)
            raise HTTPException(status_code=401, detail=GENERIC_AUTH_ERROR)
    except UnknownHashError:
        await on_login_failure(request, user.email)
        await constant_time_login(start)
        raise HTTPException(status_code=401, detail=GENERIC_AUTH_ERROR)
    
    # ── Success path ──
    # Reset rate-limit counters so the user isn't penalized for earlier typos
    await on_login_success(request, user.email)

    # Update last login
    db_user.last_login = datetime.utcnow()
    db_user.login_count = (db_user.login_count or 0) + 1
    db.commit()
    
    # Generate JWT token with user_id and email
    access_token = create_access_token(
        data={"sub": str(db_user.id), "email": db_user.email}
    )
    
    # Log user activity (login)
    log_user_activity(
        user_id=db_user.id,
        action_type="login",
        activity_event={
            "message": "User login",
            "email": db_user.email
        },
        db=db
    )

    await constant_time_login(start)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "email": db_user.email,
        "message": "Login successful"
    }

