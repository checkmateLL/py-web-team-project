import cloudinary  # type: ignore
import cloudinary.uploader  # type: ignore

from typing import Optional
from fastapi import HTTPException, File, UploadFile, Query, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Image, User
from app.services.security.auth_service import role_deps
from app.database.connection import get_conn_db
from app.repository.images import crud_images
from app.config import settings


class CloudinaryService:
    """
    Service for work with Cloudinary
    """
    def __init__(self):
        cloudinary.config(
            cloud_name=settings.CLD_NAME,
            api_key=settings.CLD_API_KEY,
            api_secret=settings.CLD_API_SECRET
        )

    async def upload_image(
            self,
            file: UploadFile,
            folder: str
    ) -> dict:
        """
        Upload image to Cloudinary
        """
        try:
            result = cloudinary.uploader.upload(
                file.file,
                folder=folder
            )
            return {
                "secure_url": result.get("secure_url"),
                "public_id": result.get("public_id")
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error uploading file to Cloudinary: " + str(e)
            )
