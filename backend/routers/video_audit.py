"""CCTV Video Integrity & Batch Ingestion Router.

Provides API endpoints for:
1. Scanning offline/hard-disk CCTV footage for missing intervals, gaps, and trimmed clips.
2. Generating security timeline continuity reports and chain-of-custody manifests.
3. Initiating fast batch face recognition ingestion on offline footage.
4. Monitoring live ingestion progress.
"""

from __future__ import annotations

import logging
import os
import re
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
import models
from schemas import ImportBatchResponse
from facial_recognition.batch_video_ingest import get_global_ingest_engine, IngestionProgress
from facial_recognition.video_auditor import VideoAuditor, VideoAuditReport

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/video-audit", tags=["Video Audit & Ingestion"])

# Cache for latest audit report in memory
_latest_audit_report: Optional[Dict[str, Any]] = None
_audit_lock = threading.Lock()
_ingestion_thread: Optional[threading.Thread] = None


def resolve_directory_path(dir_str: str) -> Path:
    """Resolve a directory path, translating Windows drive letters if running in a Linux/Docker environment."""
    raw = str(dir_str or "").strip().strip('"').strip("'").strip()
    p = Path(raw)
    if p.exists():
        return p.resolve()

    # Translate Windows drive letter paths on Linux/Docker (e.g. D:\DBGT POC -> /d/DBGT POC)
    clean = raw.replace("\\", "/")
    m = re.match(r"^([a-zA-Z]):[/\\]?(.*)", clean)
    if m:
        drive = m.group(1).lower()
        sub = m.group(2).strip("/")
        candidates = [
            Path(f"/{drive}/{sub}" if sub else f"/{drive}"),
            Path(f"/mnt/{drive}/{sub}" if sub else f"/mnt/{drive}"),
            Path(f"/media/{drive}/{sub}" if sub else f"/media/{drive}"),
            Path(f"/host/{drive}/{sub}" if sub else f"/host/{drive}"),
        ]
        for c in candidates:
            if c.exists():
                return c.resolve()

    # If HOST_FOOTAGE_DIR is mounted to /footage, check if path matches it
    host_footage = os.environ.get("HOST_FOOTAGE_DIR", "").replace("\\", "/").strip().rstrip("/")
    if host_footage:
        if clean.lower() == host_footage.lower() or clean.lower() == Path(host_footage).name.lower():
            if Path("/footage").exists():
                return Path("/footage").resolve()
        if clean.lower().startswith(host_footage.lower() + "/"):
            sub_rel = clean[len(host_footage) + 1:]
            c = Path("/footage") / sub_rel
            if c.exists():
                return c.resolve()

    return p.resolve()


def allowed_footage_roots() -> List[Path]:
    """Folders the footage tools may read: FOOTAGE_ROOTS (separated by ; or ,), default /footage."""
    raw = os.environ.get("FOOTAGE_ROOTS", "").strip()
    items = [part.strip() for part in re.split(r"[;,]", raw) if part.strip()] if raw else ["/footage", "/app/data"]
    # Auto-add available drive mounts
    for auto_dir in [
        "/d", "/e", "/f", "/g",
        "/c/Users", "/c",
        "/mnt/d", "/mnt/e", "/mnt/f", "/mnt/g", "/mnt/c",
        "/footage", "/app/data",
    ]:
        try:
            if Path(auto_dir).exists() and auto_dir not in items:
                items.append(auto_dir)
        except OSError:
            # Dead mount point (e.g. disconnected USB drive) — skip silently
            continue
    roots: List[Path] = []
    for item in items:
        try:
            resolved = resolve_directory_path(item)
            if resolved.exists() and resolved not in roots:
                roots.append(resolved)
        except OSError:
            continue
    return roots


def ensure_within_roots(path: Path) -> Path:
    """Return the resolved path if it is inside an allowed footage folder, otherwise raise 403.

    Symlinks and ".." are resolved first, so they cannot be used to step outside the allowed folders.
    """
    resolved = path.resolve()
    for root in allowed_footage_roots():
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Path is outside the allowed footage folders. Set FOOTAGE_ROOTS to the folder(s) holding your footage.",
    )


