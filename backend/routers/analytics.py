
import logging
from fastapi import APIRouter, File, UploadFile, Form, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, extract, text, case, select, or_
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Any
import uuid

logger = logging.getLogger(__name__)

from database import get_db
from models import (
    Camera, Profile, Detection, CameraTransition, Alert, UnregisteredSubject, Embedding,
    ProfileRole as ProfileRoleEnum, DetectionStatus as DetectionStatusEnum
)
from schemas import (
    SubjectIntelligenceResponse, DailyPunchResponse, ShiftBreakdownResponse,
    ObservedCameraStat, SubjectVectorMatch, TemporalAnomalyEvent,
    MovementNetworkResponse, MovementEdgeResponse,
    DuplicateCandidateResponse, ProfileResponse,
    SubjectTrajectoryResponse, TrajectoryNodeResponse,
    FootfallBucketResponse, DemographicSliceResponse,
    AttendanceRecordFullResponse
)
from config import IST, to_ist, to_ist_iso
from utils import snapshot_tone_for

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.get("/movement-network", response_model=MovementNetworkResponse)
def get_movement_network(hours: int = Query(24), db: Session = Depends(get_db)):
    """Return observed identified-person movement between cameras."""
    start_time = datetime.now(IST) - timedelta(hours=hours)
    rows = db.query(
        CameraTransition.from_camera_id,
        CameraTransition.to_camera_id,
        func.count(CameraTransition.id).label("count"),
        func.max(CameraTransition.detected_at).label("last_seen"),
        func.avg(CameraTransition.travel_seconds).label("average_travel_seconds"),
    ).filter(
        CameraTransition.detected_at >= start_time,
    ).group_by(
        CameraTransition.from_camera_id,
        CameraTransition.to_camera_id,
    ).order_by(func.max(CameraTransition.detected_at).desc()).all()

    camera_ids = {row.from_camera_id for row in rows} | {row.to_camera_id for row in rows}
    cameras = {camera.id: camera for camera in db.query(Camera).filter(Camera.id.in_(camera_ids)).all()}
    return MovementNetworkResponse(edges=[MovementEdgeResponse(
        fromCameraId=row.from_camera_id,
        fromCameraName=cameras.get(row.from_camera_id).name if cameras.get(row.from_camera_id) else row.from_camera_id,
        toCameraId=row.to_camera_id,
        toCameraName=cameras.get(row.to_camera_id).name if cameras.get(row.to_camera_id) else row.to_camera_id,
        count=int(row.count),
        lastSeen=to_ist(row.last_seen),
        averageTravelSeconds=round(float(row.average_travel_seconds), 1),
    ) for row in rows])



def _get_duplicates_fallback(db: Session) -> list[DuplicateCandidateResponse]:
    """In-memory fallback for SQLite or non-PostgreSQL dialects where pgvector <=> is unavailable."""
    import json
    import numpy as np
    embeddings = db.query(Embedding).join(Profile).options(joinedload(Embedding.profile)).all()
    candidates = []
    seen = set()

    profile_vecs = []
    for emb in embeddings:
        p = emb.profile
        if not p or emb.vector is None:
            continue
        try:
            raw_v = emb.vector
            if isinstance(raw_v, str):
                raw_v = json.loads(raw_v)
            vec = np.asarray(raw_v, dtype=np.float32).flatten()
            norm = np.linalg.norm(vec)
            if norm >= 1e-6:
                profile_vecs.append((p, vec / norm))
        except Exception:
            continue

    for i in range(len(profile_vecs)):
        p1, v1 = profile_vecs[i]
        for j in range(i + 1, len(profile_vecs)):
            p2, v2 = profile_vecs[j]
            if p1.id == p2.id:
                continue
            pair = tuple(sorted([p1.id, p2.id]))
            if pair in seen:
                continue
            sim = float(np.dot(v1, v2))
            if sim >= 0.90:
                seen.add(pair)
                candidates.append(DuplicateCandidateResponse(
                    id=f"{p1.id}:{p2.id}",
                    profileAId=p1.id,
                    profileAName=p1.name,
                    profileARole=p1.role.value if hasattr(p1.role, 'value') else str(p1.role),
                    profileAAvatarTone=snapshot_tone_for(p1.id),
                    profileBId=p2.id,
                    profileBName=p2.name,
                    profileBRole=p2.role.value if hasattr(p2.role, 'value') else str(p2.role),
                    profileBAvatarTone=snapshot_tone_for(p2.id),
                    cosineSimilarity=round(sim, 4),
                    sharedSightings=0,
                ))
    candidates.sort(key=lambda c: c.cosineSimilarity, reverse=True)
    return candidates[:50]


