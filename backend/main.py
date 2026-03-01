from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root (parent of backend directory)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

import logging
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from routes.auth import router as auth_router
from routes.hotels import router as hotels_router
from routes.activity import router as activity_router
from config.database import init_database
from middleware.rate_limiter import start_cleanup_task, stop_cleanup_task
from services.analytics_worker import analytics_worker

# Configure logging to see email debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Initialize FastAPI app
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
app = FastAPI(
    title="Heavenly Hotel Booking API",
    version="1.0.0",
    docs_url="/docs" if ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if ENVIRONMENT != "production" else None,
)

# Mount static files directory BEFORE CORS middleware
# This ensures static file routes exist before CORS processing
uploads_dir = Path(__file__).parent / "uploads"
if uploads_dir.exists():
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

# Configure CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    # Validate critical environment variables
    jwt_secret = os.getenv("JWT_SECRET_KEY")
    if not jwt_secret:
        raise RuntimeError("FATAL: JWT_SECRET_KEY is not set")
    if ENVIRONMENT == "production" and len(jwt_secret) < 32:
        raise RuntimeError("FATAL: JWT_SECRET_KEY must be at least 32 characters in production")
    init_database()
    # Start the rate-limiter background cleanup (evicts stale entries every 10 min)
    start_cleanup_task()
    # Start the analytics background worker (drains buffer → bulk INSERT)
    analytics_worker.start()


@app.on_event("shutdown")
async def shutdown_event():
    stop_cleanup_task()
    # Flush remaining buffered analytics events and stop the worker
    await analytics_worker.stop()


# Global exception handler — never expose stack traces
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.getLogger(__name__).error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# Include routers
app.include_router(auth_router)
app.include_router(hotels_router)
app.include_router(activity_router)

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Authentication API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
