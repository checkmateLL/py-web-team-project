from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status
import cloudinary # type: ignore
import cloudinary.uploader # type: ignore
import cloudinary.api # type: ignore

from app.database.models import Image, User

class ImageCrud:

    async def create_image(
            self,
            url:str,
            description:str,
            user_id:int,
            public_id,
            session:AsyncSession
    )->Image:
        session
        """
        Create record images in database
        """
        try:
            image_record = Image(
                image_url=url,
                description=description,
                user_id=user_id,
                public_id=public_id
            )
            session.add(image_record)
            await session.commit()
            await session.refresh(image_record)

            return image_record
        
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Error creating image record in database {str(err)}'
            )

    async def update_image_description(
            self,
            image_id,
            description,
            session:AsyncSession,
            current_user:User,
    ):
        try:
            result = await session.execute(select(Image).filter(Image.id == image_id))
            image = result.scalar_one_or_none()

            if image is None:
                raise HTTPException(
                    status_code=404, 
                    detail="Image not found."
                )

            if image.user_id != current_user.id:
                raise HTTPException(
                    status_code=403, 
                    detail="You don't have permission to update this image."
                )

            image.description = description
            await session.commit()
            await session.refresh(image)

            return {
                        'url':image.image_url,
                        'description':image.description,
                        'owner_id':image.user_id
                    }
        
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=str(e)
            )
            
    async def delete_image(
            self,
            image_id: int, 
            session: AsyncSession, 
            current_user: User
        ):
        try:
            
            result = await session.execute(select(Image).filter(Image.id == image_id))
            image = result.scalar_one_or_none()

            if image is None:
                raise HTTPException(
                    status_code=404, 
                    detail="Image not found."
                )
            
            if image.user_id != current_user.id:
                raise HTTPException(
                    status_code=403, 
                    detail="You don't have permission to delete this image."
                )
            
            cloudinary.uploader.destroy(image.public_id)

            await session.delete(image)
            await session.commit()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def get_image_url(
            self,
            image_id:int,
            session:AsyncSession
    ):
        result = await session.execute(select(Image).filter(Image.id == image_id))
        image = result.scalar_one_or_none()
        if image is None:
            raise HTTPException(
                status_code=404, 
                detail="Image not found"
            )
        return image

crud_images = ImageCrud()
