"""Pipeline Jobs & Background Task Queue Router.

Provides endpoints to submit, monitor, and cancel long-running surveillance tasks,
including Engine v2 video forensic runs, 30-day batch orchestration, and vector indexing.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.services.background_worker import BackgroundWorkerManager, TaskStatus, TaskType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pipeline", tags=["Pipeline Background Tasks"])


class JobSubmitRequest(BaseModel):
    task_type: str = Field(..., description="Task type (ENGINE_V2_DAY_RUN, ORCHESTRATE_30DAY, REINDEX_CENTROIDS, CUSTOM_SCRIPT)")
    title: Optional[str] = Field(None, description="Human-readable title for the task")
    day: Optional[int] = Field(None, description="Target CCTV day index (e.g. 25)")
    skip_completed: Optional[bool] = Field(True, description="Skip already processed days/chunks")
    workers: Optional[int] = Field(4, description="Parallel worker count for batch jobs")
    params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional arbitrary parameters")


class JobResponse(BaseModel):
    task_id: str
    title: str
    task_type: str
    status: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress_pct: float = 0.0
    current_step: str
    metrics: Dict[str, Any] = Field(default_factory=dict)
    log_tail: List[str] = Field(default_factory=list)
    error: Optional[str] = None
    pid: Optional[int] = None


class JobStatsResponse(BaseModel):
    total_jobs: int
    running_jobs: int
    queued_jobs: int
    completed_jobs: int
    failed_jobs: int
    cancelled_jobs: int


@router.post("/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def submit_pipeline_job(request: JobSubmitRequest):
    """Enqueue a new surveillance processing job to the decoupled worker queue."""
    manager = BackgroundWorkerManager.get_instance()
    
    # Merge explicit fields into params dict
    merged_params = dict(request.params)
    if request.day is not None:
        merged_params["day"] = request.day
    if request.skip_completed is not None:
        merged_params["skip_completed"] = request.skip_completed
    if request.workers is not None:
        merged_params["workers"] = request.workers

    title = request.title
    if not title:
        if request.task_type == TaskType.ENGINE_V2_DAY_RUN:
            title = f"Engine v2 HOI Forensic Analysis - Day {request.day or 25}"
        elif request.task_type == TaskType.ORCHESTRATE_30DAY:
            title = "30-Day Master Surveillance Orchestrator Batch"
        elif request.task_type == TaskType.REINDEX_CENTROIDS:
            title = "Biometric Centroid & Embedding Reindex"
        else:
            title = f"Pipeline Task: {request.task_type}"

    task = manager.enqueue_task(
        task_type=request.task_type,
        title=title,
        params=merged_params,
    )
    return task


@router.get("/jobs", response_model=List[JobResponse])
def list_pipeline_jobs(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED)"),
    limit: int = Query(50, ge=1, le=200, description="Max jobs to return")
):
    """List recent and active background pipeline jobs."""
    manager = BackgroundWorkerManager.get_instance()
    clean_status = status_filter.strip().upper() if isinstance(status_filter, str) and status_filter.strip() else None
    return manager.list_tasks(status=clean_status, limit=limit)


@router.get("/jobs/stats", response_model=JobStatsResponse)
def get_pipeline_job_stats():
    """Get high-level statistics for all queue workers and execution states."""
    manager = BackgroundWorkerManager.get_instance()
    all_tasks = manager.list_tasks(limit=1000)
    
    return JobStatsResponse(
        total_jobs=len(all_tasks),
        running_jobs=sum(1 for t in all_tasks if t.get("status") == TaskStatus.RUNNING),
        queued_jobs=sum(1 for t in all_tasks if t.get("status") == TaskStatus.QUEUED),
        completed_jobs=sum(1 for t in all_tasks if t.get("status") == TaskStatus.COMPLETED),
        failed_jobs=sum(1 for t in all_tasks if t.get("status") == TaskStatus.FAILED),
        cancelled_jobs=sum(1 for t in all_tasks if t.get("status") == TaskStatus.CANCELLED),
    )


@router.get("/jobs/{task_id}", response_model=JobResponse)
def get_pipeline_job(task_id: str):
    """Retrieve detailed telemetry and live log output for a specific job."""
    manager = BackgroundWorkerManager.get_instance()
    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Pipeline task '{task_id}' not found")
    return task


@router.post("/jobs/{task_id}/cancel")
def cancel_pipeline_job(task_id: str):
    """Request immediate cancellation and process termination for a job."""
    manager = BackgroundWorkerManager.get_instance()
    success = manager.cancel_task(task_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Task '{task_id}' could not be cancelled (might not exist or is already completed/failed)"
        )
    return {"status": "cancelled", "task_id": task_id}


@router.post("/jobs/clear-finished")
def clear_finished_jobs():
    """Purge completed, failed, and cancelled tasks from queue history."""
    manager = BackgroundWorkerManager.get_instance()
    cleared_count = manager.clear_finished()
    return {"status": "cleared", "count": cleared_count}
