# endponint from profile users and managment
from fastapi import APIRouter, Depends, HTTPException, status, Path, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from typing import Annotated, Optional
import logging

from app.database.connection import get_conn_db
from app.repository.users import crud_users
from app.schemas import UserProfileResponse, UserProfileEdit, UserProfileFull
from app.services.security.auth_service import role_deps
from app.database.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])

@router.get(
    "/{username}", 
    response_model=UserProfileResponse,
    responses={
        404: {"description": "User not found"},
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "username": "john_doe",
                        "created_at": "2024-02-21T12:00:00",
                        "total_images": 42,
                        "total_comments": 156,
                        "total_ratings_given": 89,
                        "member_since": "1 year and 3 months",
                        "avatar_url": "https://example.com/avatar.jpg",
                        "bio": "Python developer and photographer"
                    }
                }
            }
        }
    }
)
async def get_user_profile(
    username: str = Path(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$"),
    current_user: User = role_deps.all_users(),
    db: AsyncSession = Depends(get_conn_db)
):
    """Get public profile information for any user"""
    profile = await crud_users.get_user_profile(username, db)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return profile

@router.get("/me/profile", response_model=UserProfileFull)
async def get_my_profile(
    current_user: User = role_deps.all_users(),
    db: AsyncSession = Depends(get_conn_db)
):
    """Get full profile information for authenticated user"""
    profile = await crud_users.get_user_profile(current_user.username, db)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    return profile

@router.put("/me/profile", response_model=UserProfileFull)
async def update_my_profile(
    profile_update: UserProfileEdit,
    response: Response,
    current_user: User = role_deps.all_users(),
    db: AsyncSession = Depends(get_conn_db)    
):
    """Update authenticated user's profile with auto-logout on email change"""
    try:
        email_changed = False
        
        # Check if username is taken if trying to change it
        if profile_update.username and profile_update.username != current_user.username:
            existing_user = await crud_users.get_user_by_username(profile_update.username, db)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )

        # Check if email is changing
        if profile_update.email and profile_update.email != current_user.email:
            existing_user = await crud_users.exist_user(profile_update.email, db)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            email_changed = True

        # Attempt to update the profile
        updated_user = await crud_users.update_user_profile(
            user_id=current_user.id,
            username=profile_update.username,
            email=profile_update.email,
            bio=profile_update.bio,
            avatar_url=profile_update.avatar_url,
            session=db
        )
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or update failed"
            )

        # Get full profile data
        profile = await crud_users.get_user_profile(updated_user.username, db)
        
        # If email was changed, set header to trigger logout
        if email_changed:
            # Add a custom header to indicate logout is needed
            response.headers["X-Require-Logout"] = "true"
            
            # Add a message to the profile response
            if hasattr(profile, "__dict__"):
                profile_dict = dict(profile.__dict__)
            else:
                # Handle Pydantic models or regular dicts
                profile_dict = profile.dict() if hasattr(profile, 'dict') else dict(profile)
                
            profile_dict["require_logout"] = True
            profile_dict["message"] = "Your email was updated. Please log in again with your new credentials."
            return profile_dict
            
        return profile
    
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )
