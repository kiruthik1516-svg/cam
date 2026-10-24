
from fastapi import APIRouter, BackgroundTasks, File, UploadFile, Form, Depends, Query, HTTPException, Request, Response
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, text, case, select, or_
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
import uuid
import json

from database import get_db, check_database_health
from models import *
from models import ModelThreshold as DBModelThreshold
from schemas import *
from config import settings, IST
from dependencies import verify_edge_node
from auth import CurrentUser, require_admin, log_audit
from state import active_version_bundle, node_health_store, streaming_camera_ids
from utils import live_camera_ids, archive_camera_ids
from websocket import manager

router = APIRouter(tags=['System'])



# ==================== Health & Readiness Probes ====================

@router.get("/health")
def health_check(
    deep: bool = Query(False, description="Perform deep probe of database and Redis subsystems"),
    response: Response = None,
):
    """Health check endpoint with optional deep readiness probe."""
    now_iso = datetime.now(IST).isoformat()
    if not deep:
        return {"status": "ok", "timestamp": now_iso}

    db_healthy = check_database_health()
    redis_status = "disabled"
    if settings.redis_url:
        redis_status = "connected" if (manager.redis is not None) else "disconnected"

    subsystems = {
        "database": "healthy" if db_healthy else "unhealthy",
        "redis": redis_status,
        "websocket_active_channels": {k: len(v) for k, v in manager.active_connections.items()},
    }

    overall_status = "ok" if db_healthy else "degraded"
    payload = {
        "status": overall_status,
        "subsystems": subsystems,
        "timestamp": now_iso,
    }
    if not db_healthy and response is not None:
        response.status_code = 503
    return payload


@router.get("/health/ready")
def readiness_check(response: Response):
    """Container / Cloud orchestrator readiness probe."""
    return health_check(deep=True, response=response)





# ==================== KPI Endpoints ====================

@router.get("/api/kpis", response_model=SystemKpisResponse)
def get_kpis(
    source: Optional[str] = Query(None, description="Filter by data source: 'live' or 'archive'"),
    batch_id: Optional[str] = Query(None, description="Filter by specific archive batch ID"),
    db: Session = Depends(get_db)
):
    """Get system KPIs, optionally filtered by source or batch."""
    today = datetime.now(IST).date()
    
    det_q = db.query(Detection)
    alert_q = db.query(Alert)
    
    if source:
        det_q = det_q.filter(Detection.source == source)
        alert_q = alert_q.filter(Alert.source == source)
    if batch_id:
        det_q = det_q.filter(Detection.batch_id == batch_id)
        alert_q = alert_q.filter(Alert.batch_id == batch_id)
        
    total_detections = det_q.with_entities(func.count(Detection.id)).scalar() or 0
    unique_profiles = det_q.with_entities(func.count(func.distinct(Detection.profile_id))).scalar() or 0
    total_profiles = db.query(func.count(Profile.id)).scalar() or 0
    if source == "archive":
        # Imported footage: cameras are those that appear in the (selected) archive data.
        total_cameras = len(archive_camera_ids(db, batch_id))
        connected_cameras = total_cameras
        system_health = "green"
    else:
        # Live: a camera is connected while it keeps pushing frames.
        live_ids = live_camera_ids(db)
        total_cameras = len(live_ids)
        connected_cameras = len(live_ids & streaming_camera_ids())
        if total_cameras == 0:
            system_health = "yellow"
        elif connected_cameras == total_cameras:
            system_health = "green"
        elif connected_cameras > 0:
            system_health = "yellow"
        else:
            system_health = "yellow"
    cameras_online = connected_cameras
    active_alerts = alert_q.filter(
        Alert.acknowledged == False
    ).with_entities(func.count(Alert.id)).scalar() or 0
    critical_alerts = alert_q.filter(
        Alert.severity == "critical",
        Alert.acknowledged == False
    ).with_entities(func.count(Alert.id)).scalar() or 0
    
    # Today's stats evaluated against local day start
    today_start_ist = datetime.combine(today, datetime.min.time()).replace(tzinfo=IST)
    
    recognitions_today = det_q.filter(
        Detection.timestamp >= today_start_ist,
        Detection.status == DetectionStatus.recognized
    ).with_entities(func.count(Detection.id)).scalar() or 0
    unknowns_today = det_q.filter(
        Detection.timestamp >= today_start_ist,
        Detection.status == DetectionStatus.unknown
    ).with_entities(func.count(Detection.id)).scalar() or 0
    
    # Average confidence
    avg_confidence = det_q.filter(
        Detection.confidence > 0
    ).with_entities(func.avg(Detection.confidence)).scalar() or 0.0
    
    # The dashboard header shows "detections today" for live data and the batch total for archives
    # (archive data is dated in the past, so "today" would always be zero).
    if source == "archive":
        detections_today = total_detections
    else:
        detections_today = det_q.filter(
            Detection.timestamp >= today_start_ist
        ).with_entities(func.count(Detection.id)).scalar() or 0

    return SystemKpisResponse(
        total_detections=total_detections,
        unique_individuals=unique_profiles or 0,
        total_profiles=total_profiles,
        cameras_online=cameras_online,
        critical_alerts=critical_alerts,
        recognitions_today=recognitions_today,
        unknowns_today=unknowns_today,
        average_confidence=float(avg_confidence),
        connected_cameras=connected_cameras,
        total_cameras=total_cameras,
        detections_today=detections_today,
        active_alerts=active_alerts,
        system_health=system_health,
    )





