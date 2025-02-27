from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status, Path, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.utils.logger import logger
from app.database.connection import get_conn_db
from app import schemas as sch
from app.services.security.auth_service import role_deps
from app.services.user_service import  UserService
from app.services.image_service import CloudinaryService
from app.database.models import User
from app.repository.users import crud_users
from app.services.email_service import email_service as ems
from app.services.security.secure_token.manager import token_manager, TokenType
from app.services.security.secure_password import Hasher

router = APIRouter(prefix="/users", tags=["users"])

@router.get(
    "/{username}", 
    response_model=sch.UserProfileResponse,
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
    _: User = role_deps.all_users(),
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
        response_model=sch.UserProfileFull,
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
        response_model=sch.UserProfileWithLogout,
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
    profile_update: sch.UserProfileEdit,
    current_user: User = role_deps.all_users(),
    db: AsyncSession = Depends(get_conn_db)
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
        if not any([
            profile_update.username and profile_update.username != current_user.username,
            profile_update.bio is not None and profile_update.bio != current_user.bio,

        ]):            
            profile = await crud_users.get_user_profile(current_user.username, db)
            return profile        
                
        if profile_update.username and profile_update.username != current_user.username:
            existing_user = await crud_users.get_user_by_username(profile_update.username, db)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
                
            
        updated_user = await crud_users.update_user_profile(
            user_id=current_user.id,
            session=db,
            username=profile_update.username,   
            bio=profile_update.bio
        )
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or update failed"
            )
                
        profile = await crud_users.get_user_profile(updated_user.username, db)
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

@router.post('/forgot_email')
async def forgot_email(
    email,
    request: Request,
    bt: BackgroundTasks,
    session = Depends(get_conn_db)
    ):
    """
    User forgot email, change email process.
    """
    curent_user = await crud_users.get_user_by_email(email, session)

    if not curent_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    bt.add_task(ems.send_email_change_user_email, curent_user, str(request.base_url))
    return {
        'message': 
        'Processing sending email'
        }

@router.post('/reset-email')
async def reset_email(
    request:Request,
    bt: BackgroundTasks,
    current_user: User = role_deps.all_users()
    ):
    """
    Send email to reset user_email.
    """
    bt.add_task(
        ems.send_email_change_user_email, 
        current_user, 
        str(request.base_url)
    )
    return {
        'message': 
        'Processing sending email'
        }

@router.post('/reset_email')
async def change_email(
    token: str,
    body: sch.EmailSchemaUpdate,
    session = Depends(get_conn_db)):
    """
    Confirn and change user_email to new user_email
    """
    payload = await token_manager.decode_token(
        TokenType.RESET_EMAIL, token
    )
    if not payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired token"
            )
    
    flag = await crud_users.get_user_by_email(body.new_email, session)
    if flag:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='User already exists'
        )
    current_user_email = payload.get('sub')
    updated_user = await crud_users.change_email(
        current_user_email, 
        body.new_email, 
        session
    )

    return {
        'message': 'Email updated successfully',
        'new_email': updated_user.email
    }

@router.get('/confirm_email/{token}')
async def change_email_confirm_token(token: str):
    """
    Check token from change email. Redirect on post router.
    """
    try:
        payload = await token_manager.decode_token(
            TokenType.RESET_EMAIL, token
        )
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid or expired token'
            )
        
        return {
            "status": "success",
            "message": "Token is valid",
            "email": payload.get('sub'),
            "redirect_to": "app/users/reset_email",
            "token": token
        }
    
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to vetify token: {str(err)}'
        )


@router.post('/reset-password')
async def reset_password(
    body: sch.UserEmail,
    request:Request,
    bt: BackgroundTasks,
    session = Depends(get_conn_db),
    _:User = role_deps.all_users()
    ):
    """
    Send email to reset user_password.
    """
    curent_user = await crud_users.get_user_by_email(body.user_email, session)

    if not curent_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    bt.add_task(ems.send_password_reset_email, curent_user, str(request.base_url))
    return {
        'message': 
        'Processing sending email'
        }

@router.post('/password-forgot')
async def password_forgot(
    email,
    request:Request,
    bt: BackgroundTasks,
    session = Depends(get_conn_db)
    ):
    """
    User forgot password, send email.
    """
    curent_user = await crud_users.get_user_by_email(email, session)

    if not curent_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    bt.add_task(ems.send_password_reset_email, curent_user, str(request.base_url))
    return {
        'message': 
        'Processing sending email'
        }

@router.get('/reset_password/{token}')
async def change_password_confirm_token(
    token: str
):
    """
    Check token from change password. Redirect on poser router.
    """
    try:
        payload = await token_manager.decode_token(
            TokenType.RESET_PASSWORD, token
        )
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid or expired token'
            )
        
        return {
            "status": "success",
            "message": "Token is valid",
            "email": payload.get('sub'),
            "redirect_to": "app/users/reset-password"
        }
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to vetify token: {str(err)}'
        )
    
@router.post('/change_password')
async def change_password(
    token: str,
    body: sch.ChangePasswordRequest,
    session = Depends(get_conn_db)):
    """
    Confirn and change user_password to new password
    """
    payload = await token_manager.decode_token(
        TokenType.RESET_PASSWORD, token
    )
    if not payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired token"
            )
    try:
        
        user_email = payload.get('sub')
        if not user_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired token"
            )
        user = await crud_users.get_user_by_email(user_email, session)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if Hasher.verify_password(body.new_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from the old password"
            )
        
        hashed_password = Hasher.get_password_hash(body.new_password)
        await crud_users.update_user_profile(
            user_id=user.id,
            session=session,
            password_hash=hashed_password
        )

        return {
            'message': 'Password updated successfully',
            'email': user.email
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
    )