@router.get("/duplicates", response_model=list[DuplicateCandidateResponse])
def get_duplicates(db: Session = Depends(get_db)):
    """Find duplicate profiles using pgvector (with in-memory SQLite fallback)."""
    bind = db.get_bind()
    if not bind or getattr(bind, "dialect", None) is None or bind.dialect.name != "postgresql":
        return _get_duplicates_fallback(db)

    # Use LATERAL nearest-neighbor query to leverage the HNSW index on embeddings.vector
    # instead of an O(N^2) all-pairs Cartesian join (solves R9).
    sql = text("""
        SELECT
            e1.profile_id as p1_id, p1.name as p1_name, p1.role as p1_role, p1.created_at as p1_created,
            nearest.profile_id as p2_id, nearest.p2_name as p2_name, nearest.p2_role as p2_role, nearest.p2_created as p2_created,
            1.0 - nearest.dist as similarity
        FROM (
            SELECT DISTINCT ON (profile_id) id, profile_id, vector
            FROM embeddings
            ORDER BY profile_id, created_at DESC
            LIMIT 200
        ) e1
        JOIN profiles p1 ON e1.profile_id = p1.id
        CROSS JOIN LATERAL (
            SELECT e2.profile_id, p2.name as p2_name, p2.role as p2_role, p2.created_at as p2_created,
                   (e2.vector <=> e1.vector) as dist
            FROM embeddings e2
            JOIN profiles p2 ON e2.profile_id = p2.id
            WHERE e2.profile_id != e1.profile_id
            ORDER BY e2.vector <=> e1.vector ASC
            LIMIT 1
        ) nearest
        WHERE nearest.dist < 0.1
        ORDER BY similarity DESC
        LIMIT 20
    """)
    try:
        result = db.execute(sql)
        candidates = []
        seen = set()
        for row in result:
            pair = tuple(sorted([row.p1_id, row.p2_id]))
            if pair in seen:
                continue
            seen.add(pair)
            
            candidates.append(DuplicateCandidateResponse(
                id=f"{row.p1_id}:{row.p2_id}",
                profileAId=row.p1_id,
                profileAName=row.p1_name,
                profileARole=row.p1_role.value if hasattr(row.p1_role, 'value') else str(row.p1_role),
                profileAAvatarTone=snapshot_tone_for(row.p1_id),
                profileBId=row.p2_id,
                profileBName=row.p2_name,
                profileBRole=row.p2_role.value if hasattr(row.p2_role, 'value') else str(row.p2_role),
                profileBAvatarTone=snapshot_tone_for(row.p2_id),
                cosineSimilarity=round(float(row.similarity), 4),
                sharedSightings=0,
            ))
        return candidates
    except Exception as exc:
        logger.warning("PostgreSQL lateral pgvector query encountered error: %s. Falling back to in-memory.", exc)
        return _get_duplicates_fallback(db)


