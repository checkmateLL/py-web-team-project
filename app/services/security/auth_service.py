from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_conn_db
from app.repository.users import crud_users
from app.services.security.secure_token.manager import token_manager, TokenType
from app.database.models import User


class ConstructionAuthService(ABC):

    @abstractmethod
    async def get_current_user(
        self, toke: str, db: AsyncSession
    ) -> Optional["User"]: ...


class AuthService(ConstructionAuthService):
    auth2scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

    async def get_current_user(
        self,
        token: str = Depends(auth2scheme),
        session: AsyncSession = Depends(get_conn_db),
    ):

        credential_exeptions = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            pyload = await token_manager.decode_token(
                token_type=TokenType.ACCESS,
                token=token
            )
            email = pyload.get('sub')
            if email is None:
                raise credential_exeptions
        except JWTError:
            raise credential_exeptions

        user = await crud_users.get_user_by_email(
            email=email,
            session=session)
        
        return user


auth_serv = AuthService()