class ScanRequest(BaseModel):
    directory: str = Field(..., description="Absolute path to CCTV footage directory or hard drive")
    tolerance_seconds: float = Field(5.0, description="Allowable gap in seconds before flagging as missing footage")
    compute_hashes: bool = Field(True, description="Whether to compute SHA-256 for chain of custody")


class IngestRequest(BaseModel):
    directory: str = Field(..., description="Absolute path to CCTV footage directory or hard drive")
    sample_fps: float = Field(3.0, description="Frames per second to sample (default: 3.0 FPS for fast 10-15x scan)")
    threshold: float = Field(0.60, description="Face recognition confidence threshold")
    use_gpu: bool = Field(False, description="Enable GPU acceleration if available")
    batch_name: Optional[str] = Field(None, description="Optional descriptive label for this import batch")
    enable_motion_gating: bool = Field(True, description="Skip static night/empty scenes for 3x speedup while preserving detections")
    max_workers: Optional[int] = Field(None, description="Max parallel camera workers (None = auto-scale based on free VRAM)")
    live_reserve_mb: int = Field(6144, description="VRAM in MB reserved exclusively for concurrent live surveillance")
    scenario: Optional[str] = Field("auto", description="Operational scenario preset (e.g. wide_perimeter, auto, office_desk)")


@router.get("/browse", response_model=Dict[str, Any])
def browse_directories(path: Optional[str] = Query(None, description="Path to inspect")):
    """
    List available drives or subdirectories containing video footage.
    Allows dashboard users to visually select CCTV folders without typing absolute paths.
    """
    results = []
    current_path = ""
    parent_path = None

    roots = allowed_footage_roots()
    if not path or not path.strip():
        for root in roots:
            drive_match = re.match(r"^/([a-zA-Z])$", str(root))
            display_name = f"{drive_match.group(1).upper()}:\\" if drive_match else (root.name or str(root))
            display_path = f"{drive_match.group(1).upper()}:\\" if drive_match else str(root)
            results.append({"name": display_name, "path": display_path, "is_drive": True, "has_videos": False})
    else:
        resolved = ensure_within_roots(resolve_directory_path(path))
        if not resolved.exists() or not resolved.is_dir():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Directory not found: {path}")

        current_path = str(resolved)
        parent_path = str(resolved.parent) if (resolved not in roots and resolved.parent != resolved) else None

        VIDEO_EXTS = {".mp4", ".avi", ".mkv", ".mov", ".flv", ".wmv", ".ts", ".webm"}
        try:
            for item in sorted(resolved.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                if item.name.startswith(".") or item.name.startswith("$") or "System Volume Information" in item.name:
                    continue
                if item.is_dir():
                    has_vids = False
                    try:
                        for sub in item.iterdir():
                            if sub.suffix.lower() in VIDEO_EXTS:
                                has_vids = True
                                break
                    except Exception:
                        pass

                    display_path = str(item)
                    m = re.match(r"^/([a-zA-Z])/(.*)", str(item))
                    if m:
                        sub_win = m.group(2).replace('/', '\\')
                        display_path = f"{m.group(1).upper()}:\\{sub_win}"

                    results.append({
                        "name": item.name,
                        "path": display_path,
                        "is_dir": True,
                        "has_videos": has_vids,
                    })
        except Exception as exc:
            logger.warning("Error reading directory %s: %s", resolved, exc)

    return {
        "current_path": current_path,
        "parent_path": parent_path,
        "items": results,
    }


@router.get("/locate", response_model=Dict[str, Any])
def locate_folder(name: str = Query(..., description="Folder name to search for")):
    """Locate a folder name across available drives to auto-complete folder selections."""
    name_clean = name.strip().strip("/\\")
    candidates = []
    for root in allowed_footage_roots():
        try:
            match = (root / name_clean).resolve()
            match.relative_to(root)   # reject ".." escapes
        except (ValueError, OSError):
            continue
        if match.is_dir():
            display_path = str(match)
            m = re.match(r"^/([a-zA-Z])/(.*)", str(match))
            if m:
                sub_win = m.group(2).replace('/', '\\')
                display_path = f"{m.group(1).upper()}:\\{sub_win}"
            candidates.append(display_path)

    # Also check /footage directly if name matches HOST_FOOTAGE_DIR or contains videos
    host_footage = os.environ.get("HOST_FOOTAGE_DIR", "")
    if host_footage and Path(host_footage).name.lower() == name_clean.lower():
        if host_footage not in candidates:
            candidates.insert(0, host_footage)

    return {
        "name": name,
        "found": len(candidates) > 0,
        "path": candidates[0] if candidates else None,
        "all_matches": candidates,
    }


@router.post("/scan", response_model=Dict[str, Any])
def scan_cctv_footage(req: ScanRequest):
    """
    Perform deep timeline continuity & tamper analysis on CCTV directory.
    Identifies missing time clips, abnormally trimmed videos, and computes SHA-256 hashes.
    """
    global _latest_audit_report
    # Protect against raw root directory scan DoS
    raw_str = (req.directory or "").strip().strip('"').strip("'").strip().rstrip("/\\")
    if not raw_str or (len(raw_str) <= 3 and ":" in raw_str) or raw_str in ["/", "/d", "/c", "/mnt", "/app"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scanning raw drive root is restricted for security. Please specify a CCTV folder path.",
        )

    target_path = resolve_directory_path(raw_str)
    root_str = str(target_path).strip().rstrip("/\\")
    if not root_str or (len(root_str) <= 3 and ":" in root_str) or root_str in ["/", "/d", "/c", "/mnt", "/app"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scanning raw drive root is restricted for security. Please specify a CCTV folder path.",
        )

    target_path = ensure_within_roots(target_path)

    if not target_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Directory does not exist: {req.directory}. Ensure the footage folder exists or is mounted.",
        )

    try:
        auditor = VideoAuditor(
            tolerance_seconds=req.tolerance_seconds,
            compute_full_hashes=req.compute_hashes,
        )
        if target_path.is_file():
            report = auditor.scan_file(target_path)
        else:
            report = auditor.scan_directory(target_path)

        report_dict = asdict(report)
        # Preserve the friendly path format requested by the user
        report_dict["root_directory"] = req.directory

        with _audit_lock:
            _latest_audit_report = report_dict

        return report_dict
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Footage folder not found: {str(exc)}")
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error scanning CCTV footage: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audit scan failed: {str(exc)}",
        )