# ==================== System Version Bundle Endpoint ====================

@router.get("/api/system/version-bundle", response_model=VersionBundleResponse)
def get_system_version_bundle():
    """
    Get current immutable version snapshot for detection model, embedding model,
    gallery, thresholds, camera configuration, and algorithm versions.
    """
    return active_version_bundle.to_dict()




@router.post("/api/nodes/health", response_model=NodeHealthReportResponse)
def report_node_health(
    req: NodeHealthReportRequest,
    api_key: str = Depends(verify_edge_node)
):
    """
    Ingest live health metrics, operational mode, and adaptive runtime decisions
    from an edge recognition node.
    """
    now = datetime.now(IST)
    node_health_store[req.device_id] = {
        "device_id": req.device_id,
        "camera_id": req.camera_id,
        "mode": req.mode,
        "metrics": req.metrics,
        "decisions": req.decisions or [],
        "last_heartbeat": now.isoformat(),
    }
    return NodeHealthReportResponse(
        status="ok",
        recorded_at=now,
    )





@router.get("/api/nodes/health")
def get_all_nodes_health(
    db: Session = Depends(get_db)
):
    """Get latest health snapshots and runtime modes for all active edge nodes."""
    return {"nodes": list(node_health_store.values())}




# ==================== Thresholds Endpoints ====================

# Threshold settings that are on/off switches rather than numbers.
_BOOLEAN_THRESHOLDS = {"auto_alert_on_blacklist"}


@router.get("/api/thresholds", response_model=ModelThresholdsResponse)
def get_thresholds(db: Session = Depends(get_db)):
    """Get current model thresholds."""
    # Defaults
    thresholds: Dict[str, Any] = {
        "similarity_confidence": 0.60,
        "liveness_threshold": 0.50,
        "age_variance": 5.0,
        "unknown_face_retention_days": 30.0,
        "auto_alert_on_blacklist": True,
    }

    # Load from DB if available (every value is stored as a number; booleans are stored as 1.0 / 0.0)
    db_thresholds = db.query(DBModelThreshold).all()
    for t in db_thresholds:
        if t.name in _BOOLEAN_THRESHOLDS:
            thresholds[t.name] = t.value >= 0.5
        elif t.name in thresholds:
            thresholds[t.name] = t.value

    return ModelThresholdsResponse(**thresholds)





@router.post("/api/thresholds", response_model=ModelThresholdsResponse)
def update_thresholds(
    thresholds: ModelThresholdsResponse,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Update model thresholds."""
    dumped = thresholds.model_dump() if hasattr(thresholds, "model_dump") else thresholds.dict()
    for field, value in dumped.items():
        if value is None:
            continue
        # The value column is numeric. PostgreSQL rejects a boolean in a numeric column (SQLite accepts it),
        # so store booleans as 1.0 / 0.0.
        stored = float(value)
        existing = db.query(DBModelThreshold).filter(DBModelThreshold.name == field).first()
        if existing:
            existing.value = stored
        else:
            db.add(DBModelThreshold(id=field, name=field, value=stored))
    
    db.commit()
    
    # Broadcast to all connected clients. This endpoint runs in a worker thread (no event loop),
    # so schedule the async broadcast as a background task instead of asyncio.create_task.
    background_tasks.add_task(manager.broadcast, "kpis", {"thresholds": dumped})

    return thresholds


# ==================== Biometric Retention Endpoints ====================

@router.get("/api/system/retention/status", response_model=BiometricRetentionStatusResponse)
def get_system_retention_status(db: Session = Depends(get_db)):
    """Retrieve current biometric retention policy status and metric counters."""
    from retention import get_retention_status
    status = get_retention_status(db)
    return BiometricRetentionStatusResponse(**status)


@router.post("/api/system/retention/purge", response_model=BiometricRetentionResponse)
def trigger_system_retention_purge(
    req: Optional[BiometricRetentionRequest] = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    """
    Manually trigger biometric retention pruning (Administrator only).
    Purges raw face crop thumbnails older than retention_days while preserving full event audit records.
    Profile reference enrollment photos are never touched.
    """
    from retention import purge_expired_biometrics
    req = req or BiometricRetentionRequest()
    result = purge_expired_biometrics(
        db=db,
        retention_days=req.retention_days,
        preserve_flagged_alerts=req.preserve_flagged_alerts,
    )

    log_audit(
        db=db,
        action="retention.purge",
        username=current_user.username,
        role=current_user.role,
        user_id=current_user.id,
        resource_type="system",
        resource_id="biometrics",
        details=(
            f"Purged {result.get('purged_face_crops_count', 0)} face crops "
            f"(retention_days={result.get('retention_days')}, "
            f"preserve_flagged_alerts={result.get('preserve_flagged_alerts')})"
        ),
    )

    return BiometricRetentionResponse(**result)



