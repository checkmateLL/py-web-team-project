# endponint from profile users and managment
from fastapi import APIRouter, Depends, HTTPException, status, Path, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from typing import Annotated, Optional
import logging

from app.database.connection import get_conn_db
from app.repository.users import crud_users
from app.schemas import UserProfileResponse, UserProfileEdit, UserProfileFull, UserProfileWithLogout
from app.services.security.auth_service import role_deps, AuthService
from app.services.security.secure_password import Hasher
from app.services.user_service import get_token_blacklist
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

@router.put("/me/profile", response_model=UserProfileWithLogout)
async def update_my_profile(
    profile_update: UserProfileEdit,
    response: Response,
    current_user: User = role_deps.all_users(),
    db: AsyncSession = Depends(get_conn_db),
    token: str = Depends(AuthService.get_token),
    token_blacklist = Depends(get_token_blacklist)   
):
    """
    Update authenticated user's profile.
    If the email is changed, the current access token is blacklisted to force a logout.
    """
    try:
        email_changed = False
        password_changed = False
        password_hash = None
        
        # Check if username is changing and if the new username is available.
        if profile_update.username and profile_update.username != current_user.username:
            existing_user = await crud_users.get_user_by_username(profile_update.username, db)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
        
        # Check if email is changing and ensure the new email is not already registered.
        if profile_update.email and profile_update.email != current_user.email:
            existing_user = await crud_users.exist_user(profile_update.email, db)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            email_changed = True

        if profile_update.password:
            password_hash = Hasher.get_password_hash(profile_update.password)
            password_changed = True

        # Update the user profile in the database.
        updated_user = await crud_users.update_user_profile(
            user_id=current_user.id,
            session=db,
            username=profile_update.username,
            email=profile_update.email,
            password_hash=password_hash,
            bio=profile_update.bio,
            avatar_url=profile_update.avatar_url
        )
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or update failed"
            )

        # Retrieve the updated profile data.
        profile = await crud_users.get_user_profile(updated_user.username, db)
        
        # Handle logout requirements
        if email_changed or password_changed:
            await AuthService().logout_set(token=token, token_blacklist=token_blacklist)
            response.headers["X-Require-Logout"] = "true"
            profile["require_logout"] = True
            
            # message based on what changed
            if email_changed and password_changed:
                profile["message"] = "Your email and password were updated. Please log in again with your new credentials."
            elif email_changed:
                profile["message"] = "Your email was updated. Please log in again with your new credentials."
            else:  
                profile["message"] = "Your password was updated. Please log in again with your new credentials."
        
        return profile
    
    except SQLAlchemyError as e:
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