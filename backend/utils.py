import hashlib
import logging
import re
import uuid
from typing import Optional, Tuple, Any, Dict
from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from config import IST, to_ist_iso
from models import (
    Profile, Detection, Camera,
    DetectionStatus as DetectionStatusEnum,
    ProfileRole as ProfileRoleEnum,
    Gender as GenderEnum
)

AVATAR_TONES = ['sky', 'amber', 'rose', 'violet', 'emerald', 'cyan', 'orange', 'indigo']

logger = logging.getLogger(__name__)

# Camera ids from edge nodes become database keys and URL parts: keep them simple.
CAMERA_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def compute_gallery_version(embedding_ids) -> int:
    """Deterministic gallery version derived from the enrolled vectors themselves.

    It changes whenever a vector is added, removed or replaced; a count-based number stays the same when one
    vector replaces another. Result is a positive 31-bit integer (1 for an empty gallery).
    """
    digest = hashlib.sha256("|".join(sorted(str(i) for i in embedding_ids)).encode("utf-8")).hexdigest()
    if not embedding_ids:
        return 1
    return (int(digest[:8], 16) % 2_000_000_000) or 1


def is_valid_camera_id(camera_id: str) -> bool:
    return bool(CAMERA_ID_PATTERN.match(camera_id or ""))


def live_camera_ids(db: Session) -> set:
    """Cameras that are live: they have pushed frames, or have live (non-archive) detections."""
    from state import known_stream_camera_ids
    ids = set(known_stream_camera_ids())
    rows = db.query(Detection.camera_id).filter(
        or_(Detection.source == "live", Detection.source.is_(None))
    ).distinct().all()
    ids.update(row[0] for row in rows if row[0])
    return ids


def archive_camera_ids(db: Session, batch_id: Optional[str] = None) -> set:
    """Cameras that appear in imported archive footage, optionally for one import batch."""
    query = db.query(Detection.camera_id).filter(Detection.source == "archive")
    if batch_id:
        query = query.filter(Detection.batch_id == batch_id)
    return {row[0] for row in query.distinct().all() if row[0]}


def register_live_camera(camera_id: str, name: Optional[str] = None, zone: Optional[str] = None) -> bool:
    """Create the Camera row for a live edge camera the first time it sends frames with a human-readable display name and zone."""
    from database import SessionLocal
    from models import CameraStatus
    db = SessionLocal()
    try:
        existing = db.query(Camera).filter(Camera.id == camera_id).first()
        if not existing:
            # Format clean human-readable default name and zone
            clean_name = name or camera_id.replace("-", " ").replace("_", " ").title()
            default_zone = zone or ("Lobby / Entrance" if any(w in camera_id.lower() for w in ("reception", "door", "lane", "entrance", "gate")) else "General Facility")
            db.add(Camera(id=camera_id, name=clean_name, zone=default_zone, status=CameraStatus.online))
            db.commit()
        return True
    except Exception as exc:
        db.rollback()
        logger.warning("Could not register live camera %s: %s", camera_id, exc)
        return False
    finally:
        db.close()

def snapshot_tone_for(key: str) -> str:
    digest = hashlib.md5(key.encode('utf-8')).hexdigest()
    return AVATAR_TONES[int(digest, 16) % len(AVATAR_TONES)]

def is_pending_unknown_identity(identity: str) -> bool:
    if not identity or identity == "Unknown":
        return True
    if identity.startswith("Person "):
        parts = identity.split()
        if len(parts) == 2 and parts[1].isdigit():
            return True
    return False

def parse_gender(value: Optional[str]) -> GenderEnum:
    if not value:
        return GenderEnum.unknown
    normalized = str(value).lower()
    if normalized == GenderEnum.male.value:
        return GenderEnum.male
    if normalized == GenderEnum.female.value:
        return GenderEnum.female
    return GenderEnum.unknown

def resolve_detection_identity(db: Session, identity: str):
    """Return (profile, profile_id, status) for an edge identity string."""
    if is_pending_unknown_identity(identity):
        return None, None, DetectionStatusEnum.unknown

    profile = db.query(Profile).filter(Profile.name == identity).first()
    if profile:
        if profile.role in (ProfileRoleEnum.blacklist, ProfileRoleEnum.watchlist):
            status = DetectionStatusEnum.flagged
        else:
            status = DetectionStatusEnum.recognized
        return profile, profile.id, status

    new_id = str(uuid.uuid4())
    profile = Profile(id=new_id, name=identity, role=ProfileRoleEnum.visitor)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile, new_id, DetectionStatusEnum.recognized

