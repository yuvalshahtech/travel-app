"""
Application settings and configuration
Loads from environment variables
"""
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)


class Settings:
    """Application settings from environment variables"""
    
    # Database Configuration (PostgreSQL)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/heavenly_db"
    )
    
    # JWT Configuration
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY",
        "your-secret-key-change-in-production"
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 168  # 7 days
    
    # Email Configuration (Brevo)
    BREVO_API_KEY: str = os.getenv("BREVO_API_KEY", "")
    SENDER_EMAIL: str = os.getenv("SENDER_EMAIL", "noreply@heavenly.com")
    
    # App Configuration
    APP_NAME: str = "Heavenly Hotel Booking"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = ENVIRONMENT == "development"
    
    # CORS Configuration
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = "logs/app.log"
    
    # OTP Configuration
    OTP_EXPIRY_MINUTES: int = 5
    
    # ── Rate Limiting Configuration ──────────────────────────────────────
    # Format: "<max_requests>/<window>" e.g. "5/15minutes", "3/1hour"
    # Parsed by backend.middleware.rate_limiter._parse_rate()
    LOGIN_RATE_LIMIT: str = os.getenv("LOGIN_RATE_LIMIT", "5/15minutes")
    SIGNUP_RATE_LIMIT: str = os.getenv("SIGNUP_RATE_LIMIT", "3/1hour")
    SIGNUP_EMAIL_RATE_LIMIT: str = os.getenv("SIGNUP_EMAIL_RATE_LIMIT", "3/1hour")
    ACTIVITY_RATE_LIMIT: str = os.getenv("ACTIVITY_RATE_LIMIT", "60/1minute")
    
    # Maximum tracked keys in the in-memory store (防 memory exhaustion)
    # Each key ≈ 200 bytes. 10,000 keys ≈ 2 MB.
    RATE_LIMIT_MAX_KEYS: int = int(os.getenv("RATE_LIMIT_MAX_KEYS", "10000"))
    
    # Log a security warning after this many blocked requests per key
    ABUSE_LOG_THRESHOLD: int = int(os.getenv("ABUSE_LOG_THRESHOLD", "10"))

    # ── Analytics Buffer Configuration ───────────────────────────────────
    # How many events per bulk INSERT statement
    ANALYTICS_BATCH_SIZE: int = int(os.getenv("ANALYTICS_BATCH_SIZE", "100"))
    # Seconds between forced flush (even if batch not full)
    ANALYTICS_FLUSH_INTERVAL: float = float(os.getenv("ANALYTICS_FLUSH_INTERVAL", "5.0"))
    # Maximum events the in-memory queue can hold before backpressure kicks in
    ANALYTICS_MAX_QUEUE_SIZE: int = int(os.getenv("ANALYTICS_MAX_QUEUE_SIZE", "5000"))
    # Drop heartbeat events first when queue is >80% full
    ANALYTICS_DROP_HEARTBEAT_ON_OVERFLOW: bool = os.getenv("ANALYTICS_DROP_HEARTBEAT_ON_OVERFLOW", "true").lower() == "true"
    # Extra headroom above max_queue_size reserved for CRITICAL events
    ANALYTICS_CRITICAL_HEADROOM: int = int(os.getenv("ANALYTICS_CRITICAL_HEADROOM", "500"))
    # Maximum retries for failed bulk inserts before dead-lettering
    ANALYTICS_MAX_RETRIES: int = int(os.getenv("ANALYTICS_MAX_RETRIES", "3"))
    # Base delay (seconds) for exponential backoff between retries
    ANALYTICS_RETRY_BASE_DELAY: float = float(os.getenv("ANALYTICS_RETRY_BASE_DELAY", "1.0"))
    
    @classmethod
    def get_database_url(cls) -> str:
        """Get database URL"""
        return cls.DATABASE_URL
    
    @classmethod
    def get_jwt_secret(cls) -> str:
        """Get JWT secret key"""
        if cls.JWT_SECRET_KEY == "your-secret-key-change-in-production":
            if cls.ENVIRONMENT == "production":
                raise ValueError(
                    "JWT_SECRET_KEY not configured in production! "
                    "Set JWT_SECRET_KEY in .env file"
                )
        return cls.JWT_SECRET_KEY


# Singleton instance
settings = Settings()
