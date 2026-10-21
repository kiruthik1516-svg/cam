"""Biometric data retention service and background worker."""

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any, Dict, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from config import IST, settings
from models import (
    Alert,
    Detection,
    DetectionStatus,
    EventPriority,
    EventProvenance,
    Profile,
)

logger = logging.getLogger(__name__)


def purge_expired_biometrics(
    db: Session,
    retention_days: Optional[int] = None,
    preserve_flagged_alerts: bool = True,
) -> Dict[str, Any]:
    """
    Purge raw face crops from Detection records older than retention_days.
    - Preserves audit metadata (timestamp, camera_id, status, confidence, bbox, profile_id).
    - If preserve_flagged_alerts is True, keeps crops associated with active alerts or flagged identities.
    - Profile reference photos/embeddings are NEVER touched.
    """
    days = retention_days if retention_days is not None else settings.detection_image_retention_days
    if days <= 0:
        return {
            "purged_face_crops_count": 0,
            "retained_face_crops_count": db.query(Detection).filter(Detection.face_image.isnot(None)).count(),
            "purged_provenance_count": 0,
            "cutoff_timestamp": None,
            "retention_days": days,
            "preserve_flagged_alerts": preserve_flagged_alerts,
        }

    cutoff = datetime.now(IST) - timedelta(days=days)

    # Build query for candidate detections with existing thumbnails
    query = db.query(Detection).filter(
        Detection.face_image.isnot(None),
        Detection.timestamp < cutoff,
    )

    if preserve_flagged_alerts:
        alert_subq = select(Alert.detection_id).where(Alert.detection_id.isnot(None))
        query = query.filter(
            Detection.status != DetectionStatus.flagged,
            Detection.priority.notin_([EventPriority.critical, EventPriority.high]),
            Detection.id.notin_(alert_subq),
        )

    expired_detections = query.all()
    purged_face_crops = len(expired_detections)
    for det in expired_detections:
        det.face_image = None

    # Also prune corresponding event_provenances older than cutoff
    prov_records = db.query(EventProvenance).filter(EventProvenance.created_at < cutoff).all()
    purged_prov = len(prov_records)
    for p in prov_records:
        db.delete(p)

    db.commit()

    retained_crops = db.query(Detection).filter(Detection.face_image.isnot(None)).count()

    logger.info(
        "[Retention] Purged %d face crops and %d provenance records older than %s "
        "(retention=%dd, preserve_flagged=%s)",
        purged_face_crops,
        purged_prov,
        cutoff.isoformat(),
        days,
        preserve_flagged_alerts,
    )

    return {
        "purged_face_crops_count": purged_face_crops,
        "retained_face_crops_count": retained_crops,
        "purged_provenance_count": purged_prov,
        "cutoff_timestamp": cutoff,
        "retention_days": days,
        "preserve_flagged_alerts": preserve_flagged_alerts,
    }


def get_retention_status(db: Session) -> Dict[str, Any]:
    """Return current status and metrics of the biometric retention policy."""
    days = settings.detection_image_retention_days
    is_enabled = days > 0
    cutoff = datetime.now(IST) - timedelta(days=days) if is_enabled else None

    total_detections = db.query(Detection).count()
    detections_with_crops = db.query(Detection).filter(Detection.face_image.isnot(None)).count()

    if is_enabled and cutoff:
        alert_subq = select(Alert.detection_id).where(Alert.detection_id.isnot(None))
        eligible_query = db.query(Detection).filter(
            Detection.face_image.isnot(None),
            Detection.timestamp < cutoff,
            Detection.status != DetectionStatus.flagged,
            Detection.priority.notin_([EventPriority.critical, EventPriority.high]),
            Detection.id.notin_(alert_subq),
        )
        eligible_crops = eligible_query.count()
    else:
        eligible_crops = 0

    flagged_crops = db.query(Detection).filter(
        Detection.face_image.isnot(None),
        or_(
            Detection.status == DetectionStatus.flagged,
            Detection.priority.in_([EventPriority.critical, EventPriority.high]),
        ),
    ).count()

    enrolled_profiles = db.query(Profile).filter(Profile.embedding_count > 0).count()

    return {
        "retention_days": days,
        "is_enabled": is_enabled,
        "worker_interval_seconds": settings.retention_worker_interval_seconds,
        "cutoff_timestamp": cutoff,
        "total_detections": total_detections,
        "detections_with_face_crops": detections_with_crops,
        "face_crops_eligible_for_purge": eligible_crops,
        "preserved_alert_face_crops": flagged_crops,
        "enrolled_profiles_protected": enrolled_profiles,
    }


async def retention_background_worker():
    """Background task that runs periodically to execute the biometric retention policy."""
    logger.info(
        "Retention background worker started (interval: %ds, retention: %d days)",
        settings.retention_worker_interval_seconds,
        settings.detection_image_retention_days,
    )
    while True:
        try:
            await asyncio.sleep(settings.retention_worker_interval_seconds)
            if settings.detection_image_retention_days > 0:
                from database import SessionLocal
                with SessionLocal() as db:
                    res = purge_expired_biometrics(
                        db=db,
                        retention_days=settings.detection_image_retention_days,
                        preserve_flagged_alerts=True,
                    )
                    logger.info("[Retention Worker] Auto-purge finished: %s", res)
        except asyncio.CancelledError:
            logger.info("Retention background worker received cancellation signal; stopping.")
            break
        except Exception as exc:
            logger.exception("[Retention Worker] Error in retention background loop: %s", exc)
