"""FastAPI application for Podcast Downloader API."""

import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routers import episode, podcast

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="Podcast Downloader API",
    description="API for managing podcast episode processing",
    version="1.0.0"
)

# Configure CORS to allow all origins (for testing with public URLs)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(episode.router)
app.include_router(podcast.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Podcast Downloader API",
        "version": "1.0.0",
        "endpoints": {
            "rerun_summarize_post": "/api/episodes/rerun-summarize (POST with JSON body: {\"episode_id\": \"<episode_id>\"})",
            "rerun_summarize_get": "/api/episodes/rerun-summarize/{episode_id} (GET)",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health():
    """Global health check endpoint."""
    return {"status": "healthy"}
