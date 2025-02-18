from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from abc import ABC, abstractmethod
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import RoleSet
from app.database.connection import get_conn_db
from app.repository.users import crud_users
from app.services.security.secure_token.manager import token_manager, TokenType
from app.database.models import User


class ConstructionAuthService(ABC):

    @abstractmethod
    async def get_current_user(
        self, token: str, session:AsyncSession
    ) -> Optional['User']: ...


class AuthService(ConstructionAuthService):

    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


    async def get_current_user(
        self,
        token: str = Depends(oauth2_scheme),
        session : AsyncSession = Depends(get_conn_db)
    ):

        credentials_exception = HTTPException(
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
                raise credentials_exception
            user = await crud_users.get_user_by_email(
                email=email,
                session=session)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='User not found'
                )
            return user
        except JWTError:
            raise credentials_exception



class RoleProtect:

    def __init__(self, auth_service:AuthService):
        self.auth_service = auth_service

    def role_required(self, required_roles: list[RoleSet]):
        async def check_role(
                current_user:User = Depends(self.auth_service.get_current_user)
        ):
            if current_user.role not in required_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f'Access denied'
                )
            return current_user
        return Depends(check_role)
    
    def all_users(self):
        return self.role_required(
            [
                RoleSet.admin, 
                RoleSet.moderator, 
                RoleSet.user
            ]
        )
    
    def admin_moderator(self):
        return self.role_required(
            [
                RoleSet.admin, 
                RoleSet.moderator
            ]
        )

    def admin_only(self):
        return self.role_required(
            [
                RoleSet.admin
            ]
        )

    def moderator_only(self):
        return self.role_required(
            [
                RoleSet.moderator
            ]
        )


auth_service = AuthService()
role_deps = RoleProtect(auth_service)