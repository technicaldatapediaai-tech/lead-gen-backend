"""
User and Organization API routes.
"""
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.database import get_session
from backend.services.user_service import UserService
from backend.schemas.user import UserResponse, UserUpdate, OrganizationResponse, OrganizationUpdate
from backend.api.deps import get_current_user
from backend.models.user import User, OrganizationMember

router = APIRouter(tags=["users"])


# User endpoints
@router.get("/api/users/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get current user profile with role in current organization."""
    # Get role from OrganizationMember
    role = None
    if current_user.current_org_id:
        query = select(OrganizationMember).where(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.org_id == current_user.current_org_id
        )
        result = await session.exec(query)
        membership = result.first()
        if membership:
            role = membership.role
    
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        avatar_url=current_user.avatar_url,
        is_verified=current_user.is_verified,
        current_org_id=current_user.current_org_id,
        role=role,
        created_at=current_user.created_at,
        last_login_at=current_user.last_login_at
    )


@router.patch("/api/users/me", response_model=UserResponse)
async def update_current_user_profile(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update current user profile."""
    user_service = UserService(session)
    updated_user = await user_service.update_profile(
        current_user.id,
        full_name=update_data.full_name,
        avatar_url=update_data.avatar_url
    )
    
    # Get role
    role = None
    if updated_user.current_org_id:
        query = select(OrganizationMember).where(
            OrganizationMember.user_id == updated_user.id,
            OrganizationMember.org_id == updated_user.current_org_id
        )
        result = await session.exec(query)
        membership = result.first()
        if membership:
            role = membership.role
    
    return UserResponse(
        id=updated_user.id,
        email=updated_user.email,
        full_name=updated_user.full_name,
        avatar_url=updated_user.avatar_url,
        is_verified=updated_user.is_verified,
        current_org_id=updated_user.current_org_id,
        role=role,
        created_at=updated_user.created_at,
        last_login_at=updated_user.last_login_at
    )


# User Settings endpoints
@router.get("/api/users/me/settings")
async def get_user_settings(
    current_user: User = Depends(get_current_user)
):
    """Get current user settings."""
    return {
        "language_preference": current_user.language_preference,
        "timezone": current_user.timezone,
        "email_preferences": current_user.email_preferences or {}
    }


@router.patch("/api/users/me/settings")
async def update_user_settings(
    settings: dict,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update current user settings."""
    # Update settings fields
    if "language_preference" in settings:
        current_user.language_preference = settings["language_preference"]
    if "timezone" in settings:
        current_user.timezone = settings["timezone"]
    if "email_preferences" in settings:
        current_user.email_preferences = settings["email_preferences"]
    
    current_user.updated_at = datetime.utcnow()
    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)
    
    return {
        "language_preference": current_user.language_preference,
        "timezone": current_user.timezone,
        "email_preferences": current_user.email_preferences or {}
    }


@router.get("/api/users/me/activity")
async def get_user_activity(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    limit: int = 50
):
    """Get user activity logs."""
    from backend.models.activity import ActivityLog
    
    query = select(ActivityLog).where(
        ActivityLog.actor_id == current_user.id
    ).order_by(ActivityLog.created_at.desc()).limit(limit)
    
    result = await session.exec(query)
    activities = result.all()
    
    return {
        "items": [
            {
                "id": str(activity.id),
                "action": activity.action,
                "entity_type": activity.entity_type,
                "entity_id": str(activity.entity_id) if activity.entity_id else None,
                "description": activity.description,
                "meta_data": activity.meta_data,
                "ip_address": activity.ip_address,
                "user_agent": activity.user_agent,
                "created_at": activity.created_at.isoformat()
            }
            for activity in activities
        ],
        "total": len(activities)
    }


# Organization endpoints
@router.get("/api/org/", response_model=OrganizationResponse)
async def get_organization(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get current user's organization."""
    user_service = UserService(session)
    return await user_service.get_organization(current_user.current_org_id)


@router.patch("/api/org/profile", response_model=OrganizationResponse)
async def update_organization_profile(
    update_data: OrganizationUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update organization profile."""
    user_service = UserService(session)
    return await user_service.update_organization(
        current_user.current_org_id,
        current_user.id,
        update_data.model_dump(exclude_unset=True)
    )
