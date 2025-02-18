from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import HTTPException, status
import time
from zoneinfo import ZoneInfo
from app.config import settings

class ITokenStrategy(ABC):
    def __init__(self):
        self.secret_key = settings.SECRET_KEY_JWT
        self.algorithm = settings.ALGORITHM

    @abstractmethod
    async def create_token(
        self,
        data : dict,
        expire_delta: Optional[float] = None
    ) -> str:
        pass

    @abstractmethod
    async def decode_token(self, token : str ) -> dict:
        pass

    @abstractmethod
    def _get_default_expiry(self) -> timedelta:
        pass

    def _encode_token(
            self, 
            data:dict, 
            scope:str, 
            expire_delta:Optional[float] = None
        ) -> str:
        to_encode = data.copy()

        expire = datetime.now(ZoneInfo('UTC')) + (timedelta(days=expire_delta) if expire_delta else self._get_default_expiry())

        to_encode.update(
            {
                'exp':expire,
                'scope':scope
            }
        )
        return jwt.encode(
            to_encode, 
            self.secret_key, 
            algorithm=self.algorithm
        )

    def _decode_token(
            self,
            token:str,
            scope:str
    ):
        """
        returned payload, mean {'sub':useremail}
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
                )
            
            if payload.get('scope') != scope:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail='Invalid token scope')
            
            if 'exp' in payload and payload['exp'] < time.time():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail='Tokec has expired'
                )
            
            return payload
        except JWTError as err:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f'Invalid token: {str(err)}'
            )