def alert_meta_for_detection(
    status: DetectionStatusEnum,
    profile: Optional[Profile],
    identity: str,
) -> tuple[bool, Optional[str], Optional[str]]:
    if status == DetectionStatusEnum.unknown:
        label = identity if identity != "Unknown" else "unknown subject"
        return True, "medium", f"Unknown face detected ({label})"
    if profile and profile.role == ProfileRoleEnum.blacklist:
        return True, "critical", f"Blacklist match: {profile.name}"
    if profile and profile.role == ProfileRoleEnum.watchlist:
        return True, "high", f"Watchlist match: {profile.name}"
    if status == DetectionStatusEnum.flagged:
        name = profile.name if profile else identity
        return True, "high", f"Flagged identity: {name}"
    return False, None, None

def build_face_log_payload(
    detection: Detection,
    camera: Camera,
    profile: Optional[Profile],
) -> dict:
    return {
        "id": detection.id,
        "camera_id": detection.camera_id,
        "camera_name": camera.name,
        "timestamp": to_ist_iso(detection.timestamp),
        "status": detection.status.value,
        "confidence": detection.confidence,
        "liveness_score": detection.liveness_score,
        "profile_id": detection.profile_id,
        "profile_name": profile.name if profile else None,
        "role": profile.role.value if profile else None,
        "age": detection.age or 0,
        "gender": detection.gender.value if detection.gender else "unknown",
        "wearing_mask": detection.wearing_mask,
        "wearing_glasses": detection.wearing_glasses,
        "snapshot_tone": snapshot_tone_for(detection.id),
        "face_image": detection.face_image,
        "quality_score": getattr(detection, "quality_score", None),
    }

MAX_IMAGE_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB default limit
ALLOWED_IMAGE_MIMES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/bmp",
    "application/octet-stream",  # Permitted if binary magic bytes verify as image
}


def is_valid_image_bytes(data: bytes) -> bool:
    """Check magic bytes for JPEG, PNG, WebP, or BMP."""
    if len(data) < 4:
        return False
    # JPEG: starts with FF D8 FF
    if data.startswith(b"\xff\xd8\xff"):
        return True
    # PNG: starts with 89 50 4E 47 0D 0A 1A 0A
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return True
    # WebP: starts with RIFF....WEBP
    if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP":
        return True
    # BMP: starts with BM
    if data.startswith(b"BM"):
        return True
    return False


async def validate_image_upload(
    file: Any,
    max_size: int = MAX_IMAGE_UPLOAD_BYTES
) -> bytes:
    """
    Safely read and validate an uploaded image file.
    - Ensures file is non-empty.
    - Enforces maximum size bounds (raises 413 if exceeded).
    - Checks MIME type and header magic bytes (raises 400 if invalid).
    Returns raw byte contents.
    """
    if file is None:
        raise HTTPException(status_code=400, detail="No file provided")

    if isinstance(file, bytes):
        data = file
    elif hasattr(file, "read"):
        chunk = await file.read(max_size + 1)
        if len(chunk) > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"Uploaded file exceeds maximum allowed limit of {max_size // (1024 * 1024)}MB."
            )
        data = chunk
    else:
        raise HTTPException(status_code=400, detail="Invalid file object provided")

    if not data or len(data) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    content_type = getattr(file, "content_type", None)
    if content_type and content_type.lower() not in ALLOWED_IMAGE_MIMES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{content_type}'. Allowed formats: JPEG, PNG, WebP, BMP."
        )

    if not is_valid_image_bytes(data):
        raise HTTPException(
            status_code=400,
            detail="File content does not match a valid image format (JPEG, PNG, WebP, BMP)."
        )

    return data


async def extract_face_embedding(file: Any) -> Optional[Any]:
    """Helper to extract face embedding from uploaded file or validated image bytes."""
    try:
        from state import ai_models
        import cv2
        import numpy as np
    except ImportError:
        return None

    detector = ai_models.get('detector')
    if not detector:
        return None
    try:
        if isinstance(file, bytes):
            contents = file
        else:
            contents = await validate_image_upload(file)

        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return None
        
        # Get faces using the facial_recognition module
        results = detector.detect(img)
        if not results:
            return None
            
        # Return largest face embedding (bbox is [x0, y0, x1, y1])
        faces = sorted(results, key=lambda f: (f['bbox'][2]-f['bbox'][0]) * (f['bbox'][3]-f['bbox'][1]), reverse=True)
        face = faces[0]
        embedding = detector.extract_embedding(img, face)
        return embedding
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error extracting embedding: {e}")
        return None


