"""
Automatic Video Summarization - REST API
=========================================
FastAPI-based REST API for video summarization.

Run with:
    python api.py

Or with uvicorn directly:
    uvicorn api:app --host 0.0.0.0 --port 8000 --reload

API Documentation:
    http://localhost:8000/docs (Swagger UI)
    http://localhost:8000/redoc (ReDoc)
"""

import os
import uuid
import time
import shutil
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional
from enum import Enum

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from summarize import summarize, get_video_info


# ==========================================
# Configuration
# ==========================================

PROJECT_DIR = Path(__file__).parent
API_OUTPUT_DIR = PROJECT_DIR / "outputs" / "_api_workspace"
API_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# In-memory job storage (use Redis/DB for production)
jobs: dict = {}


# ==========================================
# Models
# ==========================================

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SummarizeRequest(BaseModel):
    """Parameters for video summarization."""
    fps_sample: float = Field(default=4.0, ge=1.0, le=10.0, description="Analysis sampling rate (FPS)")
    threshold_percentile: float = Field(default=92, ge=50, le=99, description="Scene detection threshold")
    min_shot_duration: float = Field(default=3.0, ge=1.0, le=30.0, description="Minimum scene duration (seconds)")
    max_summary_duration: float = Field(default=60.0, ge=15.0, le=300.0, description="Maximum summary duration")
    secs_per_shot: float = Field(default=2.5, ge=1.0, le=10.0, description="Seconds per scene in summary")
    keep_audio: bool = Field(default=True, description="Preserve audio in summary")
    clean_input: bool = Field(default=False, description="Re-encode input to fix codec issues")
    best_keyframes: bool = Field(default=True, description="Select sharpest keyframes")
    transcribe: bool = Field(default=False, description="Generate transcript with Whisper")


class JobResponse(BaseModel):
    """Job creation response."""
    job_id: str
    status: JobStatus
    message: str
    created_at: str


class JobStatusResponse(BaseModel):
    """Job status response."""
    job_id: str
    status: JobStatus
    progress: Optional[float] = None
    message: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None


class VideoInfoResponse(BaseModel):
    """Video information response."""
    filename: str
    duration_sec: float
    duration_hms: str
    width: int
    height: int
    fps: float
    frame_count: int


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    uptime_sec: float
    ffmpeg_available: bool


# ==========================================
# App Initialization
# ==========================================

app = FastAPI(
    title="Video Summarizer API",
    description="Transform long videos into concise, engaging summaries with AI-powered scene detection",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Track startup time
START_TIME = time.time()


# ==========================================
# Helper Functions
# ==========================================

def check_ffmpeg() -> bool:
    """Check if ffmpeg is available."""
    return shutil.which("ffmpeg") is not None


def format_time(seconds: float) -> str:
    """Format seconds to HH:MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


async def process_video_task(
    job_id: str,
    video_path: Path,
    output_dir: Path,
    params: SummarizeRequest
):
    """Background task to process video."""
    try:
        jobs[job_id]["status"] = JobStatus.PROCESSING
        jobs[job_id]["message"] = "Processing video..."
        
        # Run summarization
        result = summarize(
            input_path=str(video_path),
            output_dir=str(output_dir),
            fps_sample=params.fps_sample,
            threshold_percentile=params.threshold_percentile,
            min_shot_duration=params.min_shot_duration,
            secs_per_shot=params.secs_per_shot,
            max_summary_duration=params.max_summary_duration,
            keep_audio=params.keep_audio and check_ffmpeg(),
            clean_input=params.clean_input,
            best_keyframes=params.best_keyframes,
            transcribe=params.transcribe,
        )
        
        # Update job with results
        jobs[job_id]["status"] = JobStatus.COMPLETED
        jobs[job_id]["completed_at"] = datetime.now().isoformat()
        jobs[job_id]["message"] = "Summarization complete"
        jobs[job_id]["result"] = {
            "manifest": result["manifest"],
            "files": {
                "summary_video": str(output_dir / "summary.mp4"),
                "storyboard": str(output_dir / "storyboard.png"),
                "analysis": str(output_dir / "analysis.png"),
                "manifest": str(output_dir / "summary.json"),
            },
            "elapsed_sec": result["elapsed_sec"],
        }
        
    except Exception as e:
        jobs[job_id]["status"] = JobStatus.FAILED
        jobs[job_id]["completed_at"] = datetime.now().isoformat()
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["message"] = f"Failed: {str(e)}"


# ==========================================
# API Endpoints
# ==========================================

@app.get("/", tags=["General"])
async def root():
    """API root - welcome message."""
    return {
        "name": "Video Summarizer API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        uptime_sec=round(time.time() - START_TIME, 2),
        ffmpeg_available=check_ffmpeg(),
    )


@app.post("/api/summarize", response_model=JobResponse, tags=["Summarization"])
async def create_summarization_job(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(..., description="Video file to summarize"),
    fps_sample: float = Query(default=4.0, ge=1.0, le=10.0),
    threshold_percentile: float = Query(default=92, ge=50, le=99),
    min_shot_duration: float = Query(default=3.0, ge=1.0, le=30.0),
    max_summary_duration: float = Query(default=60.0, ge=15.0, le=300.0),
    secs_per_shot: float = Query(default=2.5, ge=1.0, le=10.0),
    keep_audio: bool = Query(default=True),
    clean_input: bool = Query(default=False),
    best_keyframes: bool = Query(default=True),
    transcribe: bool = Query(default=False),
):
    """
    Upload a video and start summarization.
    
    Returns a job_id that can be used to check status and retrieve results.
    """
    # Validate file
    if not video.filename:
        raise HTTPException(status_code=400, detail="No video file provided")
    
    # Generate job ID
    job_id = str(uuid.uuid4())[:8]
    created_at = datetime.now().isoformat()
    
    # Create output directory
    output_dir = API_OUTPUT_DIR / job_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save uploaded video
    video_path = output_dir / "input.mp4"
    try:
        with open(video_path, "wb") as f:
            content = await video.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save video: {e}")
    
    # Create job record
    params = SummarizeRequest(
        fps_sample=fps_sample,
        threshold_percentile=threshold_percentile,
        min_shot_duration=min_shot_duration,
        max_summary_duration=max_summary_duration,
        secs_per_shot=secs_per_shot,
        keep_audio=keep_audio,
        clean_input=clean_input,
        best_keyframes=best_keyframes,
        transcribe=transcribe,
    )
    
    jobs[job_id] = {
        "status": JobStatus.PENDING,
        "created_at": created_at,
        "message": "Job queued for processing",
        "video_path": str(video_path),
        "output_dir": str(output_dir),
        "params": params.model_dump(),
    }
    
    # Start background processing
    background_tasks.add_task(
        process_video_task,
        job_id,
        video_path,
        output_dir,
        params,
    )
    
    return JobResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        message="Video uploaded. Summarization started.",
        created_at=created_at,
    )


@app.get("/api/status/{job_id}", response_model=JobStatusResponse, tags=["Summarization"])
async def get_job_status(job_id: str):
    """Get the status of a summarization job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job = jobs[job_id]
    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        message=job.get("message"),
        created_at=job["created_at"],
        completed_at=job.get("completed_at"),
        result=job.get("result"),
        error=job.get("error"),
    )


