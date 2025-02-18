# itegration with Cloudinary, image processing, upload images to the cloudinary
import cloudinary
from app.database.models import Image
from app.services.auth_service import get_current_user
from app.database.connection import AsyncSession
from app.templates.config import settings
from app.services.auth_service import RoleSet
from cloudinary.uploader import upload
from app.templates.schemas import ImageCreate
from typing import List
from fastapi import HTTPException

# Настройка Cloudinary
cloudinary.config(
    cloud_name=settings.CLD_NAME, 
    api_key=settings.CLD_API_KEY,   
    api_secret=settings.CLD_API_SECRET  
)

async def upload_image_service(description: str,
                               file,  # UploadFile
                               tags: List[str], 
                               db: AsyncSession,
                               current_user) -> dict:
    # download image cloud cloudinary
    try:
        result = cloudinary.uploader.upload(file.file, folder=current_user.email)
        secure_url = result["secure_url"]
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error uploading file to Cloudinary: " + str(e))

    # create new post/image in DB
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

