"""
Request logging middleware for production monitoring
Logs all API requests and responses
"""
import time
import logging
import json
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all HTTP requests and responses"""
    
    async def dispatch(self, request: Request, call_next):
        """Process request and log it"""
        
        # Extract request info
        request_id = request.headers.get('X-Request-ID', 'unknown')
        method = request.method
        path = request.url.path
        query_params = dict(request.query_params)
        client_ip = request.client.host if request.client else 'unknown'
        
        # Start timer
        start_time = time.time()
        
        # Log request
        logger.info(
            f"REQUEST: {method} {path}",
            extra={
                'method': method,
                'path': path,
                'query_params': query_params,
                'client_ip': client_ip,
                'request_id': request_id
            }
        )
        
        try:
            # Call the route
            response = await call_next(request)
        except Exception as e:
            # Log exception
            elapsed_time = time.time() - start_time
            logger.error(
                f"ERROR: {method} {path} - {str(e)}",
                exc_info=True,
                extra={
                    'method': method,
                    'path': path,
                    'elapsed_time': elapsed_time,
                    'request_id': request_id,
                    'error': str(e)
                }
            )
            raise
        
        # Calculate response time
        elapsed_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"RESPONSE: {method} {path} - {response.status_code}",
            extra={
                'method': method,
                'path': path,
                'status_code': response.status_code,
                'elapsed_time': round(elapsed_time, 3),
                'request_id': request_id
            }
        )
        
        # Add response headers
        response.headers['X-Process-Time'] = str(elapsed_time)
        response.headers['X-Request-ID'] = request_id
        
        return response
