import os
import re
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from auth import (
    CurrentUser,
    get_current_user,
    hash_password,
    log_audit,
    require_admin,
)
from config import IST
from database import get_db
from models import User, UserRole
from schemas import UserCreateRequest, UserResponse, UserUpdateRequest

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("", response_model=List[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    """List all registered system users (Administrator only)."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    res = [UserResponse.model_validate(u) for u in users]
    admin_usernames = {u.username for u in users}
    admin_env = os.environ.get("ADMIN_USERNAME", "admin")
    if admin_env not in admin_usernames and "admin" not in admin_usernames:
        res.insert(0, UserResponse(
            id="root-admin",
            username=admin_env,
            full_name="Root System Administrator",
            role="admin",
            is_active=True,
            created_at=datetime(2026, 1, 1),
            last_login=datetime.now(IST),
        ))
    return res


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    req: UserCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    """Create a new user with assigned role (Administrator only)."""
    username = req.username.strip()
    if not username or len(username) < 3 or len(username) > 64:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Username must be between 3 and 64 characters",
        )
    if not re.match(r"^[a-zA-Z0-9_\-\.]+$", username):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Username may only contain letters, numbers, underscores, dashes, and periods",
        )

    if not req.password or len(req.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 6 characters long",
        )

    try:
        assigned_role = UserRole(req.role) if req.role else UserRole.viewer
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid role '{req.role}'. Must be one of: viewer, operator, admin",
        )

    # Check for existing user with same username
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with username '{username}' already exists",
        )

    client_ip = request.client.host if request.client else None
    new_user = User(
        id=str(uuid.uuid4()),
        username=username,
        hashed_password=hash_password(req.password),
        full_name=req.full_name.strip() if req.full_name else None,
        role=assigned_role,
        is_active=bool(req.is_active) if req.is_active is not None else True,
        created_at=datetime.now(IST),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    log_audit(
        db=db,
        action="user.create",
        username=current_user.username,
        role=current_user.role,
        user_id=current_user.id,
        resource_type="user",
        resource_id=new_user.id,
        client_ip=client_ip,
        details=f"Created user '{new_user.username}' with role '{new_user.role.value}'",
    )

    return UserResponse.model_validate(new_user)


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Retrieve profile and assigned role of the currently logged-in user."""
    user = db.query(User).filter(User.username == current_user.username).first()
    if user:
        return UserResponse.model_validate(user)

    # Fallback representation for root admin or development tokens
    return UserResponse(
        id=current_user.id or "root-admin",
        username=current_user.username,
        full_name=current_user.full_name or "Administrator",
        role=current_user.role,
        is_active=True,
        created_at=None,
        last_login=None,
    )


@router.get("/{user_id}", response_model=UserResponse)
def get_user_details(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Retrieve details for a specific user (Admin or self)."""
    if not current_user.is_admin() and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot view other users' profiles",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse)
def update_user_profile(
    user_id: str,
    req: UserUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Update user information (Admin or self for name/password)."""
    is_self = current_user.id == user_id
    if not current_user.is_admin() and not is_self:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot modify other users' profiles",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if req.full_name is not None:
        user.full_name = req.full_name.strip() or None

    if req.password is not None:
        if len(req.password) < 6:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Password must be at least 6 characters long",
            )
        user.hashed_password = hash_password(req.password)

    if req.role is not None:
        if not current_user.is_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Only administrators can modify roles",
            )
        try:
            user.role = UserRole(req.role)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid role '{req.role}'. Must be one of: viewer, operator, admin",
            )

    if req.is_active is not None:
        if not current_user.is_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Only administrators can modify active status",
            )
        if is_self and req.is_active is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate your own account",
            )
        user.is_active = bool(req.is_active)

    db.commit()
    db.refresh(user)

    client_ip = request.client.host if request.client else None
    log_audit(
        db=db,
        action="user.update",
        username=current_user.username,
        role=current_user.role,
        user_id=current_user.id,
        resource_type="user",
        resource_id=user.id,
        client_ip=client_ip,
        details=f"Updated user '{user.username}'",
    )

    return UserResponse.model_validate(user)


@router.delete("/{user_id}")
def delete_user(
    user_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    """Delete a user account (Administrator only)."""
    if current_user.id == user_id or user_id == "root-admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account or the root administrator",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    deleted_username = user.username
    db.delete(user)
    db.commit()

    client_ip = request.client.host if request.client else None
    log_audit(
        db=db,
        action="user.delete",
        username=current_user.username,
        role=current_user.role,
        user_id=current_user.id,
        resource_type="user",
        resource_id=user_id,
        client_ip=client_ip,
        details=f"Deleted user '{deleted_username}'",
    )

    return {"deleted": True, "user_id": user_id, "username": deleted_username}
