from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_conn_db
from app.database.models import User
from app.repository.comments import crud_comments
from app.services.security.auth_service import role_deps
import app.schemas as sch

router = APIRouter(prefix="/comments", tags=["comments"])


@router.post(
    "/{photo_id}/", 
    response_model=sch.CommentResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_comment(
    photo_id: int,
    body: sch.CommentCreate,
    current_user: User = role_deps.all_users(),
    session: AsyncSession = Depends(get_conn_db)
):
    """
    Creates a new comment for a specific photo.

    Args:
        photo_id (int): The ID of the image being commented on.
        body (CommentCreate): The request body containing the comment text.
        current_user (User): The authenticated user creating the comment.
        session (AsyncSession): The database session.

    Returns:
        CommentResponse: The newly created comment.
    """
    new_comment = await crud_comments.create_comment(
        text=body.text,
        user_id=current_user.id,
        image_id=photo_id,
        session=session
    )

    return {
        "id": new_comment.id,
        "text": new_comment.text,
        "created_at": new_comment.created_at,
        "updated_at": new_comment.updated_at,
        "user_id": new_comment.user_id,
        "image_id": new_comment.image_id,  
    }

@router.put(
    "/{comment_id}/",
    response_model=sch.CommentResponse
)
async def update_comment(
    comment_id: int,
    body: sch.CommentUpdate,
    current_user: User = role_deps.all_users(),
    session: AsyncSession = Depends(get_conn_db)
):
    """
    Updates an existing comment if the user is the owner.

    Args:
        comment_id (int): The ID of the comment to update.
        body (CommentUpdate): The request body containing the new comment text.
        current_user (User): The authenticated user making the request.
        session (AsyncSession): The database session.

    Returns:
        CommentResponse: The updated comment.

    Raises:
        HTTPException: 404 if the comment is not found.
        HTTPException: 403 if the user is not the owner of the comment.
    """
    return await crud_comments.update_comment(
        comment_id=comment_id,
        text=body.text,
        user=current_user,
        session=session
    )


@router.delete(
    "/{comment_id}/",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_comment(
    comment_id: int,
    _: User = role_deps.admin_moderator(),
    session: AsyncSession = Depends(get_conn_db)
):
    """
    Deletes a comment if the user is an admin or moderator.

    Args:
        comment_id (int): The ID of the comment to delete.
        current_user (User): The authenticated user requesting the deletion.
        session (AsyncSession): The database session.

    Returns:
        None: Returns 204 No Content on successful deletion.

    Raises:
        HTTPException: 404 if the comment does not exist.
        HTTPException: 403 if the user does not have permission to delete.
    """
    await crud_comments.delete_comment(
        comment_id=comment_id,
        session=session
    )
    return None
    
@router.get("/{comment_id}/", response_model=sch.CommentResponse)
async def get_comment(
    comment_id: int,
    _: User = role_deps.all_users(),
    session: AsyncSession = Depends(get_conn_db)
):
    """
    Retrieves a single comment by ID.

    Args:
        comment_id (int): The ID of the comment to retrieve.
        session (AsyncSession): The database session.

    Returns:
        CommentResponse: The retrieved comment.

    Raises:
        HTTPException: 404 if the comment is not found.
    """
    comment = await crud_comments.get_comment(comment_id, session)

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Comment not found"
        )

    return {
        "id": comment.id,
        "text": comment.text,
        "created_at": comment.created_at,
        "updated_at": comment.updated_at,
        "user_id": comment.user_id,
        "image_id": comment.image_id,
    }

@router.get(
        "/image/{image_id}/", 
        response_model=list[sch.CommentResponse]
    )
async def get_comments_for_image(
    image_id: int,
    _: User = role_deps.all_users(),
    session: AsyncSession = Depends(get_conn_db)
):
    """
    Retrieves all comments for a specific image.

    Args:
        image_id (int): The ID of the image to retrieve comments for.
        session (AsyncSession): The database session.

    Returns:
        list[CommentResponse]: A list of comments for the given image.

    Raises:
        HTTPException: 404 if no comments are found.
    """
    comments = await crud_comments.get_comments_for_image(image_id, session)

    if not comments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="No comments found for this image"
        )

    return [
        {
            "id": comment.id,
            "text": comment.text,
            "created_at": comment.created_at,
            "updated_at": comment.updated_at,
            "user_id": comment.user_id,
            "image_id": comment.image_id,
        }
        for comment in comments
    ]
