from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from fastapi.responses import RedirectResponse
from datetime import datetime

from app.database.models import User
from app.services.security.auth_service import role_deps
from app.repository.users import crud_users
from app.database.connection import get_conn_db
import app.schemas as sch
from app.repository.images import crud_images
from app.repository.ratings import crud_ratings

router = APIRouter(prefix='/admin_panel')

@router.put(
        '/ban-user/{user_id}',
        status_code=status.HTTP_200_OK,
        responses={
        200: {
            "description": "User is already deactivated",
            "content": {
                "application/json": {
                    "example": {
                        "message": "User is already deactivated",
                        "user": {
                            "id": 1,
                            "username": "john_doe",
                            "is_active": False
                        }
                    }
                }
            }
        },
        204: {
            "description": "User successfully deactivated",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "username": "john_doe",
                        "is_active": False
                    }
                }
            }
        },
        404: {"description": "User not found"},
        500: {"description": "Database error occurred"},
        403: {"description": "Forbidden. Only admin can perform this action"}
    }
)
async def desactivate_user(
    user_id:int = Path(..., description='ID of the user to deactivate', gt=0),
    session : AsyncSession = Depends(get_conn_db),
    _ : User = role_deps.admin_only()
):
    """
    Deactivate a user by settings 'is_active' to False

    - **user_id**: ID if the user to deactivate
    - **Requires admin previleges**:
    """
    result = await crud_users.desactivate_user(user_id, session)
    if isinstance (result, dict):
        return result
    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )


@router.put(
        '/unban-user/{user_id}',
        status_code=status.HTTP_200_OK,
        responses={
        200: {
            "description": "User is already activated",
            "content": {
                "application/json": {
                    "example": {
                        "message": "User is already activated",
                        "user": {
                            "id": 1,
                            "username": "john_doe",
                            "is_active": True
                        }
                    }
                }
            }
        },
        204: {
            "description": "User successfully activated",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "username": "john_doe",
                        "is_active": True
                    }
                }
            }
        },
        404: {"description": "User not found"},
        500: {"description": "Database error occurred"},
        403: {"description": "Forbidden. Only admin can perform this action"}
    }
)
async def activate_user(
    user_id:int = Path(..., description='ID of the user to activate', gt=0),
    session : AsyncSession = Depends(get_conn_db),
    _ : User = role_deps.admin_only()
):
    """
    Aactivate a user by settings 'is_active' to True

    - **user_id**: ID if the user to Activate
    - **Requires admin previleges**:
    """
    result = await crud_users.activate_user(user_id, session)
    if isinstance (result, dict):
        return result
    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )

@router.get(
        "/get_all_images_by_admin/{user_id}/", 
        response_model=list[sch.ImageResponseSchema]
    )
async def get_all_images_by_admin(
    user_id: int,
    session: AsyncSession = Depends(get_conn_db),
    _: User = role_deps.admin_only(),
):
    """
    Get all images uploaded by a specific user (admin only).

    - **user_id**: ID of the user whose images you want to retrieve.
    - **Requires admin privileges**.

    Returns:
        List of ImageResponseSchema objects containing image details.

    Raises:
        HTTPException: If the user is not found or has no images.
    """
    user_exists = await crud_users.get_user_by_id(user_id, session)
    if not user_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found."
        )

    images = await crud_images.get_images_by_user_id(user_id, session)
    if not images:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No images found for user with ID {user_id}."
        )

    return [
        sch.ImageResponseSchema(
            id=image.id,
            description=image.description,
            image_url=image.image_url,
            user_id=image.user_id,
            created_at=image.created_at,
            tags=[tag.name for tag in image.tags],
        )
        for image in images
    ]

@router.get("/serch/by_user/", response_model=list[sch.ImageResponseSchema])
async def search_images_by_username(
    username: str = Query(..., description="Username to search images"),
    session: AsyncSession = Depends(get_conn_db),
    _: User = role_deps.admin_moderator(),
):
    """
    Search images by user (available to moderators and administrators).
    """
    images = await crud_images.search_by_user(username, session)

    return [sch.ImageResponseSchema(
        id=img.id,
        description=img.description,
        image_url=img.image_url,
        user_id=img.user_id,
        tags=[tag.name for tag in img.tags],
        average_rating=getattr(img, 'average_rating', 0.0),
        created_at=getattr(img, 'created_at', datetime.now())
    ) for img in images]

@router.delete("/delete_rating/{rating_id}/")
async def delete_rating(
    rating_id: int, 
    session: AsyncSession = Depends(get_conn_db), 
    _: User = role_deps.admin_moderator()
):
    """
    Delete rating(Only moderators and admins).
    """
    return await crud_ratings.delete_rating(rating_id, session)

@router.delete(
        "/delete_image/{image_id}/", 
        status_code=status.HTTP_204_NO_CONTENT
    )
async def delete_image_admin(
    image_id: int,
    session: AsyncSession = Depends(get_conn_db),
    current_user: User = role_deps.admin_moderator(),
    ):
    """
    Delete image by ID
    """
    try:
        deleted = await crud_images.delete_image_admin(
            image_id, 
            session, 
            current_user
        )
    
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Image not found or access denied"
            )
        return {
            "message": "Image deleted successfully"
        }
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Database error: {str(e)}")
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Unexpected error: {str(e)}")
    
@router.get("/get_image/{image_id}/")
async def get_image_by_id(
    image_id: int,
    session: AsyncSession = Depends(get_conn_db),
    _ : User = role_deps.admin_moderator(),
):
    """
    Find URL by ImageId.
    """
    image_object = await crud_images.get_image_url(image_id, session)
    if not image_object:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Image not found"
        )
    return RedirectResponse(url=image_object.image_url)
    
@router.put(
    "/update_image_description/{image_id}/",
    response_model=sch.ImageResponseUpdateSchema,
)
async def update_image_description(
    image_id: int,
    description: str,
    session: AsyncSession = Depends(get_conn_db),
    current_user: User = role_deps.admin_moderator(),
):
    update_image_object = await crud_images.update_image_description(
        image_id, description, session, current_user
    )

    return sch.ImageResponseUpdateSchema(
        id=update_image_object.id,
        description=update_image_object.description,
        image_url=update_image_object.image_url,
        user_id=update_image_object.user_id,
    )

@router.get('/image-info')
async def get_image_info(
    image_id:int,
    session:AsyncSession = Depends(get_conn_db),
    current_user:User = role_deps.admin_moderator(),
):
    """
    Get info about image.
    """

    image_object = await crud_images.get_image_obj(
        image_id=image_id,
        session=session,
    )
    crud_images.check_permission(
        image_obj=image_object, 
        current_user_id=current_user.id 
    )
    
    return sch.ImageResponseSchema(
        id=image_object.id,
        description=image_object.description,
        image_url=image_object.image_url,
        user_id=image_object.user_id,
        tags=[tag.name for tag in image_object.tags] 
    )