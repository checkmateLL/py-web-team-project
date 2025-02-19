# crud images operations with db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException
import cloudinary
import cloudinary.uploader
import cloudinary.api

from app.database.models import Image, User
from app.schemas import ImageResponseSchema
from app.config import RoleSet


async def update_image_description(image_id: int, description: str, db: AsyncSession, current_user: User) -> ImageResponseSchema:
    try:
      
        result = await db.execute(select(Image).filter(Image.id == image_id))
        image = result.scalar_one_or_none()

        if image is None:
            raise HTTPException(status_code=404, detail="Image not found.")

        if image.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="You don't have permission to update this image.")

        # Update the image description
        image.description = description
        await db.commit()
        await db.refresh(image)

        return ImageResponseSchema(url=image.url, description=image.description, owner_id=image.owner_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

async def get_image_by_url(image_url: str, db: AsyncSession) -> ImageResponseSchema:
    try:
        
        result = await db.execute(select(Image).filter(Image.url == image_url))
        image = result.scalar_one_or_none()

        if image is None:
            raise HTTPException(status_code=404, detail="Image not found.")

        return ImageResponseSchema(url=image.url, description=image.description, owner_id=image.owner_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
async def delete_image(image_id: int, db: AsyncSession, current_user: User):
    try:
        
        result = await db.execute(select(Image).filter(Image.id == image_id))
        image = result.scalar_one_or_none()

        if image is None:
            raise HTTPException(status_code=404, detail="Image not found.")
        
        #видаляти тепер може власник або адмін
        if image.user_id != current_user.id and current_user.role != RoleSet.admin:
            raise HTTPException(status_code=403, detail="You don't have permission to delete this image.")
        
        # Видалення з Cloudinary (додати public_id в модель Image!)
        if image.public_id:
            cloudinary.uploader.destroy(image.public_id)

        # Delete image record from database
        await db.delete(image)
        await db.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
