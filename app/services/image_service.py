# itegration with Cloudinary, image processing, upload images to the cloud
from typing import Optional, List

from fastapi import status, APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

import cloudinary
import cloudinary.uploader
import cloudinary.api

from app.database.models import Image, User
from app.database.connection import get_conn_db
from app.templates.schemas import ImageCreate, ImageResponseSchema
from app.services.auth_service import get_current_user   #зробити корректн import!
from app.templates.config import settings, RoleSet

router = APIRouter(tags=['images'])

cloudinary.config(
    cloud_name=settings.CLD_NAME, 
    api_key=settings.CLD_API_KEY,   
    api_secret=settings.CLD_API_SECRET  
)

@router.post("/upload_image/",
             response_model=ImageCreate,
             status_code=status.HTTP_201_CREATED)

async def upload_file(description: str,
                      file: UploadFile = File(...),
                      tags: Optional[List[str]] = Query([]),
                      db: AsyncSession = Depends(get_db),
                      current_user: User = Depends(get_current_user)) -> dict:
                          
    if current_user.role not in [RoleSet.user, RoleSet.admin, RoleSet.moderator]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to upload images")

    if len(tags) > 5:
        raise HTTPException(status_code=400, detail="You can only add up to 5 tags.")

    try:
        # Upload file to Cloudinary
        result = cloudinary.uploader.upload(file.file, folder=current_user.email)
        secure_url = result["secure_url"]

     # Create a new image
        db_file = Image(url=secure_url,
                       description=description,
                       owner_id=current_user.id)
        db.add(db_file)
        await db.commit()
        await db.refresh(db_file)

        return {
                "url": secure_url,
                "description": db_file.description,
                "owner_id": db_file.owner_id
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
