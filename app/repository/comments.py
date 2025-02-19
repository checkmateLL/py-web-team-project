# crud from comments
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from fastapi import HTTPException, status

from app.database.models import Comment, User
from app.config import RoleSet

class CommentCrud:
    async def create_comment(
        self,
        text: str,
        user_id: int,
        image_id: int,
        session: AsyncSession
    ) -> Comment:
        new_comment = Comment(
            text=text,
            user_id=user_id,
            image_id=image_id
        )
        session.add(new_comment)
        await session.commit()
        await session.refresh(new_comment)
        return new_comment

    async def update_comment(
        self,
        comment_id: int,
        text: str,
        user: User,
        session: AsyncSession
    ) -> Comment | None:
        query = select(Comment).filter(Comment.id == comment_id)
        result = await session.execute(query)
        comment = result.scalar_one_or_none()
        
        if not comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    
        if comment.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot edit another user's comment")

        comment.text = text
        await session.commit()
        await session.refresh(comment)
        return comment

    async def delete_comment(
        self,
        comment_id: int,
        user: User,
        session: AsyncSession
    ) -> bool:
        query = select(Comment).filter(Comment.id == comment_id)
        result = await session.execute(query)
        comment = result.scalar_one_or_none()
        
        if comment and (user.role in [RoleSet.admin, RoleSet.moderator]):
            await session.delete(comment)
            await session.commit()
            return True
        return False

    async def get_comment(
        self,
        comment_id: int,
        session: AsyncSession
    ) -> Comment | None:
        query = select(Comment).options(joinedload(Comment.user)).filter(Comment.id == comment_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

crud_comments = CommentCrud()