from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    status,
    Path,
    UploadFile,
)
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.utils.logger import logger
from app.database.connection import get_conn_db
from app import schemas as sch
from app.services.security.auth_service import role_deps, auth_service
from app.services.user_service import UserService, get_token_blacklist
from app.services.image_service import CloudinaryService
from app.database.models import User
from app.repository.users import crud_users
from app.services.email_service import email_service as ems
from app.services.security.secure_token.manager import token_manager, TokenType
from app.services.security.secure_password import Hasher
from app.utils.rate_limit import rate_limited

router = APIRouter(prefix="/users")


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
                        "bio": "Python developer and photographer",
                    }
                }
            },
        },
    },
)
async def get_user_profile(
    username: str = Path(
        ...,
        min_length=sch.USERNAME_MIN_LENGTH,
        max_length=sch.USERNAME_MAX_LENGTH,
        pattern=sch.USERNAME_PATTERN,
    ),
    _: User = role_deps.all_users(),
    db: AsyncSession = Depends(get_conn_db),
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
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
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
                        "id": 1,
                    }
                }
            },
        },
        404: {"description": "Profile not found"},
        401: {"description": "Not authenticated"},
    },
)
async def get_my_profile(
    current_user: User = role_deps.all_users(), db: AsyncSession = Depends(get_conn_db)
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
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
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
                        "message": "Your email was updated. Please log in again with your new credentials.",
                    }
                }
            },
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
                        },
                    }
                }
            },
        },
        404: {"description": "User not found or update failed"},
        401: {"description": "Not authenticated"},
        500: {"description": "Internal server error"},
    },
)
async def update_my_profile(
    profile_update: sch.UserProfileEdit,
    current_user: User = role_deps.all_users(),
    db: AsyncSession = Depends(get_conn_db),
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
        if not any(
            [
                profile_update.username
                and profile_update.username != current_user.username,
                profile_update.bio is not None
                and profile_update.bio != current_user.bio,
            ]
        ):
            profile = await crud_users.get_user_profile(current_user.username, db)
            return profile

        if profile_update.username and profile_update.username != current_user.username:
            existing_user = await crud_users.get_user_by_username(
                profile_update.username, db
            )
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken",
                )

        updated_user = await crud_users.update_user_profile(
            user_id=current_user.id,
            session=db,
            username=profile_update.username,
            bio=profile_update.bio,
        )

        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or update failed",
            )

        profile = await crud_users.get_user_profile(updated_user.username, db)
        return profile

    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred",
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
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
            },
        },
        400: {
            "description": "Bad request",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_file_type": {
                            "value": {
                                "detail": "Invalid file type. Only JPEG, PNG and WebP are allowed."
                            }
                        },
                        "file_too_large": {
                            "value": {"detail": "File too large. Maximum size is 5MB"}
                        },
                    }
                }
            },
        },
        404: {"description": "User not found"},
        500: {"description": "Internal server error"},
        401: {"description": "Not authenticated"},
    },
)
async def update_avatar(
    file: UploadFile,
    current_user: User = role_deps.all_users(),
    db: AsyncSession = Depends(get_conn_db),
    cloudinary_service: CloudinaryService = Depends(lambda: CloudinaryService()),
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
            detail="Failed to update avatar",
        )


@router.post("/reset-email-send")
@rate_limited(max_calls=settings.RL_TIMES_EMAIL, time_frame=settings.RL_TIMES_EMAIL)
async def send_email_reset_user_email(
    request: Request,
    bt: BackgroundTasks,
    current_user: User = role_deps.all_users(),
):
    """
    Initiates the email reset process by sending a confirmation email to the user.

    This endpoint triggers an email to be sent to the user with a link to reset
    their email address.
    The request is rate-limited to 1 request per minute to prevent abuse.

    Parameters:
    - request (Request): The FastAPI Request object, used to generate the base
    URL for the confirmation link.
    - bt (BackgroundTasks): A FastAPI BackgroundTasks instance used to send the confirmation email asynchronously.
    - current_user (User): The current authenticated user requesting the email
    change.
    - rate_limiter (RateLimiter): A rate limiter that allows only 1 request per
    minute.

    Returns:
    - dict: A message confirming that the email change request is being processed and the confirmation email has been sent.

    Example response:
    {
        "message": "Email change request is being processed. A confirmation email has been sent."
    }
    """
    bt.add_task(ems.send_email_change_user_email, current_user, str(request.base_url))
    return {
        "message": "Email change request is being processed. A confirmation email has been sent."
    }