@router.get("/latest-report", response_model=Optional[Dict[str, Any]])
def get_latest_audit_report():
    """Retrieve the latest cached CCTV security audit report."""
    with _audit_lock:
        if _latest_audit_report is None:
            return None
        return _latest_audit_report


@router.post("/ingest", response_model=Dict[str, Any])
def start_batch_ingest(req: IngestRequest):
    """
    Start standalone fast batch video ingestion in a background thread.
    Processes video clips chronologically, computes exact recorded timestamps,
    and populates detections, alerts, and demographics into the database.
    """
    global _ingestion_thread
    # Protect against raw root directory scan DoS
    raw_str = (req.directory or "").strip().strip('"').strip("'").strip().rstrip("/\\")
    if not raw_str or (len(raw_str) <= 3 and ":" in raw_str) or raw_str in ["/", "/d", "/c", "/mnt", "/app"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ingesting raw drive root is restricted for security. Please specify a CCTV folder path.",
        )

    target_path = resolve_directory_path(raw_str)
    root_str = str(target_path).strip().rstrip("/\\")
    if not root_str or (len(root_str) <= 3 and ":" in root_str) or root_str in ["/", "/d", "/c", "/mnt", "/app"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ingesting raw drive root is restricted for security. Please specify a CCTV folder path.",
        )

    target_path = ensure_within_roots(target_path)

    if not target_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Directory does not exist: {req.directory}. Ensure the footage folder exists or is mounted.",
        )

    engine = get_global_ingest_engine()
    if engine.progress.running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Batch video ingestion is already currently running.",
        )

    # Configure engine
    engine.progress.error = None
    engine.progress.completed = False
    engine.sample_fps = max(0.5, float(req.sample_fps))
    engine.progress.sample_fps = engine.sample_fps
    engine.threshold = req.threshold
    engine.use_gpu = req.use_gpu
    engine.progress.device = "gpu" if req.use_gpu else "cpu"
    engine.progress.cpu_cores = os.cpu_count() or 4
    engine.enable_motion_gating = req.enable_motion_gating
    engine.max_workers = req.max_workers
    engine.live_reserve_mb = req.live_reserve_mb
    engine.scenario = req.scenario or "auto"
    engine.progress.scenario = engine.scenario

    def _worker():
        try:
            logger.info("Starting background batch ingestion on %s (motion_gating=%s, max_workers=%s)...",
                        target_path, req.enable_motion_gating, req.max_workers)
            engine.ingest_directory(target_path, batch_name=req.batch_name)
            logger.info("Background batch ingestion completed.")
        except Exception as exc:
            logger.exception("Background ingestion worker failed: %s", exc)

    _ingestion_thread = threading.Thread(target=_worker, daemon=True)
    _ingestion_thread.start()

    return {
        "status": "started",
        "directory": str(req.directory),
        "sample_fps": req.sample_fps,
        "threshold": req.threshold,
        "batch_name": req.batch_name,
        "enable_motion_gating": req.enable_motion_gating,
        "max_workers": req.max_workers,
    }


