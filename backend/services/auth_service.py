"""
Authentication service - user registration, login, OTP verification
Handles password hashing, JWT token generation, and logging
"""
import logging
from typing import Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.models.models import User, EmailVerification
from backend.utils.auth import hash_password, verify_password
from backend.utils.otp import generate_otp, is_otp_expired
from backend.utils.jwt_auth import create_access_token
from backend.utils.email import send_otp_email
from backend.config.settings import settings

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication business logic"""
    
    @staticmethod
    def signup(db: Session, email: str, password: str) -> Tuple[bool, str]:
        """
        Sign up user: store email/password, generate and send OTP
        
        Returns:
            (success: bool, message: str)
        """
        try:
            # Check if user already exists
            existing_user = db.query(User).filter(User.email == email).first()
            if existing_user:
                logger.warning(f"Signup failed: User {email} already exists")
                return (False, "Account already exists. Please log in.")
            
            # Check if OTP already pending
            pending_verification = db.query(EmailVerification).filter(
                EmailVerification.email == email
            ).first()
            if pending_verification:
                logger.warning(f"Signup failed: OTP already pending for {email}")
                return (False, "OTP already sent. Please verify your email.")
            
            # Hash password
            password_hash = hash_password(password)
            
            # Generate OTP
            otp = generate_otp()
            expires_at = datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
            
            # Store in email_verifications table
            verification = EmailVerification(
                email=email,
                password_hash=password_hash,
                otp=otp,
                expires_at=expires_at
            )
            db.add(verification)
            db.commit()
            
            logger.info(f"User registered for OTP verification: {email}")
            
            # Send OTP email
            email_sent = send_otp_email(email, otp)
            if not email_sent:
                logger.error(f"Failed to send OTP email to {email}")
                return (False, "Failed to send OTP email. Please try again.")
            
            logger.info(f"OTP sent successfully to {email}")
            return (True, "Signup prepared. Check your email for OTP.")
        
        except Exception as e:
            logger.error(f"Signup error for {email}: {e}", exc_info=True)
            db.rollback()
            raise
    
    @staticmethod
    def verify_otp(db: Session, email: str, otp_code: str) -> Tuple[bool, str, Optional[str]]:
        """
        Verify OTP and create user account
        
        Returns:
            (success: bool, message: str, access_token: Optional[str])
        """
        try:
            # Get verification record
            verification = db.query(EmailVerification).filter(
                EmailVerification.email == email
            ).first()
            
            if not verification:
                logger.warning(f"OTP verification failed: No pending verification for {email}")
                return (False, "No pending verification for this email.", None)
            
            # Check if OTP is expired
            if is_otp_expired(verification.expires_at):
                db.delete(verification)
                db.commit()
                logger.warning(f"OTP verification failed: OTP expired for {email}")
                return (False, "OTP has expired. Please sign up again.", None)
            
            # Verify OTP
            if verification.otp != otp_code:
                logger.warning(f"OTP verification failed: Invalid OTP for {email}")
                return (False, "Invalid OTP. Please try again.", None)
            
            # Create user in users table
            user = User(
                email=email,
                password_hash=verification.password_hash,
                login_count=0
            )
            db.add(user)
            db.flush()  # Get user ID
            
            # Delete verification record
            db.delete(verification)
            db.commit()
            
            logger.info(f"User verified: {email} (user_id={user.id})")
            
            # Generate JWT token
            access_token = create_access_token(data={"sub": str(user.id)})
            
            return (True, "Email verified. Account created successfully.", access_token)
        
        except Exception as e:
            logger.error(f"OTP verification error for {email}: {e}", exc_info=True)
            db.rollback()
            raise
    
    @staticmethod
    def login(db: Session, email: str, password: str) -> Tuple[bool, str, Optional[str]]:
        """
        User login: verify credentials and generate JWT token
        
        Returns:
            (success: bool, message: str, access_token: Optional[str])
        """
        try:
            # Get user
            user = db.query(User).filter(User.email == email).first()
            if not user:
                logger.warning(f"Login failed: User {email} not found")
                return (False, "Invalid credentials.", None)
            
            # Verify password
            if not verify_password(password, user.password_hash):
                logger.warning(f"Login failed: Invalid password for {email}")
                return (False, "Invalid credentials.", None)
            
            # Update login tracking
            user.last_login = datetime.utcnow()
            user.login_count += 1
            db.commit()
            
            logger.info(f"User logged in: {email} (user_id={user.id})")
            
            # Generate JWT token
            access_token = create_access_token(data={"sub": str(user.id)})
            
            return (True, "Login successful.", access_token)
        
        except Exception as e:
            logger.error(f"Login error for {email}: {e}", exc_info=True)
            db.rollback()
            raise
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get user by ID"""
        try:
            user = db.query(User).filter(User.id == user_id).first()
            return user
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {e}", exc_info=True)
            raise
