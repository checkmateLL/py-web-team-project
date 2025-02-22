from datetime import datetime, timezone
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from sqlalchemy import select
from sqlalchemy.orm import joinedload
from fastapi import HTTPException, status

from app.database.models import Comment, User

class CommentCrud:
    """
    Handles CRUD operations for comments, ensuring only authorized users can modify or delete.
    """

    async def create_comment(
        self,
        text: str,
        user_id: int,
        image_id: int,
        session: AsyncSession
    ) -> Comment:
        """
        Create a new comment associated with a user and an image.

        Args:
            text (str): The text content of the comment.
            user_id (int): The ID of the user creating the comment.
            image_id (int): The ID of the image being commented on.
            session (AsyncSession): The database session.

        Returns:
            Comment: The newly created comment.
        """
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
    ) -> Comment:
        """
        Updates an existing comment if the user is the owner.

        Args:
            comment_id (int): The ID of the comment to update.
            text (str): The new text content for the comment.
            user (User): The authenticated user attempting to update the comment.
            session (AsyncSession): The database session.

        Returns:
            Comment: The updated comment.

        Raises:
            HTTPException: 404 if the comment is not found.
            HTTPException: 403 if the user is not the owner of the comment.
        """
        query = select(Comment).filter(Comment.id == comment_id)
        result = await session.execute(query)
        comment = result.scalar_one_or_none()

        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found")

        if comment.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot edit another user's comment")

        if not text.strip():  # Double check to prevent empty comments
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Comment text cannot be empty")

        comment.text = text
        comment.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

        await session.commit()
        await session.refresh(comment)
        return comment

    async def delete_comment(
        self,
        comment_id: int,       
        session: AsyncSession
    ):
        """
        Deletes a comment only if the user has admin or moderator privileges.

        Args:
            comment_id (int): The ID of the comment to delete.
            user (User): The authenticated user attempting to delete the comment.
            session (AsyncSession): The database session.

        Returns:
            bool: True if the comment was successfully deleted.

        Raises:
            HTTPException: 404 if the comment is not found.
            HTTPException: 403 if the user lacks permission to delete.
        """
        try:
            query = select(Comment).filter(Comment.id == comment_id)
            result = await session.execute(query)
            comment = result.scalar_one_or_none()
            if not comment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='Comment not found'
                )
    
            await session.delete(comment)
            await session.commit()
            return comment
        except SQLAlchemyError as e:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred while deleting comment"
            )


    async def get_comment(
        self,
        comment_id: int,
        session: AsyncSession
    ) -> Comment | None:
        """
        Retrieves a single comment by ID, including the user relationship.

        Args:
            comment_id (int): The ID of the comment to retrieve.
            session (AsyncSession): The database session.

        Returns:
            Comment | None: The retrieved comment or None if not found.
        """
        query = select(Comment).options(
            joinedload(Comment.user)
        ).filter(Comment.id == comment_id)
        
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def get_comments_for_image(
        self,
        image_id: int,
        session: AsyncSession
    ) -> Sequence[Comment]:
        """
        Retrieves all comments for a given image ID.

        Args:
            image_id (int): The ID of the image to retrieve comments for.
            session (AsyncSession): The database session.

        Returns:
            list[Comment]: A list of comments for the given image.
        """
        query = select(Comment).options(
            joinedload(Comment.user)
        ).filter(Comment.image_id == image_id)

        result = await session.execute(query)
        return result.scalars().all()

# Initialize the CRUD instance for comments
crud_comments = CommentCrud()
