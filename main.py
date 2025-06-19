"""
FastAPI Backend for Developer Efficiency Tracker
Replaces the Streamlit application with a REST API backend.
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import uvicorn
from pathlib import Path
import boto3

from routers import admin, engineer, auth, teams, data
from core.config import get_settings
from core.database import init_data_managers

# Initialize FastAPI app
app = FastAPI(
    title="Developer Efficiency Tracker API",
    description="API for tracking and analyzing developer productivity gains from AI coding assistants",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configure CORS for Vue.js frontend
# Get allowed origins from environment or use defaults
allowed_origins = os.environ.get("CORS_ORIGINS", "").split(",") if os.environ.get("CORS_ORIGINS") else [
    "http://localhost:5173",  # Vite dev server default
    "http://localhost:5174",  # Vite dev server alternative
    "http://localhost:3000",  # Common dev port
    "http://localhost:8080",  # Common dev port
    "https://mnwpivaen5.us-east-1.awsapprunner.com",  # Current AppRunner URL
    "https://bynixti6xn.us-east-1.awsapprunner.com"
]

# Add current host for production
if not os.environ.get("DEVELOPMENT_MODE", "false").lower() == "true":
    # In production, also allow the current host
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8080))
    if host != "0.0.0.0":
        allowed_origins.append(f"https://{host}")
        allowed_origins.append(f"http://{host}")
        if port != 80 and port != 443:
            allowed_origins.append(f"https://{host}:{port}")
            allowed_origins.append(f"http://{host}:{port}")

print(f"🌐 CORS allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "X-CSRFToken"
    ],
    expose_headers=["*"]
)

# Include API routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(engineer.router, prefix="/api/engineer", tags=["Engineer"])
app.include_router(teams.router, prefix="/api/teams", tags=["Teams"])
app.include_router(data.router, prefix="/api/data", tags=["Data Management"])

# Serve Vue.js static files (for production)
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")
    
    @app.get("/")
    async def serve_frontend():
        """Serve the Vue.js frontend"""
        return FileResponse(frontend_dist / "index.html")
    
    @app.get("/{path:path}")
    async def serve_frontend_routes(path: str):
        """Handle Vue Router paths"""
        file_path = frontend_dist / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    settings = get_settings()
    
    # For development, allow running without S3 if DEVELOPMENT_MODE=true
    dev_mode = os.environ.get("DEVELOPMENT_MODE", "false").lower() == "true"
    
    if dev_mode:
        print("🔧 Running in DEVELOPMENT MODE - S3 checks disabled")
        print("⚠️  WARNING: This is for development only! Data will not persist.")
        return
    
    # Validate S3 configuration for production
    if not settings.use_s3:
        raise RuntimeError("S3 configuration required. Set USE_S3=true environment variable.")
    
    if not settings.s3_bucket_name:
        raise RuntimeError("S3 bucket name required. Set S3_BUCKET_NAME environment variable.")
    
    try:
        # Test S3 connection before initializing managers
        s3_client = boto3.client('s3')
        s3_client.head_bucket(Bucket=settings.s3_bucket_name)
        print(f"✅ Successfully connected to S3 bucket: {settings.s3_bucket_name}")
        
        # Initialize data managers
        init_data_managers(settings)
        print("✅ Data managers initialized successfully")
        
    except Exception as e:
        error_msg = f"Failed to initialize S3 connection: {str(e)}"
        print(f"❌ {error_msg}")
        raise RuntimeError(error_msg)

@app.get("/api/health")
async def health_check():
    """Health check endpoint for AWS AppRunner"""
    settings = get_settings()
    
    health_status = {
        "status": "healthy",
        "version": "2.0.0",
        "service": "Developer Efficiency Tracker API",
        "s3_configured": settings.use_s3 and bool(settings.s3_bucket_name),
        "s3_bucket": settings.s3_bucket_name if settings.use_s3 else None
    }
    
    # Test S3 connection
    if settings.use_s3 and settings.s3_bucket_name:
        try:
            s3_client = boto3.client('s3')
            s3_client.head_bucket(Bucket=settings.s3_bucket_name)
            health_status["s3_connection"] = "healthy"
        except Exception as e:
            health_status["s3_connection"] = f"error: {str(e)}"
            health_status["status"] = "degraded"
    else:
        health_status["s3_connection"] = "not_configured"
        health_status["status"] = "degraded"
    
    return health_status

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        reload=settings.debug
    ) 