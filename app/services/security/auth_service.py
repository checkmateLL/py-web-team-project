from datetime import datetime, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from abc import ABC, abstractmethod
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user_service import TokenBlackList, get_token_blacklist
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

    @abstractmethod
    async def get_token(self) -> str: ...

class AuthService(ConstructionAuthService):

    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="app/auth/login")

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
            
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail='User is banned'
                )
            
            return user
        
        except JWTError:
            raise credentials_exception

    async def logout_set(
            self,
            token:str = Depends(oauth2_scheme),
            token_blacklist: TokenBlackList = Depends(get_token_blacklist)
    ):
            
        if await token_blacklist.is_token_blacklisted(token):
            raise HTTPException(
                status_code=401,
                detail='Invalid token'
            )
        
        try:
            pyload = await token_manager.decode_token(
                token_type=TokenType.ACCESS,
                token=token
            )
            exp_timestamp = pyload.get('exp')
            if not exp_timestamp:
                raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
            expires_in = max(exp_timestamp - int(datetime.now(timezone.utc).timestamp()), 0)

            await token_blacklist.blacklist_access_token(token, expires_in)
            return {
                'message':'Logged out successfully'
            }
        
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
    @staticmethod
    async def get_token(
            token:str = Depends(oauth2_scheme)
    ):
        """return access token"""
        return token

class IRokeProtect(ABC):

    @abstractmethod
    def role_required(self, required_role:list[RoleSet]):
        """check role userObject"""
        ...
    
    @abstractmethod
    def all_users(self):
        """access granted all roles"""
        ...

    @abstractmethod
    def admin_moderator(self):
        """access granted admin and moderator"""
        ...
    
    @abstractmethod
    def admin_only(self):
        """access admin"""
        ...
    
    @abstractmethod
    def moderator_only(self):
        """access granted moderator"""
        ...
        


class RoleProtect(IRokeProtect):

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

role_deps = RoleProtect(AuthService())