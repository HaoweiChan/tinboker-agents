"""Router for podcast-specific episode processing endpoints."""

import asyncio
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks, Security
from pydantic import BaseModel
from src.auth import verify_api_key
from src.job_tracker import create_job, update_job
from src.routers.episode import run_episode_rerun

router = APIRouter(prefix="/api/podcast", tags=["podcast"])


class EpisodeRegenerateResponse(BaseModel):
    """Response model for episode regeneration."""
    message: str
    episode_id: str
    podcast_name: str
    status: str


@router.post("/{podcast_name}/episodes/{episode_id}/regenerate", response_model=EpisodeRegenerateResponse)
async def regenerate_episode(
    podcast_name: str,
    episode_id: str,
    background_tasks: BackgroundTasks,
    api_key: str = Security(verify_api_key)
):
    """
    Regenerate (rerun summarize) for a specific episode.
    
    This endpoint accepts a podcast name and episode ID and runs the command:
    python main.py --rerun-from summarize --episode <episode_id>
    
    The podcast_name parameter is included in the URL for organization but
    the actual processing uses only the episode_id.
    
    Args:
        podcast_name: The podcast name (URL-encoded, e.g., 財經一路發)
        episode_id: The episode ID to process
        background_tasks: FastAPI background tasks
        
    Returns:
        Response indicating the job has been started
    """
    if not episode_id or not episode_id.strip():
        raise HTTPException(status_code=400, detail="episode_id is required")
    
    if not podcast_name or not podcast_name.strip():
        raise HTTPException(status_code=400, detail="podcast_name is required")
    
    # Get project root (assuming this file is in src/routers)
    project_root = Path(__file__).parent.parent.parent
    
    # Add the background task (same function as rerun-summarize)
    background_tasks.add_task(run_episode_rerun, episode_id, project_root)
    
    return EpisodeRegenerateResponse(
        message=f"Episode regeneration job started for episode_id: {episode_id}",
        episode_id=episode_id,
        podcast_name=podcast_name,
        status="started"
    )
