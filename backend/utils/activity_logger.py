"""
User activity logging utility
Logs user behavior to the user_activity table for analytics
"""
import logging
from typing import Optional
from sqlalchemy.orm import Session
from backend.models.models import UserActivity
from backend.config.database import SessionLocal

logger = logging.getLogger(__name__)


def log_user_activity(
    user_id: Optional[int],
    action_type: str,
    activity_event: Optional[dict] = None,
    db: Optional[Session] = None
) -> bool:
    """
    Log user activity to the user_activity table
    
    Args:
        user_id: ID of the user performing the action (can be None for anonymous)
        action_type: Type of action ('login', 'search', 'view', 'booking')
        activity_event: JSON dictionary with event metadata
        db: Database session (if None, creates new session)
    
    Returns:
        True if logged successfully, False otherwise
    """
    try:
        # Use provided session or create new one
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        # Create activity record
        # Let database auto-generate timestamp via server_default
        activity = UserActivity(
            user_id=user_id,
            action_type=action_type,
            activity_event=activity_event
        )
        
        # Add, commit, and refresh
        db.add(activity)
        db.commit()
        db.refresh(activity)
        
        logger.info(
            f"User activity logged: user_id={user_id}, action_type={action_type}"
        )
        
        return True
    
    except Exception as e:
        logger.error(f"Failed to log user activity: {e}", exc_info=True)
        if db:
            db.rollback()
        return False
    
    finally:
        if should_close and db:
            db.close()
