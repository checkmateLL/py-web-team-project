from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, distinct
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from typing import Optional

from app.config import RoleSet
from app.services.security.secure_password import Hasher
from app.database.models import User, Image, Comment, Rating
from fastapi import HTTPException, status


class UserCrud:

    async def exist_user(self, email: str, session: AsyncSession) -> bool:
        """check if email exist in tableUser, unicValue"""
        query = select(User).filter(User.email == email)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        return user is not None
    
    async def create_new_user(
            self, 
            email : str,
            user_name : str,
            password : str,
            session: AsyncSession):
        """
        if userObject is first do admin role
        else userObject exist in database do user role
        """
        if await self.is_no_users(session=
                                 session):
            new_user = User(
                email=email,
                username=user_name,
                password_hash=password,
                is_active=True,
                role=RoleSet.admin
            )
        else:
            new_user = User(
                email=email,
                username=user_name,
                password_hash=password,
                is_active=True,
                role=RoleSet.user,
            )
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
    
        return new_user

    async def get_user_by_email(self, email:str, session:AsyncSession):
        result = await session.execute(select(User).filter(User.email == email))
        user = result.scalars().first()
        return user

    async def autenticate_user(
            self, 
            email: str, 
            password: str, 
            session: AsyncSession
        ):
        user = await self.get_user_by_email(email, session)
        if not user:
            return False
        if not Hasher.verify_password(password, user.password_hash):
            return False
        return user
    
    async def is_no_users(self, session: AsyncSession) -> bool:
        """
        Check, userobject in database.
        Returned True, if database empty.
        """
        result = await session.execute(select(func.count(User.id)))
        count = result.scalar_one()
        return count == 0
    
    async def get_user_by_username(self, username: str, session: AsyncSession) -> User | None:
        """Get user by username"""
        result = await session.execute(select(User).filter(User.username == username))
        return result.scalar_one_or_none()
    
    async def get_user_profile(self, username: str, session: AsyncSession):
        """Get user profile with statistics"""
        # Get user with related counts
        query = select(
            User,
            func.count(distinct(Image.id)).label('total_images'),
            func.count(distinct(Comment.id)).label('total_comments'),
            func.count(distinct(Rating.id)).label('total_ratings')
        ).outerjoin(Image, User.id == Image.user_id)\
         .outerjoin(Comment, User.id == Comment.user_id)\
         .outerjoin(Rating, User.id == Rating.user_id)\
         .filter(User.username == username)\
         .group_by(User.id)

        result = await session.execute(query)
        user_data = result.first()
        
        if not user_data:
            return None
            
        user, total_images, total_comments, total_ratings = user_data
        
        # Calculate member_since in general format
        days_since = (datetime.now() - user.register_on).days
        years = days_since // 365
        months = (days_since % 365) // 30
        
        if years > 0:
            member_since = f"{years} year{'s' if years != 1 else ''}"
            if months > 0:
                member_since += f" and {months} month{'s' if months != 1 else ''}"
        else:
            member_since = f"{months} month{'s' if months != 1 else ''}"
            if months == 0:
                member_since = "Less than a month"

        return {
            "username": user.username,
            "created_at": user.register_on,
            "total_images": total_images,
            "total_comments": total_comments,
            "total_ratings_given": total_ratings,
            "member_since": member_since,
            "bio": user.bio,
            "avatar_url": user.avatar_url,
            "email": user.email,
            "is_active": user.is_active,
            "role": user.role.value,
            "id": user.id
        }

    async def update_user_profile(
        self, 
        user_id: int, 
        session: AsyncSession,
        username: str | None = None,
        email: str | None = None,
        password_hash: Optional[str] = None,
        bio: str | None = None,
        avatar_url: str | None = None        
    ) -> User:
        """Update user profile"""
        try:
            query = select(User).filter(User.id == user_id)
            result = await session.execute(query)
            user = result.scalar_one_or_none()

            if not user:
                return None 
            
            if user:
                if username:
                    user.username = username
                if email:
                    user.email = email
                if bio is not None:
                    user.bio = bio
                if avatar_url is not None:
                    user.avatar_url = avatar_url
                if password_hash is not None:
                    user.password_hash = password_hash
                    
            await session.commit()
            await session.refresh(user)                
            return user
        
        except SQLAlchemyError as e:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            ) from e


crud_users = UserCrud()