@router.get("/status", response_model=Dict[str, Any])
def get_ingest_status():
    """Get live batch ingestion progress, processing speed, ETA, and detection counts."""
    engine = get_global_ingest_engine()
    p: IngestionProgress = engine.progress
    return asdict(p)


@router.get("/gpu-status", response_model=Dict[str, Any])
def get_gpu_status():
    """Get real-time GPU VRAM or CPU telemetry and recommended parallel worker count."""
    from facial_recognition.batch_video_ingest import VRAMScheduler
    vram = VRAMScheduler.get_vram_info()
    has_gpu = vram.get("total_mb", 0) > 0
    workers, meta = VRAMScheduler.calculate_safe_workers(camera_count=5, live_reserve_mb=6144 if has_gpu else 0)
    return {
        "vram_info": vram,
        "device": "gpu" if has_gpu else "cpu",
        "gpu_name": vram.get("device_name", "NVIDIA GPU") if has_gpu else "Host CPU",
        "cpu_cores": os.cpu_count() or 4,
        "safe_workers_recommended": workers,
        "live_reserve_mb": 6144 if has_gpu else 0,
        "autoscaler_meta": meta,
    }


@router.post("/stop", response_model=Dict[str, Any])
def stop_batch_ingest():
    """Gracefully cancel the running batch ingestion worker."""
    engine = get_global_ingest_engine()
    if not engine.progress.running:
        return {"status": "not_running"}

    engine.stop()
    return {"status": "stopping"}


@router.get("/batches", response_model=List[ImportBatchResponse])
def list_import_batches(db: Session = Depends(get_db)):
    """List all CCTV import batches."""
    batches = db.query(models.ImportBatch).order_by(models.ImportBatch.created_at.desc()).all()
    return batches


@router.delete("/batches/{batch_id}", response_model=Dict[str, Any])
def purge_import_batch(batch_id: str, db: Session = Depends(get_db)):
    """
    Atomically purge an imported CCTV dataset from the system.
    Deletes all detections and alerts associated with this batch_id without touching live data.
    """
    batch = db.query(models.ImportBatch).filter(models.ImportBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Import batch '{batch_id}' not found.",
        )

    # Count deleted records
    deleted_alerts = db.query(models.Alert).filter(models.Alert.batch_id == batch_id).delete(synchronize_session=False)
    deleted_detections = db.query(models.Detection).filter(models.Detection.batch_id == batch_id).delete(synchronize_session=False)

    db.delete(batch)
    db.commit()

    logger.info("Purged batch %s: %d detections, %d alerts deleted.", batch_id, deleted_detections, deleted_alerts)

    return {
        "status": "purged",
        "batch_id": batch_id,
        "deleted_detections": deleted_detections,
        "deleted_alerts": deleted_alerts,
    }

