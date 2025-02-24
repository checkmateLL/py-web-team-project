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
from app.services.password_service import PasswordResetService
from app.services.user_service import get_token_blacklist, UserService
from app.services.image_service import CloudinaryService
from app.database.models import User
from app.services.email_service import EmailService
from app.config import settings

router = APIRouter(prefix="/users", tags=["users"])
logger = logging.getLogger(__name__)


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
    """
    Get public profile information for any user.
    
    Retrieves non-sensitive profile information that is publicly viewable.
    
    Args:
        username (str): Username of the profile to retrieve.
        current_user (User): Currently authenticated user (from dependency).
        db (AsyncSession): Database session (from dependency).
        
    Returns:
        UserProfileResponse: Public profile information.
        
    Raises:
        HTTPException: 404 Not Found if user doesn't exist.
    """
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
    """
    Get full profile information for authenticated user.
    
    Retrieves complete profile information including private details
    for the currently authenticated user.
    
    Args:
        current_user (User): Currently authenticated user (from dependency).
        db (AsyncSession): Database session (from dependency).
        
    Returns:
        UserProfileFull: Complete profile information.
        
    Raises:
        HTTPException: 404 Not Found if profile doesn't exist.
    """
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
                        },
                        "incorrect_password": {
                            "value": {"detail": "Current password is incorrect"}
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
    token_blacklist = Depends(get_token_blacklist),
    email_service: EmailService = Depends(lambda: EmailService())
):
    """
    Update authenticated user's profile.
    
    Updates profile information for the currently authenticated user.
    If the email or password is changed, the current access token is blacklisted
    to force a logout.
    
    Args:
        profile_update (UserProfileEdit): Profile fields to update.
        response (Response): FastAPI response object.
        current_user (User): Currently authenticated user (from dependency).
        db (AsyncSession): Database session (from dependency).
        token (str): JWT token from Authorization header.
        token_blacklist: Token blacklist service.
        email_service (EmailService): Email service for notifications.
        
    Returns:
        UserProfileWithLogout: Updated profile information, potentially with logout flag.
        
    Raises:
        HTTPException:
            - 400 Bad Request for validation errors.
            - 404 Not Found if user doesn't exist.
            - 500 Internal Server Error for database or unexpected errors.
    """
    try:
        requires_logout = False
        logout_message = ""

        if not any([
            profile_update.username and profile_update.username != current_user.username,
            profile_update.email and profile_update.email != current_user.email,
            profile_update.bio is not None and profile_update.bio != current_user.bio,
            profile_update.new_password is not None
        ]):            
            profile = await crud_users.get_user_profile(current_user.username, db)
            return profile        
        
        if profile_update.new_password:            
            if not Hasher.verify_password(profile_update.current_password, current_user.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Current password is incorrect"
                )            
            
            password_hash = Hasher.get_password_hash(profile_update.new_password)
                        
            requires_logout = True
            logout_message = "Your password has been changed. Please log in again."
        else:
            password_hash = None
        
        if profile_update.username and profile_update.username != current_user.username:
            existing_user = await crud_users.get_user_by_username(profile_update.username, db)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
                
        if profile_update.email and profile_update.email != current_user.email:
            existing_user = await crud_users.exist_user(profile_update.email, db)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )            
            
            requires_logout = True
            logout_message = "Your email has been updated. Please log in again."
            
        updated_user = await crud_users.update_user_profile(
            user_id=current_user.id,
            session=db,
            username=profile_update.username,
            email=profile_update.email,
            password_hash=password_hash,
            bio=profile_update.bio
        )
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or update failed"
            )
                
        profile = await crud_users.get_user_profile(updated_user.username, db)
                    
        if requires_logout:
            await AuthService().logout_set(token=token, token_blacklist=token_blacklist)
            response.headers["X-Require-Logout"] = "true"
            profile["require_logout"] = True
            profile["message"] = logout_message
            
            try:
                await email_service.send_password_changed_email(updated_user.email)
            except Exception as e:
                logger.warning(f"Failed to send change notification email: {str(e)}")
        
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
    