@router.post("/change-email")
@rate_limited(
    max_calls=settings.RL_TIMES_CHANGE_SET, time_frame=settings.RL_TIMES_CHANGE_SET
)
async def change_email(
    request: Request,
    token: str,
    body: sch.EmailSchemaUpdate,
    session=Depends(get_conn_db),
    token_blacklist=Depends(get_token_blacklist),
):
    """
    Confirm and change user email to a new one, and add the token to the blacklist.

    This endpoint is used to change the user's email address. It validates the provided token,
    checks if the new email is already in use, and updates the email if valid. The token is added
    to the blacklist to prevent reuse.

    Parameters:
    - token (str): The token used to confirm the email change request.
    - body (EmailSchemaUpdate): The new email address that the user wants to set.
    - session: Database session dependency.
    - token_blacklist: A dependency that checks if the token is blacklisted.
    - rate_limiter (RateLimiter): A rate limiter that allows up to 5 requests per minute.

    Returns:
    - dict: A message confirming the email update and the new email address.

    Example response:
    {
        "message": "Email updated successfully",
        "new_email": "newemail@example.com"
    }

    Raises:
    - HTTPException: If the token is invalid, expired, or already blacklisted.
    - HTTPException: If the new email is already registered in the system.
    """
    payload = await auth_service.added_resets_email_token_blacklist(
        token, token_blacklist
    )
    flag = await crud_users.get_user_by_email(body.new_email, session)
    if flag:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists"
        )
    current_user_email = payload.get("sub")
    await crud_users.change_email(current_user_email, body.new_email, session)
    auth_header = request.headers.get("Autorization")
    if auth_header and auth_header.startswith("Bearer"):
        access_token = auth_header.split(" ")[1]
        await auth_service.added_access_token_blacklist(access_token, token_blacklist)
    return {"status": "correct", "message": "login with new password"}
    # return RedirectResponse(url='/app/auth/login')


@router.get("/confirm-email/{token}")
async def change_email_confirm_token(token: str):
    """
    Confirm the validity of the email change token.

    This endpoint checks if the provided token is valid and not expired. If the
    token is valid,
    it returns a success message along with the associated email and a
    redirection URL.
    If the token is invalid or expired, an error is raised.

    Parameters:
    - token (str): The token that was provided to confirm the email change request.

    Returns:
    - dict: A message indicating the validity of the token, the associated email,
    and a redirect URL.

    Example response:
    {
        "status": "success",
        "message": "Token is valid",
        "email": "user@example.com",
        "redirect_to": "app/users/change-email",
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkaW1hY2hlYmFuMjNAbWV0YS51YSIsImV4cCI6MTc0MDY0MTE0Nywic2NvcGUiOiJyZXNldF9lbWFpbF90b2tlbiJ9.CaHZt8eeZuZK7ufrNZHVJRfZZ172B413-QkGlfL5UV"
    }

    Raises:
    - HTTPException: If the token is invalid or expired (400 Bad Request).
    - HTTPException: If there is an internal server error while processing the
    token (500 Internal Server Error).
    """
    try:
        payload = await token_manager.decode_token(TokenType.RESET_EMAIL, token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired token",
            )

        return {
            "status": "success",
            "message": "Token is valid",
            "email": payload.get("sub"),
            "redirect_to": "app/users/change-email",
            "token": token,
        }

    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to vetify token: {str(err)}",
        )


@router.post("/reset-password-send")
@rate_limited(max_calls=settings.RL_TIMES_EMAIL, time_frame=settings.RL_TIMES_EMAIL)
async def reset_password(
    request: Request,
    body: sch.UserEmail,
    bt: BackgroundTasks,
    session=Depends(get_conn_db),
    _: User = role_deps.all_users(),
):
    """
    Send a password reset email to the user.

    This endpoint triggers the sending of a password reset email to the user, if the provided
    email exists in the system. If the user does not exist, a 404 error is raised.

    Parameters:
    - body (UserEmail): The email address of the user requesting the password reset.
    - request (Request): The FastAPI Request object, used to construct the base URL for the reset link.
    - bt (BackgroundTasks): Used to send the email asynchronously in the background.
    - session: Database session dependency for fetching user data.
    - _ (User): The current user role, ensuring that the request is coming from a valid user.
    - rate_limiter (RateLimiter): A rate limiter to prevent abuse (1 request per minute).

    Returns:
    - dict: A message indicating the processing of the email sending.

    Example response:
    {
        "message": "Password change request is being processed. A confirmation email has been sent."
    }

    Raises:
    - HTTPException: If the user is not found (404 Not Found).
    """
    curent_user = await crud_users.get_user_by_email(body.user_email, session)

    if not curent_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    bt.add_task(ems.send_password_reset_email, curent_user, str(request.base_url))
    return {
        "message": "Password change request is being processed. A confirmation email has been sent."
    }


