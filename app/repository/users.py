from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.security.secure_password import Hasher
from app.database.models import User


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
        new_user = User(
            email=email,
            username=user_name,
            password_hash=password,
            is_active=True,
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

crud_users = UserCrud()