@router.put(
        "/me/avatar",
        responses={
        200: {
            "description": "Avatar updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "avatar_url": "https://res.cloudinary.com/example/image/upload/avatars/user123.webp"
                    }
                }
            }
        },
        400: {
            "description": "Bad request",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_file_type": {
                            "value": {"detail": "Invalid file type. Only JPEG, PNG and WebP are allowed."}
                        },
                        "file_too_large": {
                            "value": {"detail": "File too large. Maximum size is 5MB"}
                        }
                    }
                }
            }
        },
        404: {"description": "User not found"},
        500: {"description": "Internal server error"},
        401: {"description": "Not authenticated"}
    }
)
async def update_avatar(
    file: UploadFile,
    current_user: User = role_deps.all_users(),
    db: AsyncSession = Depends(get_conn_db),
    cloudinary_service: CloudinaryService = Depends(lambda: CloudinaryService())
):
    """
    Update user's avatar.
    
    Uploads a new avatar image for the authenticated user and
    deletes the previous avatar if it exists.
    
    Args:
        file (UploadFile): Image file to use as avatar.
        current_user (User): Currently authenticated user (from dependency).
        db (AsyncSession): Database session (from dependency).
        cloudinary_service (CloudinaryService): Cloudinary service for image operations.
        
    Returns:
        dict: Contains the URL of the new avatar.
        
    Raises:
        HTTPException:
            - 400 Bad Request for invalid file type or size.
            - 404 Not Found if user doesn't exist.
            - 500 Internal Server Error for upload failures.
    """   
    user_service = UserService(db, cloudinary_service)
    
    try:
        result = await user_service.update_avatar(current_user.id, file)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Avatar update error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update avatar"
        )

@router.post(
    "/request-password-reset",
    responses={
        200: {
            "description": "Password reset request processed",
            "content": {
                "application/json": {
                    "example": {
                        "message": "If an account exists with that email, a password reset link will be sent."
                    }
                }
            }
        },
        500: {"description": "Internal server error"}
    }
)
async def request_password_reset(
    body: RequestEmail,
    db: AsyncSession = Depends(get_conn_db),
    email_service: EmailService = Depends(lambda: EmailService())
):
    """
    Request password reset with token generation and email.
    
    Generates a password reset token and sends it via email
    to the user's registered email address.
    
    Args:
        body (RequestEmail): Email address for password reset.
        db (AsyncSession): Database session (from dependency).
        email_service (EmailService): Email service for sending reset emails.
        
    Returns:
        dict: Success message.
        
    Raises:
        HTTPException: 500 Internal Server Error for processing failures.
        
    Notes:
        - Returns the same success message regardless of whether the email exists
          to prevent email enumeration attacks.
    """
    password_service = PasswordResetService(email_service)
    
    try:
        user = await crud_users.get_user_by_email(body.email, db)
        if not user:            
            return {
                "message": "If an account exists with that email, a password reset link will be sent."
            }
        
        reset_token = password_service.create_reset_token(user.email)
        
        await email_service.send_password_reset_email(
            email=user.email,
            token=reset_token
        )

        return {
            "message": "If an account exists with that email, a password reset link will be sent."
        }

    except Exception as e:
        logger.error(f"Password reset request error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process password reset request"
        )

@router.post(
    "/reset-password",
    responses={
        200: {
            "description": "Password reset successful",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Password successfully reset"
                    }
                }
            }
        },
        400: {
            "description": "Bad request",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_token": {
                            "value": {"detail": "Invalid or expired token"}
                        },
                        "password_too_short": {
                            "value": {"detail": "Password must be at least 6 characters long"}
                        }
                    }
                }
            }
        },
        404: {"description": "User not found"},
        500: {"description": "Internal server error"}
    }
)
async def reset_password(
    token: str,
    new_password: str,
    db: AsyncSession = Depends(get_conn_db),
    email_service: EmailService = Depends(lambda: EmailService())
):
    """
    Reset password with token verification and secure update.
    
    Verifies the password reset token, updates the user's password,
    and sends a confirmation email.
    
    Args:
        token (str): Password reset token from email.
        new_password (str): New password to set.
        db (AsyncSession): Database session (from dependency).
        email_service (EmailService): Email service for sending confirmation.
        
    Returns:
        dict: Success message.
        
    Raises:
        HTTPException:
            - 400 Bad Request for invalid token or password.
            - 404 Not Found if user doesn't exist.
            - 500 Internal Server Error for reset failures.
    """    
    password_service = PasswordResetService(email_service)
    
    try:     
        if len(new_password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters long"
            )
           
        email = password_service.verify_reset_token(token)
        
        user = await crud_users.get_user_by_email(email, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        hashed_password = Hasher.get_password_hash(new_password)
        await crud_users.update_user_profile(
            user_id=user.id,
            session=db,
            password_hash=hashed_password
        )
        
        await email_service.send_password_changed_email(user.email)

        return {"message": "Password successfully reset"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        )