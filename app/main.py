import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from app.config import settings
from app.api import api_router
from app.seed_data import seed_all
from app.auth.migrate_users import migrate_users_table
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("shopmate.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Run auth migration, seed database and build initial RAG indices
    logger.info("Initializing ShopMate AI Engine...")
    try:
        migrate_users_table()
        seed_all()
    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
    yield
    # Shutdown
    logger.info("Shutting down ShopMate AI...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Enterprise-grade Agentic Retail Assistant featuring LangGraph, Hybrid RAG, ChromaDB, and Multi-Agent Orchestration",
    lifespan=lifespan
)

# CORS middleware configured for production (supporting React / Next.js frontends)
raw_origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
cors_origins = ["*"] if "*" in raw_origins else raw_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# Mount Static UI Files
static_dir = settings.BASE_DIR / "static"
static_dir.mkdir(parents=True, exist_ok=True)
(static_dir / "css").mkdir(parents=True, exist_ok=True)
(static_dir / "js").mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/")
async def serve_spa():
    """Serves the Single-Page Dark Glassmorphism Web App."""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse({
        "status": "online",
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs_url": "/docs",
        "api_v1": settings.API_V1_STR
    })

@app.get("/login")
async def serve_login():
    """Serves the dedicated Sign In / Sign Up Webpage."""
    login_path = static_dir / "login.html"
    if login_path.exists():
        return FileResponse(str(login_path))
    return FileResponse(str(static_dir / "index.html"))

@app.get("/signup")
async def serve_signup():
    """Serves the Sign Up page."""
    login_path = static_dir / "login.html"
    if login_path.exists():
        return FileResponse(str(login_path))
    return FileResponse(str(static_dir / "index.html"))

@app.get("/dashboard")
@app.get("/admin")
@app.get("/support")
async def serve_role_dashboard():
    """Serves role-specific dashboard views handled by the SPA."""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return FileResponse(str(static_dir / "login.html"))

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "project": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "port": settings.PORT
    }
