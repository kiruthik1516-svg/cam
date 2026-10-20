import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, Form, File, UploadFile, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Profile, Embedding, Detection, Alert, CameraTransition,
    ProfileRole as ProfileRoleEnum, EmbeddingStatus as EmbeddingStatusEnum
)
from schemas import ProfileResponse, ProfileUpdateRequest, ProfileMergeRequest
from config import IST

router = APIRouter(prefix="/api/profiles", tags=["Profiles"])

@router.get("", response_model=list[ProfileResponse])
def get_profiles(db: Session = Depends(get_db)):
    """Get all profiles."""
    profiles = db.query(Profile).all()
    return [ProfileResponse.model_validate(p) for p in profiles]


@router.get("/{profile_id}", response_model=ProfileResponse)
def get_profile(profile_id: str, db: Session = Depends(get_db)):
    """Get a specific profile."""
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return ProfileResponse.model_validate(profile)


@router.post("", response_model=ProfileResponse)
async def create_profile(
    name: str = Form(...),
    role: Optional[str] = Form("visitor"),
    department: Optional[str] = Form(None),
    age: Optional[int] = Form(None),
    gender: Optional[str] = Form("unknown"),
    notes: Optional[str] = Form(None),
    photos: List[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """Enroll a new profile and extract face embeddings."""
    if not name or not name.strip():
        raise HTTPException(status_code=422, detail="Profile name cannot be empty")

    if photos:
        # Enrolling from photos needs the face model in this backend process. Fail clearly instead of
        # creating a profile that silently ends up with no embeddings.
        from state import ai_models
        if ai_models.get("detector") is None:
            raise HTTPException(
                status_code=503,
                detail="The face model is not loaded on this backend, so photos cannot be enrolled. "
                       "Set ENABLE_FORENSIC_SEARCH=true and restart the backend.",
            )

    try:
        profile_role = ProfileRoleEnum(role) if role else ProfileRoleEnum.visitor
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid profile role")

    new_id = str(uuid.uuid4())
    profile = Profile(
        id=new_id,
        name=name.strip(),
        role=profile_role,
        department=department.strip() if department else None,
        embedding_status=EmbeddingStatusEnum.pending,
        embedding_count=0,
        enrolled_at=datetime.now(IST)
    )
    db.add(profile)
    db.commit()

    if photos:
        from utils import extract_face_embedding
        for photo in photos:
            embedding = await extract_face_embedding(photo)
            if embedding is not None:
                emb_id = str(uuid.uuid4())
                # embedding is a 512-dim numpy array
                db_emb = Embedding(
                    id=emb_id,
                    profile_id=new_id,
                    vector=embedding.tolist()
                )
                db.add(db_emb)
                profile.embedding_count += 1
        
    if profile.embedding_count > 0:
        profile.embedding_status = EmbeddingStatusEnum.indexed
    else:
        profile.embedding_status = EmbeddingStatusEnum.missing
    db.commit()
            
    db.refresh(profile)
    return ProfileResponse.model_validate(profile)


@router.put("/{profile_id}", response_model=ProfileResponse)
def update_profile(profile_id: str, req: ProfileUpdateRequest, db: Session = Depends(get_db)):
    """Update editable profile metadata without changing stored embeddings."""
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    if req.name is not None:
        if not req.name.strip():
            raise HTTPException(status_code=422, detail="Profile name cannot be empty")
        profile.name = req.name.strip()
    if req.role is not None:
        try:
            profile.role = ProfileRoleEnum(req.role)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid profile role")
    if req.department is not None:
        profile.department = req.department.strip() or None
    db.commit()
    db.refresh(profile)
    return ProfileResponse.model_validate(profile)


@router.delete("/{profile_id}")
def delete_profile(
    profile_id: str,
    erase_biometrics: bool = Query(False, description="Also remove the face images and vectors stored in this person's past detections"),
    db: Session = Depends(get_db),
):
    """Delete a profile and its vectors. Historical detections are kept (unlinked), unless erase_biometrics=true."""
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    if erase_biometrics:
        db.query(Detection).filter(Detection.profile_id == profile_id).update(
            {"face_image": None, "embedding_vector": None}, synchronize_session=False
        )
    db.query(Detection).filter(Detection.profile_id == profile_id).update({"profile_id": None})
    db.query(Alert).filter(Alert.profile_id == profile_id).update({"profile_id": None})
    db.query(CameraTransition).filter(CameraTransition.profile_id == profile_id).delete(synchronize_session=False)
    db.query(Embedding).filter(Embedding.profile_id == profile_id).delete(synchronize_session=False)
    db.delete(profile)
    db.commit()
    return {"deleted": True, "profile_id": profile_id}


@router.delete("/{profile_id}/embeddings/{embedding_id}")
def delete_profile_embedding(profile_id: str, embedding_id: str, db: Session = Depends(get_db)):
    """Delete one stored vector and keep the profile count/status consistent."""
    embedding = db.query(Embedding).filter(
        Embedding.id == embedding_id,
        Embedding.profile_id == profile_id,
    ).first()
    if not embedding:
        raise HTTPException(status_code=404, detail="Embedding not found")
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    db.delete(embedding)
    if profile:
        profile.embedding_count = max(0, profile.embedding_count - 1)
        if profile.embedding_count == 0:
            profile.embedding_status = EmbeddingStatusEnum.missing
    db.commit()
    return {"deleted": True, "embedding_id": embedding_id, "profile_id": profile_id}


@router.delete("/{profile_id}/embeddings")
def delete_profile_embeddings(profile_id: str, db: Session = Depends(get_db)):
    """Remove all vectors for a profile without deleting the profile."""
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    deleted_count = db.query(Embedding).filter(Embedding.profile_id == profile_id).delete(synchronize_session=False)
    profile.embedding_count = 0
    profile.embedding_status = EmbeddingStatusEnum.missing
    db.commit()
    return {"deleted": True, "profile_id": profile_id, "deleted_count": deleted_count}


@router.post("/merge")
def merge_profiles(
    req: ProfileMergeRequest,
    db: Session = Depends(get_db)
):
    """Merge two profiles."""
    keep_id = req.keepProfile or req.keepProfileId or req.profileAId
    delete_id = req.profileBId if keep_id == req.profileAId else req.profileAId
    
    if not keep_id or not delete_id:
        raise HTTPException(status_code=400, detail="Two profiles are required to merge")
    if keep_id == delete_id:
        raise HTTPException(status_code=400, detail="Choose two different profiles to merge")
    if keep_id not in (req.profileAId, req.profileBId):
        raise HTTPException(status_code=400, detail="The profile to keep must be one of the two being merged")

    keep_profile = db.query(Profile).filter(Profile.id == keep_id).first()
    delete_profile = db.query(Profile).filter(Profile.id == delete_id).first()
    
    if not keep_profile or not delete_profile:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    # Re-assign foreign keys
    db.query(Detection).filter(Detection.profile_id == delete_id).update({"profile_id": keep_id})
    db.query(Embedding).filter(Embedding.profile_id == delete_id).update({"profile_id": keep_id})
    db.query(Alert).filter(Alert.profile_id == delete_id).update({"profile_id": keep_id})
    db.query(CameraTransition).filter(CameraTransition.profile_id == delete_id).update({"profile_id": keep_id})
    db.flush()

    # Recount from the vectors actually attached (adding the two stored counts can drift)
    keep_profile.embedding_count = db.query(Embedding).filter(Embedding.profile_id == keep_id).count()
    keep_profile.embedding_status = (
        EmbeddingStatusEnum.indexed if keep_profile.embedding_count > 0 else EmbeddingStatusEnum.missing
    )
    
    db.delete(delete_profile)
    db.commit()
    
    return {
        "merged": True,
        "keptProfileId": keep_id,
        "deletedProfileId": delete_id
    }
