import re

# 1. Update backend/schemas.py
with open('backend/schemas.py', 'r', encoding='utf-8') as f:
    schemas = f.read()

old_flr = """class FaceLogResponse(BaseModel):
    \"\"\"Detailed face detection log matching frontend FaceLog type.\"\"\"
    id: str
    camera_id: str
    camera_name: str
    timestamp: str
    status: str
    confidence: float
    liveness_score: float
    profile_id: Optional[str]
    profile_name: Optional[str]
    role: Optional[str]
    age: int
    gender: str
    wearing_mask: bool
    wearing_glasses: bool
    snapshot_tone: str  # Color token for avatar
    face_image: Optional[str] = None
    source: Optional[str] = "live"
    batch_id: Optional[str] = None
    source_video: Optional[str] = None
    video_elapsed_sec: Optional[float] = None"""

new_flr = """class FaceLogResponse(BaseModel):
    \"\"\"Detailed face detection log matching frontend FaceLog type.\"\"\"
    id: str
    camera_id: str
    camera_name: str
    timestamp: str
    status: str
    confidence: Optional[float] = 0.0
    liveness_score: Optional[float] = 0.0
    profile_id: Optional[str] = None
    profile_name: Optional[str] = None
    role: Optional[str] = None
    age: Optional[int] = 0
    gender: Optional[str] = "unknown"
    wearing_mask: Optional[bool] = False
    wearing_glasses: Optional[bool] = False
    snapshot_tone: Optional[str] = "blue"  # Color token for avatar
    face_image: Optional[str] = None
    source: Optional[str] = "live"
    batch_id: Optional[str] = None
    source_video: Optional[str] = None
    video_elapsed_sec: Optional[float] = None"""

if old_flr in schemas:
    schemas = schemas.replace(old_flr, new_flr)
    with open('backend/schemas.py', 'w', encoding='utf-8') as f:
        f.write(schemas)
    print("Updated FaceLogResponse in backend/schemas.py")
else:
    print("WARNING: old_flr not found directly, checking regex")

# 2. Update backend/routers/logs.py
with open('backend/routers/logs.py', 'r', encoding='utf-8') as f:
    logs = f.read()

old_logs = """            confidence=det.confidence,
            liveness_score=det.liveness_score,
            profile_id=det.profile_id or (det.unregistered_subject.id if det.unregistered_subject else None),
            profile_name=resolved_name,
            role=det.profile.role.value if det.profile else None,
            age=det.age or 0,
            gender=det.gender.value if det.gender else "unknown",
            wearing_mask=det.wearing_mask,
            wearing_glasses=det.wearing_glasses,"""

new_logs = """            confidence=det.confidence or 0.0,
            liveness_score=det.liveness_score or 0.0,
            profile_id=det.profile_id or (det.unregistered_subject.id if det.unregistered_subject else None),
            profile_name=resolved_name,
            role=det.profile.role.value if det.profile else None,
            age=det.age or 0,
            gender=det.gender.value if det.gender else "unknown",
            wearing_mask=bool(det.wearing_mask) if det.wearing_mask is not None else False,
            wearing_glasses=bool(det.wearing_glasses) if det.wearing_glasses is not None else False,"""

if old_logs in logs:
    logs = logs.replace(old_logs, new_logs)
    with open('backend/routers/logs.py', 'w', encoding='utf-8') as f:
        f.write(logs)
    print("Updated backend/routers/logs.py")
else:
    print("WARNING: old_logs not found")
