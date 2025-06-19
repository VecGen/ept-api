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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    init_data_managers(settings)

@app.get("/api/health")
async def health_check():
    """Health check endpoint for AWS AppRunner"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "service": "Developer Efficiency Tracker API"
    }

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        reload=settings.debug
    ) 