@router.get("/trajectory", response_model=SubjectTrajectoryResponse)
def get_trajectory(profileId: Optional[str] = Query(None), hours: int = Query(24), db: Session = Depends(get_db)):
    start_time = datetime.now(IST) - timedelta(hours=hours) if hours > 0 else None
    
    # If no profileId supplied, find most recently detected profile or first available profile
    if not profileId:
        latest_det = db.query(Detection).filter(Detection.profile_id.isnot(None)).order_by(Detection.timestamp.desc()).first()
        if latest_det and latest_det.profile_id:
            profileId = latest_det.profile_id
        else:
            first_profile = db.query(Profile).first()
            if first_profile:
                profileId = first_profile.id
            else:
                return SubjectTrajectoryResponse(
                    profileId="none",
                    profileName="No Profiles Found",
                    role="visitor",
                    path=[]
                )

    # 1. Check Profile
    profile = db.query(Profile).filter(
        (Profile.id == profileId) | (func.lower(Profile.name) == func.lower(profileId))
    ).first()
    
    if profile:
        det_query = db.query(Detection).options(joinedload(Detection.camera)).filter(
            Detection.profile_id == profile.id
        )
        if start_time is not None:
            time_bounded = det_query.filter(Detection.timestamp >= start_time).order_by(Detection.timestamp.asc()).all()
            detections = time_bounded if time_bounded else det_query.order_by(Detection.timestamp.asc()).all()
        else:
            detections = det_query.order_by(Detection.timestamp.asc()).all()

        path = [
            TrajectoryNodeResponse(
                cameraId=d.camera_id,
                cameraName=d.camera.name if d.camera else "Unknown",
                zone=d.camera.zone if d.camera else "General",
                timestamp=to_ist(d.timestamp),
                confidence=d.confidence,
                snapshotTone=snapshot_tone_for(d.id),
            )
            for d in detections
        ]
        return SubjectTrajectoryResponse(
            profileId=profile.id,
            profileName=profile.name,
            role=profile.role.value if hasattr(profile.role, 'value') else str(profile.role or "visitor"),
            path=path
        )

    # 2. Check Unregistered Subject
    unreg = db.query(UnregisteredSubject).filter(
        (UnregisteredSubject.id == profileId) | (UnregisteredSubject.display_name == profileId)
    ).first()
    if unreg:
        det_query = db.query(Detection).options(joinedload(Detection.camera)).filter(
            (Detection.unregistered_subject_id == unreg.id) | (Detection.profile_id == unreg.id)
        )
        if start_time is not None:
            time_bounded = det_query.filter(Detection.timestamp >= start_time).order_by(Detection.timestamp.asc()).all()
            detections = time_bounded if time_bounded else det_query.order_by(Detection.timestamp.asc()).all()
        else:
            detections = det_query.order_by(Detection.timestamp.asc()).all()

        path = [
            TrajectoryNodeResponse(
                cameraId=d.camera_id,
                cameraName=d.camera.name if d.camera else "Unknown",
                zone=d.camera.zone if d.camera else "General",
                timestamp=to_ist(d.timestamp),
                confidence=d.confidence,
                snapshotTone=snapshot_tone_for(d.id),
            )
            for d in detections
        ]
        return SubjectTrajectoryResponse(
            profileId=unreg.id,
            profileName=unreg.display_name,
            role="visitor",
            path=path
        )

    # Graceful fallback: return empty trajectory instead of breaking client with 404
    return SubjectTrajectoryResponse(
        profileId=profileId,
        profileName="Subject Not Found",
        role="visitor",
        path=[]
    )


def _normalize_datetime_filter(dt: Any) -> Optional[datetime]:
    """Convert input datetime to naive IST timestamp matching database storage."""
    if dt is None:
        return None
    if not isinstance(dt, datetime):
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(IST).replace(tzinfo=None)
    return dt


@router.get("/footfall", response_model=list[FootfallBucketResponse])
def get_footfall(
    days: int = Query(7, description="Number of days to look back from today (used if date_from/date_to not provided)"),
    date_from: Optional[datetime] = Query(None, description="Start date (inclusive) in IST"),
    date_to: Optional[datetime] = Query(None, description="End date (inclusive) in IST"),
    source: Optional[str] = Query(None, description="Filter by data source: 'live' or 'archive'"),
    batch_id: Optional[str] = Query(None, description="Filter by specific archive batch ID"),
    db: Session = Depends(get_db)
):
    norm_from = _normalize_datetime_filter(date_from)
    norm_to = _normalize_datetime_filter(date_to)

    # Determine the time range to filter by
    if norm_from is not None or norm_to is not None:
        if norm_from is not None:
            start_time = norm_from
        else:
            start_time = norm_to - timedelta(days=7)

        if norm_to is not None:
            end_time = norm_to
        else:
            end_time = norm_from + timedelta(days=7)
    else:
        if source == "archive" or batch_id:
            start_time = datetime(1970, 1, 1)
            end_time = datetime(2099, 12, 31)
        else:
            # Fall back to default days (converted to naive IST)
            now_ist = datetime.now(IST).replace(tzinfo=None)
            start_time = now_ist - timedelta(days=days)
            end_time = now_ist

    q = db.query(
        Detection.timestamp,
        Detection.status
    ).filter(
        Detection.timestamp >= start_time,
        Detection.timestamp <= end_time
    )
    if source:
        q = q.filter(Detection.source == source)
    if batch_id:
        q = q.filter(Detection.batch_id == batch_id)

    detections = q.all()

    buckets = {}
    for d in detections:
        ts = to_ist(d.timestamp)
        if ts is None:
            continue
            
        hour_str = f"{ts.hour:02d}:00"
        if hour_str not in buckets:
            buckets[hour_str] = {'total': 0, 'recognized': 0, 'unknown': 0}
            
        buckets[hour_str]['total'] += 1
        if d.status == DetectionStatusEnum.recognized:
            buckets[hour_str]['recognized'] += 1
        elif d.status == DetectionStatusEnum.unknown:
            buckets[hour_str]['unknown'] += 1

    final_res = []
    for i in range(24):
        hour_str = f"{i:02d}:00"
        b = buckets.get(hour_str, {'total': 0, 'recognized': 0, 'unknown': 0})
        final_res.append(FootfallBucketResponse(
            hour=hour_str, 
            detections=b['total'], 
            recognized=b['recognized'], 
            unknown=b['unknown']
        ))
    return final_res


