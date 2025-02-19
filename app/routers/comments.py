# routes by comment 
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_conn_db
from app.database.models import User
from app.repository.comments import crud_comments
from app.services.security.auth_service import role_deps
import app.schemas as sch

router = APIRouter(prefix="/api/comments")

@router.post("/photos/{photo_id}/comments/", 
             response_model=sch.CommentResponse,
             status_code=status.HTTP_201_CREATED)
async def create_comment(
    photo_id: int,
    body: sch.CommentCreate,
    current_user: User = Depends(role_deps.all_users()),
    session: AsyncSession = Depends(get_conn_db)
):
    """Create a new comment for a photo"""
    comment = await crud_comments.create_comment(
        text=body.text,
        user_id=current_user.id,
        image_id=photo_id,
        session=session
    )
    return comment

@router.put("/photos/{comment_id}/",
            response_model=sch.CommentResponse)
async def update_comment(
    comment_id: int,
    body: sch.CommentUpdate,
    current_user: User = Depends(role_deps.all_users()),
    session: AsyncSession = Depends(get_conn_db)
):
    """Update user's own comment"""
    comment = await crud_comments.update_comment(
        comment_id=comment_id,
        text=body.text,
        user=current_user,
        session=session
    )
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found or you don't have permission to update it"
        )
    return comment

@router.delete("/photos/{comment_id}/",
               status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: int,
    current_user: User = Depends(role_deps.admin_moderator()),
    session: AsyncSession = Depends(get_conn_db)
):
    """Delete comment (admin/moderator only)"""
    deleted = await crud_comments.delete_comment(
        comment_id=comment_id,
        user=current_user,
        session=session
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    return None