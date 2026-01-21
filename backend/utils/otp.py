import random
import string
from datetime import datetime, timedelta

def generate_otp() -> str:
    """Generate a 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))

def get_otp_expiry(minutes: int = 10):
    """Get OTP expiry time (default 10 minutes from now)"""
    return datetime.utcnow() + timedelta(minutes=minutes)

def is_otp_expired(expires_at_str: str) -> bool:
    """Check if OTP is expired"""
    expires_at = datetime.fromisoformat(expires_at_str)
    return datetime.utcnow() > expires_at
