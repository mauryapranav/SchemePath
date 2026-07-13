from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.models import HealthResponse
from app.neo4j_client import close_driver, init_driver, verify_connectivity
from app.routers import chat, profile, eligibility, questions, scheme

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage startup and shutdown tasks."""
    # We use this lifespan manager to establish our database connection right when 
    # the server boots up, so it's ready before any user requests come in.
    # ── Startup ──────────────────────────────────────────────────────────
    logger.info("Starting up SchemePath backend…")

    init_driver()
    connected = await verify_connectivity()

    if not connected:
        logger.warning(
            "⚠️  Could not reach Neo4j on startup. "
            "The app will still start but graph features will be unavailable."
        )
    else:
        logger.info("✅ Neo4j connection verified.")

    yield  # application runs here

    # ── Shutdown ─────────────────────────────────────────────────────────
    logger.info("Shutting down SchemePath backend…")
    await close_driver()


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

# We define the core FastAPI application here, injecting our lifespan manager
# so the database driver starts and stops perfectly in sync with the web server.
app = FastAPI(
    title="SchemePath API",
    description="Backend API for the SchemePath learning-graph platform.",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS (permissive for hackathon demo) ────────────────────────────────────
# We configure permissive CORS here so that our Next.js frontend can talk to 
# this API from localhost or any deployed Vercel domain during the hackathon demo.
# In a real production setting, we'd lock this down to specific domains for security.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Global Exception Handlers
# ---------------------------------------------------------------------------

@app.exception_handler(404)
async def custom_404_handler(request: Request, exc: HTTPException):
    # We use this to provide a consistent JSON error format when someone requests
    # an endpoint or resource that doesn't exist, rather than a raw HTML page.
    return JSONResponse(
        status_code=404,
        content={"detail": "The requested resource was not found on this server."}
    )

@app.exception_handler(500)
async def custom_500_handler(request: Request, exc: Exception):
    # We catch unhandled errors here to ensure we always return a friendly JSON response
    # instead of crashing and exposing internal stack traces to the end user.
    logger.error(f"Internal Server Error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. We're looking into it."}
    )

# ---------------------------------------------------------------------------
# Router Registration
# ---------------------------------------------------------------------------

# We register our feature-specific routers here to keep main.py clean and organized.
# This makes it easy to find where all the business logic lives.
app.include_router(chat.router)
app.include_router(profile.router)
app.include_router(eligibility.router)
app.include_router(questions.router)
app.include_router(scheme.router)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["Meta"],
)
async def health_check() -> HealthResponse:
    """Return service health and Neo4j connectivity status."""
    neo4j_ok = await verify_connectivity()
    return HealthResponse(status="ok", neo4j_connected=neo4j_ok)
