from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root (parent of backend directory)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.routes.auth import router as auth_router
from backend.routes.hotels import router as hotels_router
from backend.utils.database import init_database

# Configure logging to see email debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Initialize FastAPI app
app = FastAPI(title="Authentication API", version="1.0.0")

# Mount static files directory BEFORE CORS middleware
# This ensures static file routes exist before CORS processing
uploads_dir = Path(__file__).parent / "uploads"
if uploads_dir.exists():
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

# Configure CORS - must be after mounts but before routes
# Development configuration: allows requests from frontend on different port
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Frontend dev server
        "http://127.0.0.1:3000",  # Alternative localhost
    ],
    allow_credentials=True,  # Allow cookies/auth headers
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],  # Expose all response headers to frontend
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_database()
    # Verify JWT_SECRET_KEY is loaded
    import sys
    from backend.utils.jwt_auth import get_secret_key
    secret = get_secret_key()
    print(f"[STARTUP] JWT_SECRET_KEY is configured: {secret[:20]}... (length: {len(secret)})", file=sys.stderr)
    print(f"[STARTUP] JWT authentication is ready", file=sys.stderr)

# Include routers
app.include_router(auth_router)
app.include_router(hotels_router)

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Authentication API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
