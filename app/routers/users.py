# endponint from profile users and managment
from fastapi import APIRouter, Depends, HTTPException, status, Path, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from typing import Annotated, Optional
from pydantic import EmailStr
import logging
import magic
from jose import jwt, JWTError
from datetime import datetime, timedelta


from app.database.connection import get_conn_db
from app.repository.users import crud_users
from app.repository import users as repository_users
from app.schemas import UserProfileResponse, UserProfileEdit, UserProfileFull, UserProfileWithLogout, RequestEmail
from app.services.security.auth_service import role_deps, AuthService
from app.services.security.secure_password import Hasher
from app.services.user_service import get_token_blacklist
from app.services.image_service import CloudinaryService
from app.database.models import User
from app.services.email_service import EmailService
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])

cloudinary_service = CloudinaryService()

email_service = EmailService()

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

@router.get(
        "/me/profile",
        response_model=UserProfileFull,
        responses={
            200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "username": "john_doe",
                        "email": "john@example.com",
                        "created_at": "2024-02-21T12:00:00",
                        "total_images": 42,
                        "total_comments": 156,
                        "total_ratings_given": 89,
                        "member_since": "1 year and 3 months",
                        "avatar_url": "https://example.com/avatar.jpg",
                        "bio": "Python developer and photographer",
                        "is_active": True,
                        "role": "user",
                        "id": 1
                    }
                }
            }
        },
        404: {"description": "Profile not found"},
        401: {"description": "Not authenticated"}
    }
)

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

@router.put(
        "/me/profile",
        response_model=UserProfileWithLogout,
        responses={
        200: {
            "description": "Profile updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "username": "john_doe",
                        "email": "john@example.com",
                        "created_at": "2024-02-21T12:00:00",
                        "total_images": 42,
                        "total_comments": 156,
                        "total_ratings_given": 89,
                        "member_since": "1 year and 3 months",
                        "avatar_url": "https://example.com/avatar.jpg",
                        "bio": "Python developer and photographer",
                        "is_active": True,
                        "role": "user",
                        "id": 1,
                        "require_logout": True,
                        "message": "Your email was updated. Please log in again with your new credentials."
                    }
                }
            }
        },
        400: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "examples": {
                        "username_taken": {
                            "value": {"detail": "Username already taken"}
                        },
                        "email_taken": {
                            "value": {"detail": "Email already registered"}
                        }
                    }
                }
            }
        },
        404: {"description": "User not found or update failed"},
        401: {"description": "Not authenticated"},
        500: {"description": "Internal server error"}
    }
)

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
    
async def validate_image_file(file: UploadFile):
    """Validate that the uploaded file is an image"""
    # Read first 2048 bytes for MIME detection
    first_bytes = await file.read(2048)
    # Reset file pointer
    await file.seek(0)
    
    mime = magic.Magic(mime=True)
    mime_type = mime.from_buffer(first_bytes)
    
    if not mime_type.startswith('image/'):
        raise HTTPException(
            status_code=400,
            detail="File must be an image"
        )
    
    # Limit file size to 5MB
    if len(first_bytes) > 5 * 1024 * 1024:  # 5MB
        raise HTTPException(
            status_code=400,
            detail="File size too large. Maximum size is 5MB"
        )

@router.put("me/avatar")
async def update_avatar(
    file: UploadFile,
    current_user: User = role_deps.all_users(),
    db: AsyncSession = Depends(get_conn_db)
):
    await validate_image_file(file)
    
    if current_user.avatar_url:        
        public_id = current_user.avatar_url.split("/")[-1].split(".")[0]
        await cloudinary_service.delete_avatar(public_id)

    upload_result = await cloudinary_service.upload_avatar(file)    
    
    await crud_users.update_user_profile(
        user_id=current_user.id,
        session=db,
        avatar_url=upload_result["secure_url"]
    )
    
    return {"avatar_url": upload_result["secure_url"]}

@router.post("/request-password-reset", response_model=dict)
async def request_password_reset(
    body: RequestEmail,
    db: AsyncSession = Depends(get_conn_db)
) -> dict:
    """Request password reset by email"""
    try:
        # Check if user exists
        user = await repository_users.get_user_by_email(body.email, db)
        if not user:
            # Return same message even if user doesn't exist (security best practice)
            return {"message": "If an account exists with that email, a password reset link will be sent."}

        # Generate reset token using your existing auth service
        reset_token = await AuthService().generate_reset_token(user.email)

        # Send reset email using your existing email service
        await email_service.send_password_reset_email(
            email=user.email,
            token=reset_token
        )
        
        return {"message": "If an account exists with that email, a password reset link will be sent."}

    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/reset-password", response_model=dict)
async def reset_password(
    token: str,
    new_password: str,
    db: AsyncSession = Depends(get_conn_db)
) -> dict:
    """Reset user password using reset token"""
    try:
        # Verify token
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        # Verify token type
        if payload.get("type") != "password_reset":
            raise HTTPException(status_code=400, detail="Invalid token type")
            
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=400, detail="Invalid token")

        user = await crud_users.get_user_by_email(email, db)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Update password
        await crud_users.update_user_profile(
            user_id=user.id,
            session=db,
            password_hash=Hasher.get_password_hash(new_password)
        )

        # Send confirmation email
        await EmailService().send_password_changed_email(user.email)
        
        return {"message": "Password successfully reset"}
        
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        )