@router.post("/password-forgot")
@rate_limited(max_calls=settings.RL_TIMES_EMAIL, time_frame=settings.RL_MINUTES_EMAIL)
async def password_forgot(
    request: Request,
    email,
    bt: BackgroundTasks,
    session=Depends(get_conn_db),
):
    """
    Send a password reset email when the user has forgotten their password.

    This endpoint triggers the sending of a password reset email to the user. If the provided
    email does not exist in the system, a 404 error is raised.

    Parameters:
    - email (str): The email address of the user who has forgotten their password.
    - request (Request): The FastAPI Request object, used to construct the base URL for the reset link.
    - bt (BackgroundTasks): Used to send the email asynchronously in the background.
    - session: Database session dependency for fetching user data.
    - rate_limiter (RateLimiter): A rate limiter to prevent abuse (1 request per minute).

    Returns:
    - dict: A message indicating the password reset email has been sent.

    Example response:
    {
        "message": "Password change request is being processed. A confirmation email has been sent."
    }

    Raises:
    - HTTPException: If the user is not found (404 Not Found).
    """
    curent_user = await crud_users.get_user_by_email(email, session)

    if not curent_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    bt.add_task(ems.send_password_reset_email, curent_user, str(request.base_url))
    return {
        "message": "Password change request is being processed. A confirmation email has been sent."
    }


@router.get("/reset-password/{token}")
async def change_password_confirm_token(token: str):
    """
    Confirm the password reset token. If valid, redirect to the reset password page.

    This endpoint checks the validity of the provided password reset token. If the token is valid,
    it returns the user's email and redirects to the password reset page. If the token is invalid or expired,
    a 400 error is raised.

    Parameters:
    - token (str): The password reset token to be verified.

    Returns:
    - dict: A response containing the status, message, user's email, and a redirect link to the password reset page.

    Example response:
    {
        "status": "success",
        "message": "Token is valid",
        "email": "user@example.com",
        "redirect_to": "app/users/reset-password"
    }

    Raises:
    - HTTPException: If the token is invalid or expired (400 Bad Request).
    - HTTPException: If there is an internal server error (500 Internal Server Error).
    """
    try:
        payload = await token_manager.decode_token(TokenType.RESET_PASSWORD, token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired token",
            )

        return {
            "status": "success",
            "message": "Token is valid",
            "email": payload.get("sub"),
            "redirect_to": "app/users/reset-password",
            "token": token,
        }
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to vetify token: {str(err)}",
        )


@router.post("/change-password")
@rate_limited(
    max_calls=settings.RL_TIMES_CHANGE_SET, time_frame=settings.RL_MINUTES_CHANGE_SET
)
async def change_password(
    request: Request,
    token: str,
    body: sch.ChangePasswordRequest,
    session=Depends(get_conn_db),
    token_blacklist=Depends(get_token_blacklist),
):
    """
    Confirm and change user password to a new password.

    The new password must meet the following requirements:
    - At least 6 characters long
    - Contains at least one digit
    - Contains at least one uppercase letter
    - Maximum 100 characters

    This endpoint verifies the provided token, ensures that the token is valid and not blacklisted,
    and allows the user to update their password. The new password must be different from the old one.

    Parameters:
    - token (str): The password reset token for verification.
    - body (ChangePasswordRequest): The new password provided by the user.

    Returns:
    - dict: A response indicating whether the password was successfully updated.

    Example response:
    {
        "message": "Password updated successfully",
        "email": "user@example.com"
    }

    Raises:
    - HTTPException:
        - 400 Bad Request if the token is invalid, expired, or the new password is the same as the old password.
        - 404 Not Found if the user is not found.
        - 500 Internal Server Error if an unexpected error occurs.
    """
    payload = await auth_service.added_resets_password_token_blacklist(
        token, token_blacklist
    )
    try:

        user_email = payload.get("sub")
        if not user_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired token",
            )
        user = await crud_users.get_user_by_email(user_email, session)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        if Hasher.verify_password(body.new_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from the old password",
            )

        hashed_password = Hasher.get_password_hash(body.new_password)
        await crud_users.update_user_profile(
            user_id=user.id, session=session, password_hash=hashed_password
        )

        auth_header = request.headers.get("Autorization")
        if auth_header and auth_header.startswith("Bearer"):
            access_token = auth_header.split(" ")[1]
            await auth_service.added_access_token_blacklist(
                access_token, token_blacklist
            )

        return {"status": "correct", "message": "login with new password"}
        # return RedirectResponse(url='/app/auth/login')

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password",
        )
