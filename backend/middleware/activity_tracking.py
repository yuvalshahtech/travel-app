"""
User activity tracking middleware
Automatically logs user behavior for analytics
"""
import json
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from config.database import SessionLocal
from models.models import UserActivity
from utils.jwt_auth import get_current_user_id_from_token

logger = logging.getLogger(__name__)


class UserActivityTrackingMiddleware(BaseHTTPMiddleware):
    """Track user behavior on specific routes"""
    
    # Routes to track
    TRACKED_ENDPOINTS = {
        '/hotels/search': 'search',
        '/hotels/city': 'search',
        '/hotels/': 'view_hotel',
        '/hotels/{id}': 'view_hotel',
        '/check-availability': 'booking_attempt',
        '/book': 'booking_attempt',
    }
    
    async def dispatch(self, request: Request, call_next):
        """Process request and track activity if applicable"""
        
        response = await call_next(request)
        
        # Check if this is a tracked endpoint
        path = request.url.path
        action_type = self._get_action_type(path)
        
        if action_type:
            # Extract user ID from JWT token if available
            user_id = None
            try:
                auth_header = request.headers.get('Authorization', '')
                if auth_header.startswith('Bearer '):
                    token = auth_header.split(' ')[1]
                    user_id = get_current_user_id_from_token(token)
            except Exception as e:
                logger.debug(f"Could not extract user from token: {e}")
            
            # Extract metadata based on action type
            metadata = self._extract_metadata(request, action_type)
            
            # Log activity to database (async)
            try:
                self._log_activity(user_id, action_type, metadata)
            except Exception as e:
                logger.error(f"Failed to log user activity: {e}")
        
        return response
    
    def _get_action_type(self, path: str) -> str:
        """Determine action type from path"""
        for endpoint, action in self.TRACKED_ENDPOINTS.items():
            if endpoint in path:
                return action
        return None
    
    def _extract_metadata(self, request: Request, action_type: str) -> dict:
        """Extract relevant metadata based on action type"""
        metadata = {
            'path': request.url.path,
            'method': request.method,
            'timestamp': str(request.headers.get('date', 'unknown'))
        }
        
        # Add query parameters for search actions
        if action_type == 'search':
            metadata['query_params'] = dict(request.query_params)
        
        # Add hotel ID for view_hotel actions
        elif action_type == 'view_hotel':
            path_parts = request.url.path.split('/')
            if path_parts:
                metadata['hotel_id'] = path_parts[-1]
        
        return metadata
    
    def _log_activity(self, user_id: int, action_type: str, metadata: dict) -> None:
        """Log activity to database"""
        db = SessionLocal()
        try:
            activity = UserActivity(
                user_id=user_id,
                action_type=action_type,
                metadata=metadata
            )
            db.add(activity)
            db.commit()
            logger.debug(f"Logged activity: user={user_id}, action={action_type}")
        except Exception as e:
            logger.error(f"Error logging activity: {e}")
            db.rollback()
        finally:
            db.close()
