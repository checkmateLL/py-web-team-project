from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.config import RoleSet
from app.services.security.secure_password import Hasher
from app.database.models import User
from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

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

    async def get_user_by_id(self, user_id, session:AsyncSession):
        result = await session.execute(select(User).filter(User.id == user_id))
        user = result.scalar_one_or_none()
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

    async def desactivate_user(self, user_id, session:AsyncSession):
        """
        Ban user crud operation
        """
        user = await self.get_user_by_id(user_id, session)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='User not found'
            )
        if user.is_active == False:
            return {
                'message': 'User is already deactivated',
                'user': {
                    'id':user.id,
                    'username':user.username,
                    'email':user.email,
                    'is-active-profile':user.is_active}
            }
        try:
            user.is_active = False
            session.add(user)
            await session.commit()
            await session.refresh(user)

        except SQLAlchemyError as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            ) from err

    async def activate_user(self, user_id, session:AsyncSession):
        """
        Unban user crud operation
        """
        user = await self.get_user_by_id(user_id, session)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='User not found'
            )
        
        if user.is_active == True:
            return {
                'message': 'User is already activated',
                'user': {
                    'id':user.id,
                    'username':user.username,
                    'email':user.email,
                    'is-active-profile':user.is_active}
            }
        
        try:
            user.is_active = True
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
        except SQLAlchemyError as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            ) from err
        
crud_users = UserCrud()