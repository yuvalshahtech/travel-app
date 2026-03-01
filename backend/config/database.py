"""
PostgreSQL database configuration and engine setup
Replaces the old SQLite database.py
"""
from sqlalchemy import create_engine, event, Engine, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import NullPool
from contextlib import contextmanager
import logging
from backend.config.settings import settings

logger = logging.getLogger(__name__)

# SQLAlchemy Base for ORM models
Base = declarative_base()

# Create PostgreSQL engine
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,  # Don't use connection pooling for now, add HikariCP later
    echo=False,  # Set to True to see SQL queries
    connect_args={
        "connect_timeout": 10,
        "application_name": "heavenly_app"
    }
)

# Event listeners for connection management
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set production-ready connection settings"""
    # This would be PostgreSQL-specific settings
    pass


@event.listens_for(Engine, "engine_disposed")
def receive_engine_disposed(engine):
    """Log when engine is disposed"""
    logger.info("Database connection pool disposed")


# Session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session
)


def get_db() -> Session:
    """
    Database session dependency for FastAPI
    
    Usage in routes:
        @app.get("/")
        async def read_root(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database sessions outside of FastAPI routes
    
    Usage:
        with get_db_context() as db:
            # use db
            ...
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"Database transaction error: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


def init_database():
    """
    Initialize database: create all tables from ORM models
    
    IMPORTANT: For PostgreSQL, use Alembic migrations instead!
    This is a fallback for development only.
    """
    try:
        logger.info("Initializing database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise


def test_database_connection():
    """Test database connectivity"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info("✓ Database connection successful")
            return True
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        return False


def close_database():
    """Close all database connections"""
    try:
        engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")