@router.get("/age-distribution", response_model=list[DemographicSliceResponse])
def get_age_distribution(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    source: Optional[str] = Query(None),
    batch_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    norm_from = _normalize_datetime_filter(date_from)
    norm_to = _normalize_datetime_filter(date_to)

    subject_id_col = func.coalesce(
        Detection.profile_id,
        Detection.unregistered_subject_id,
        func.concat('unk_', Detection.id)
    ).label("subject_id")

    subq = db.query(subject_id_col, Detection.age).filter(
        Detection.age != None
    )
    if norm_from:
        subq = subq.filter(Detection.timestamp >= norm_from)
    if norm_to:
        subq = subq.filter(Detection.timestamp <= norm_to)
    if source:
        subq = subq.filter(Detection.source == source)
    dialect_name = getattr(getattr(db.bind, 'dialect', None), 'name', '') if db.bind else ''
    if dialect_name == "postgresql":
        subq = subq.distinct(subject_id_col).subquery()
    else:
        subq = subq.group_by(subject_id_col, Detection.age).subquery()

    results = db.query(subq.c.age, func.count(subq.c.subject_id)).group_by(subq.c.age).all()
    
    buckets = {"18-24": 0, "25-34": 0, "35-44": 0, "45-54": 0, "55+": 0}
    for age, count in results:
        if age < 18:
            continue
        elif age <= 24:
            buckets["18-24"] += count
        elif age <= 34:
            buckets["25-34"] += count
        elif age <= 44:
            buckets["35-44"] += count
        elif age <= 54:
            buckets["45-54"] += count
        else:
            buckets["55+"] += count

    return [DemographicSliceResponse(label=k, value=v) for k, v in buckets.items()]


@router.get("/gender-distribution", response_model=list[DemographicSliceResponse])
def get_gender_distribution(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    source: Optional[str] = Query(None),
    batch_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    norm_from = _normalize_datetime_filter(date_from)
    norm_to = _normalize_datetime_filter(date_to)

    subject_id_col = func.coalesce(
        Detection.profile_id,
        Detection.unregistered_subject_id,
        func.concat('unk_', Detection.id)
    ).label("subject_id")

    subq = db.query(subject_id_col, Detection.gender).filter(
        Detection.gender.isnot(None)
    )
    if norm_from:
        subq = subq.filter(Detection.timestamp >= norm_from)
    if norm_to:
        subq = subq.filter(Detection.timestamp <= norm_to)
    if source:
        subq = subq.filter(Detection.source == source)
    dialect_name = getattr(getattr(db.bind, 'dialect', None), 'name', '') if db.bind else ''
    if dialect_name == "postgresql":
        subq = subq.distinct(subject_id_col).subquery()
    else:
        subq = subq.group_by(subject_id_col, Detection.gender).subquery()

    results = db.query(subq.c.gender, func.count(subq.c.subject_id)).group_by(subq.c.gender).all()
    slices = []
    for gender, count in results:
        if gender:
            label = gender.value.lower() if hasattr(gender, 'value') else str(gender).lower()
            slices.append(DemographicSliceResponse(label=label.capitalize(), value=count))
    return slices


@router.get("/attendance", response_model=list[AttendanceRecordFullResponse])
def get_attendance(
    days: int = Query(7),
    date_from: Optional[datetime] = Query(None, description="Start date (inclusive) in IST"),
    date_to: Optional[datetime] = Query(None, description="End date (inclusive) in IST"),
    source: Optional[str] = Query(None),
    batch_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    norm_from = _normalize_datetime_filter(date_from)
    norm_to = _normalize_datetime_filter(date_to)

    if norm_from is not None or norm_to is not None:
        if norm_from is not None:
            start_time = norm_from
        else:
            start_time = norm_to - timedelta(days=7)
        if norm_to is not None:
            end_time = norm_to
        else:
            end_time = norm_from + timedelta(days=7)
    else:
        if source == "archive" or batch_id:
            start_time = datetime(1970, 1, 1)
            end_time = datetime(2099, 12, 31)
        else:
            now_ist = datetime.now(IST).replace(tzinfo=None)
            start_time = now_ist - timedelta(days=days)
            end_time = now_ist
    
    att_q = db.query(
        Detection.profile_id,
        Detection.unregistered_subject_id,
        func.min(Detection.timestamp).label('check_in'),
        func.max(Detection.timestamp).label('check_out'),
        func.count(Detection.id).label('total_sightings'),
    ).filter(
        (Detection.profile_id != None) | (Detection.unregistered_subject_id != None),
        Detection.timestamp >= start_time,
        Detection.timestamp <= end_time
    )
    if source:
        att_q = att_q.filter(Detection.source == source)
    if batch_id:
        att_q = att_q.filter(Detection.batch_id == batch_id)

    results = att_q.group_by(Detection.profile_id, Detection.unregistered_subject_id).all()

    if not results:
        return []

    profile_ids = [r.profile_id for r in results if r.profile_id]
    unreg_ids = [r.unregistered_subject_id for r in results if r.unregistered_subject_id]
    
    profiles = {p.id: p for p in db.query(Profile).filter(Profile.id.in_(profile_ids)).all()} if profile_ids else {}
    unregs = {u.id: u for u in db.query(UnregisteredSubject).filter(UnregisteredSubject.id.in_(unreg_ids)).all()} if unreg_ids else {}

    records = []
    
    for row in results:
        if row.profile_id and row.profile_id in profiles:
            p = profiles[row.profile_id]
            records.append(AttendanceRecordFullResponse(
                profileId=p.id,
                profileName=p.name,
                role=p.role.value if hasattr(p.role, 'value') else str(p.role or "visitor"),
                department=p.department,
                checkIn=to_ist(row.check_in),
                checkOut=to_ist(row.check_out),
                totalSightings=int(row.total_sightings or 0),
                avatarTone=snapshot_tone_for(p.id),
            ))
        elif row.unregistered_subject_id and row.unregistered_subject_id in unregs:
            u = unregs[row.unregistered_subject_id]
            records.append(AttendanceRecordFullResponse(
                profileId=u.id,
                profileName=u.display_name,
                role="unknown",
                department=None,
                checkIn=to_ist(row.check_in),
                checkOut=to_ist(row.check_out),
                totalSightings=int(row.total_sightings or 0),
                avatarTone="gray",
            ))
    return records





# ==================== Subject Intelligence & Behavioral Analytics ====================

@router.get("/subjects/{subject_id}/intelligence", response_model=SubjectIntelligenceResponse)
def get_subject_intelligence(subject_id: str, db: Session = Depends(get_db)):
    """Fetch complete forensic intelligence: first/last seen, daily punches, 24h diurnal histogram, shift breakdown, active days, and vector similarity."""
    from collections import defaultdict
    import numpy as np
    import json
    
    unreg = db.query(UnregisteredSubject).filter(UnregisteredSubject.id == subject_id).first()
    profile = None
    if not unreg:
        profile = db.query(Profile).filter(Profile.id == subject_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail=f"Subject {subject_id} not found")

    display_name = unreg.display_name if unreg else profile.name
    status_str = "unregistered" if unreg else "profile"
    
    if unreg:
        dets = db.query(Detection).filter(
            Detection.unregistered_subject_id == subject_id
        ).order_by(Detection.timestamp.asc()).all()
    else:
        dets = db.query(Detection).filter(
            Detection.profile_id == subject_id
        ).order_by(Detection.timestamp.asc()).all()

    if not dets:
        return SubjectIntelligenceResponse(
            subject_id=subject_id,
            display_name=display_name,
            status=status_str,
            total_sightings=0,
            active_days_count=0,
            active_dates=[],
            shift_breakdown=ShiftBreakdownResponse(),
            hourly_frequency=[0] * 24,
            daily_punches=[],
            observed_cameras=[],
            candidate_vector_matches=[]
        )

    # 1. Global Timings
    global_first_seen = to_ist_iso(dets[0].timestamp)
    global_last_seen = to_ist_iso(dets[-1].timestamp)
    presence_span_hours = round((dets[-1].timestamp - dets[0].timestamp).total_seconds() / 3600.0, 2)

    # 2. Daily Punches (Group by Calendar Date in IST)
    daily_groups = defaultdict(list)
    for d in dets:
        ist_dt = to_ist(d.timestamp)
        date_str = ist_dt.strftime("%Y-%m-%d")
        daily_groups[date_str].append((ist_dt, d))

    sorted_dates = sorted(daily_groups.keys())
    daily_punches = []
    total_dwell_seconds = 0

    for dt_str in sorted_dates:
        group = daily_groups[dt_str]
        first_dt = group[0][0]
        last_dt = group[-1][0]
        dwell_s = max(0, int((last_dt - first_dt).total_seconds()))
        total_dwell_seconds += dwell_s
        cams = sorted(list({g[1].camera_id for g in group if g[1].camera_id}))
        daily_punches.append(DailyPunchResponse(
            date=dt_str,
            first_seen=first_dt.strftime("%H:%M:%S"),
            last_seen=last_dt.strftime("%H:%M:%S"),
            dwell_seconds=dwell_s,
            sightings_count=len(group),
            cameras=cams
        ))

    avg_dwell_min = round((total_dwell_seconds / max(1, len(sorted_dates))) / 60.0, 1)

    # 3. 24-Hour Diurnal Histogram
    hourly_freq = [0] * 24
    for d in dets:
        ist_dt = to_ist(d.timestamp)
        hourly_freq[ist_dt.hour] += 1

    # 4. Shift Breakdown
    m_count, a_count, n_count = 0, 0, 0
    for d in dets:
        ist_dt = to_ist(d.timestamp)
        h = ist_dt.hour
        if 6 <= h < 14:
            m_count += 1
        elif 14 <= h < 22:
            a_count += 1
        else:
            n_count += 1

    tot = float(len(dets))
    shift_breakdown = ShiftBreakdownResponse(
        morning_shift_a=m_count,
        afternoon_shift_b=a_count,
        night_shift_c=n_count,
        morning_percentage=round((m_count / tot) * 100.0, 1),
        afternoon_percentage=round((a_count / tot) * 100.0, 1),
        night_percentage=round((n_count / tot) * 100.0, 1)
    )

    # 5. Observed Cameras
    camera_map = {c.id: c.name for c in db.query(Camera).all()}
    cam_stats = defaultdict(lambda: {"count": 0, "first": None, "last": None})
    for d in dets:
        ist_dt = to_ist(d.timestamp)
        c_id = d.camera_id
        entry = cam_stats[c_id]
        entry["count"] += 1
        if entry["first"] is None:
            entry["first"] = ist_dt
        entry["last"] = ist_dt

    observed_cameras = []
    for c_id, stat in cam_stats.items():
        observed_cameras.append(ObservedCameraStat(
            camera_id=c_id,
            camera_name=camera_map.get(c_id, c_id),
            count=stat["count"],
            first_seen=stat["first"].strftime("%Y-%m-%d %H:%M:%S") if stat["first"] else None,
            last_seen=stat["last"].strftime("%Y-%m-%d %H:%M:%S") if stat["last"] else None,
        ))

    # 6. Best Exemplar Portrait
    best_det = max(dets, key=lambda x: x.quality_score if x.quality_score is not None else 0.0)

    # 7. Candidate Vector Matches (Cosine Similarity)
    candidate_matches = []
    subject_vec = None
    if unreg and unreg.representative_embedding is not None:
        subject_vec = unreg.representative_embedding
    elif best_det and best_det.embedding_vector is not None:
        subject_vec = best_det.embedding_vector

    if subject_vec is not None:
        try:
            raw_v = subject_vec
            if isinstance(raw_v, str):
                raw_v = json.loads(raw_v)
            vec = np.asarray(raw_v, dtype=np.float32).flatten()
            norm = np.linalg.norm(vec)
            if norm >= 1e-6:
                norm_vec = vec / norm
                # Compare against other unregistered subjects
                other_unregs = db.query(UnregisteredSubject).filter(
                    UnregisteredSubject.id != subject_id,
                    UnregisteredSubject.representative_embedding != None
                ).limit(100).all()
                for ou in other_unregs:
                    ov = ou.representative_embedding
                    if isinstance(ov, str):
                        ov = json.loads(ov)
                    ov_arr = np.asarray(ov, dtype=np.float32).flatten()
                    ov_norm = np.linalg.norm(ov_arr)
                    if ov_norm >= 1e-6:
                        sim = float(np.dot(norm_vec, ov_arr / ov_norm))
                        if sim >= 0.50:
                            candidate_matches.append(SubjectVectorMatch(
                                id=ou.id,
                                name=ou.display_name,
                                similarity=round(sim * 100.0, 1),
                                role="unregistered",
                                is_profile=False
                            ))
                # Also compare against official profiles
                profs = db.query(Profile).join(Embedding).all()
                for p in profs:
                    if p.id == subject_id:
                        continue
                    for emb in p.embeddings:
                        if emb.vector is not None:
                            pv = emb.vector
                            if isinstance(pv, str):
                                pv = json.loads(pv)
                            pv_arr = np.asarray(pv, dtype=np.float32).flatten()
                            pv_norm = np.linalg.norm(pv_arr)
                            if pv_norm >= 1e-6:
                                sim = float(np.dot(norm_vec, pv_arr / pv_norm))
                                if sim >= 0.55:
                                    candidate_matches.append(SubjectVectorMatch(
                                        id=p.id,
                                        name=p.name,
                                        similarity=round(sim * 100.0, 1),
                                        role=p.role.value if hasattr(p.role, 'value') else str(p.role),
                                        is_profile=True
                                    ))
                                    break
                candidate_matches.sort(key=lambda x: x.similarity, reverse=True)
                candidate_matches = candidate_matches[:6]
        except Exception as e:
            logger.warning(f"Failed to compute candidate vector matches: {e}")

    return SubjectIntelligenceResponse(
        subject_id=subject_id,
        display_name=display_name,
        status=status_str,
        total_sightings=len(dets),
        active_days_count=len(sorted_dates),
        active_dates=sorted_dates,
        global_first_seen=global_first_seen,
        global_last_seen=global_last_seen,
        presence_span_hours=presence_span_hours,
        average_daily_dwell_minutes=avg_dwell_min,
        shift_breakdown=shift_breakdown,
        hourly_frequency=hourly_freq,
        daily_punches=daily_punches,
        observed_cameras=observed_cameras,
        exemplar_face_image=best_det.face_image if best_det else None,
        exemplar_quality=round(best_det.quality_score, 1) if (best_det and best_det.quality_score) else None,
        exemplar_timestamp=to_ist_iso(best_det.timestamp) if best_det else None,
        exemplar_camera_id=best_det.camera_id if best_det else None,
        candidate_vector_matches=candidate_matches
    )


@router.get("/anomalies/temporal", response_model=List[TemporalAnomalyEvent])
def get_temporal_anomalies(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Return unexpected nocturnal or off-hour presence anomalies (e.g. 22:00 to 05:59)."""
    camera_map = {c.id: c.name for c in db.query(Camera).all()}
    
    dets = db.query(Detection).filter(
        or_(
            extract('hour', Detection.timestamp) < 6,
            extract('hour', Detection.timestamp) >= 22
        )
    ).order_by(Detection.timestamp.desc()).limit(limit).all()
    
    results = []
    for d in dets:
        ist_dt = to_ist(d.timestamp)
        subj_name = "Unknown Individual"
        subj_id = None
        if d.unregistered_subject:
            subj_name = d.unregistered_subject.display_name
            subj_id = d.unregistered_subject.id
        elif d.profile:
            subj_name = d.profile.name
            subj_id = d.profile.id
            
        results.append(TemporalAnomalyEvent(
            detection_id=d.id,
            subject_id=subj_id,
            subject_name=subj_name,
            timestamp=to_ist_iso(d.timestamp),
            camera_id=d.camera_id,
            camera_name=camera_map.get(d.camera_id, d.camera_id),
            hour_of_day=ist_dt.hour,
            anomaly_reason=f"Nocturnal Vigilance Detection at {ist_dt.strftime('%H:%M:%S')} (Outside Standard 06:00-22:00 Operations)",
            quality_score=round(d.quality_score, 1) if d.quality_score is not None else None,
            face_image=d.face_image
        ))
    return results