@app.get("/api/result/{job_id}/video", tags=["Results"])
async def download_summary_video(job_id: str):
    """Download the summary video for a completed job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job = jobs[job_id]
    if job["status"] != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail=f"Job is not complete. Status: {job['status']}")
    
    video_path = Path(job["result"]["files"]["summary_video"])
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Summary video not found")
    
    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=f"summary_{job_id}.mp4",
    )


@app.get("/api/result/{job_id}/storyboard", tags=["Results"])
async def download_storyboard(job_id: str):
    """Download the storyboard image for a completed job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job = jobs[job_id]
    if job["status"] != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail=f"Job is not complete. Status: {job['status']}")
    
    storyboard_path = Path(job["result"]["files"]["storyboard"])
    if not storyboard_path.exists():
        raise HTTPException(status_code=404, detail="Storyboard not found")
    
    return FileResponse(
        storyboard_path,
        media_type="image/png",
        filename=f"storyboard_{job_id}.png",
    )


@app.get("/api/result/{job_id}/manifest", tags=["Results"])
async def get_manifest(job_id: str):
    """Get the JSON manifest for a completed job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job = jobs[job_id]
    if job["status"] != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail=f"Job is not complete. Status: {job['status']}")
    
    return JSONResponse(content=job["result"]["manifest"])


@app.post("/api/analyze", response_model=VideoInfoResponse, tags=["Utilities"])
async def analyze_video(video: UploadFile = File(..., description="Video file to analyze")):
    """
    Analyze a video file and return its metadata.
    
    This is a quick operation that doesn't start summarization.
    """
    if not video.filename:
        raise HTTPException(status_code=400, detail="No video file provided")
    
    # Save to temp location
    temp_dir = API_OUTPUT_DIR / "_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"analyze_{uuid.uuid4().hex[:8]}.mp4"
    
    try:
        with open(temp_path, "wb") as f:
            content = await video.read()
            f.write(content)
        
        info = get_video_info(str(temp_path))
        
        return VideoInfoResponse(
            filename=video.filename,
            duration_sec=round(info["duration_sec"], 2),
            duration_hms=format_time(info["duration_sec"]),
            width=info["width"],
            height=info["height"],
            fps=round(info["fps"], 2),
            frame_count=info["frame_count"],
        )
    finally:
        # Cleanup temp file
        if temp_path.exists():
            temp_path.unlink()


@app.delete("/api/jobs/{job_id}", tags=["Summarization"])
async def delete_job(job_id: str):
    """Delete a job and its output files."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job = jobs[job_id]
    
    # Delete output directory
    output_dir = Path(job["output_dir"])
    if output_dir.exists():
        shutil.rmtree(output_dir)
    
    # Remove from jobs dict
    del jobs[job_id]
    
    return {"message": f"Job {job_id} deleted"}


@app.get("/api/jobs", tags=["Summarization"])
async def list_jobs(
    status: Optional[JobStatus] = Query(default=None, description="Filter by status"),
    limit: int = Query(default=20, ge=1, le=100),
):
    """List all jobs, optionally filtered by status."""
    result = []
    for job_id, job in list(jobs.items())[-limit:]:
        if status is None or job["status"] == status:
            result.append({
                "job_id": job_id,
                "status": job["status"],
                "created_at": job["created_at"],
                "completed_at": job.get("completed_at"),
            })
    return result


# ==========================================
# Main Entry Point
# ==========================================

def main():
    """Launch the FastAPI server."""
    import uvicorn
    
    print("\n" + "=" * 60)
    print("   VIDEO SUMMARIZER - REST API")
    print("=" * 60)
    print("\n📡 Starting API server...")
    print("   Swagger UI: http://localhost:8000/docs")
    print("   ReDoc:      http://localhost:8000/redoc")
    print("   Health:     http://localhost:8000/health\n")
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
