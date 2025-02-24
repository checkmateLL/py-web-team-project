import redis.asyncio as redis
from app.config import settings
from fastapi import Depends, HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import magic
import logging
from datetime import datetime, timedelta

from app.database.models import User
from app.schemas import UserProfileEdit
from app.repository.users import crud_users
from app.services.image_service import CloudinaryService
from app.services.security.secure_password import Hasher

logger = logging.getLogger(__name__)

class RedisClient():

    def __init__(self):
        self.host = settings.REDIS_HOST
        self.port = settings.REDIS_PORT
        self.db = settings.REDIS_DB
        self.set = settings.REDIS_DECODE_RESPONSES
        self._client = None

    async def get_redis_client(self):
        if not self._client:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=self.set,
            )
        return self._client
    
class TokenBlackList:

    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client

    async def blacklist_access_token(self, access_token: str, expires_in: int):
        """Added access-token in blacklist"""
        await self.redis_client.setex(
            f"blacklist:{access_token}",
            expires_in,
            "blacklisted"
        )

    async def is_token_blacklisted(self, access_token: str) -> bool:
        """Check yiet access token in blacklist"""
        return await self.redis_client.exists(
            f"blacklist:{access_token}"
        ) > 0

redis_client = RedisClient()

async def get_redis():
    client = await redis_client.get_redis_client()
    try:
        yield client
    finally:
        await client.close()

async def get_token_blacklist(redis_client: redis.Redis = Depends(get_redis)):
    return TokenBlackList(redis_client)

class UserService:
    def __init__(self, db: AsyncSession, cloudinary: CloudinaryService):
        self.db = db
        self.cloudinary = cloudinary

    async def validate_avatar_file(self, file: UploadFile) -> None:
        """Validates avatar file type and size."""
        try:
            # MIME detection
            first_chunk = await file.read(1024 * 1024)
            await file.seek(0)  # Reset file pointer

            # Validate file type using python-magic (should be only images)
            mime = magic.Magic(mime=True)
            mime_type = mime.from_buffer(first_chunk)

            allowed_types = {"image/jpeg", "image/png", "image/webp"}
            if mime_type not in allowed_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid file type. Only JPEG, PNG and WebP are allowed."
                )

            # Validate file size (5MB max)
            file_size = len(first_chunk)
            max_size = 5 * 1024 * 1024 
            
            if file_size > max_size:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File too large. Maximum size is 5MB"
                )

        except Exception as e:
            logger.error(f"Avatar validation error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error validating avatar file"
            )

    async def update_avatar(self, user_id: int, file: UploadFile) -> dict:
        """Updates user avatar with deletion of old avatar."""
        try:            
            await self.validate_avatar_file(file)
            
            user = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = user.scalar_one_or_none()

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            if user.avatar_url and '/' in user.avatar_url:
                try:                    
                    public_id = user.avatar_url.split("/")[-1].split(".")[0]
                    await self.cloudinary.delete_avatar(public_id)
                except Exception as e:
                    logger.warning(f"Failed to delete old avatar: {str(e)}")
            
            upload_result = await self.cloudinary.upload_avatar(file)            
           
            user.avatar_url = upload_result["secure_url"]
            await self.db.commit()

            return {"avatar_url": upload_result["secure_url"]}

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Avatar update error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update avatar: {str(e)}"
            )