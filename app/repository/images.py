from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status
import cloudinary # type: ignore
import cloudinary.uploader # type: ignore
import cloudinary.api # type: ignore
from sqlalchemy.orm import selectinload

from app.database.models import Image, User, Tag

class ImageCrud:

    async def create_image(
            self,
            url:str,
            description:str,
            user_id:int,
            public_id,
            session:AsyncSession,
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
                public_id=public_id,
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
            image_obj = result.scalar_one_or_none()

            if image_obj is None:
                raise HTTPException(
                    status_code=404, 
                    detail="Image not found."
                )

            if image_obj.user_id != current_user.id:
                raise HTTPException(
                    status_code=403, 
                    detail="You don't have permission to update this image."
                )

            image_obj.description = description
            await session.commit()
            await session.refresh(image_obj)

            return image_obj
        
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

    async def _get_all_tags(
            self,
            session : AsyncSession
    ) -> dict[str,Tag]:
        
        result = await session.execute(select(Tag).options(selectinload(Tag.images)))
        tags = result.scalars().fetchall()
        existing_tags = {tag.name: tag for tag in tags}
        return existing_tags
    
    async def _select_uniqal(
            self,
            tags_name,
            existings_tags
    ):
        new_tags_name = set(tags_name) - set(existings_tags.keys())
        return new_tags_name
    
    async def _create_new_tag(
        self,
        new_tag_names,
        session,
    ):
        query = (
            insert(Tag)
            .values(
                [
                    {'name': name} for name in new_tag_names
                ]
            ).returning(Tag.id)
        )
        result = await session.execute(query)
        tag_ids = result.scalars().all()
        re = await session.execute(select(Tag).where(Tag.id.in_(tag_ids)))
        return re.scalars().all()
        
    async def handle_tags(
            self,
            tags_names:list[str], session:AsyncSession
    ):
        existing_tags = await self._get_all_tags(session)
        new_tag_names = await self._select_uniqal(tags_names, existing_tags)
        if new_tag_names:
            new_tags = await self._create_new_tag(new_tag_names,session)
            existing_tags.update(
                {tag.name:tag for tag in new_tags}
            )

        return [existing_tags[name] for name in tags_names if name in existing_tags]
    
    async def _add_tag_to_image(
            self,
            image_object,
            tags_object,
            session
    ):
        if not isinstance(tags_object, list):
            tags_object = [tags_object]

        image_object.tags = list(set(image_object.tags + tags_object))
        session.add(image_object)
        await session.commit()
        await session.refresh(image_object)

crud_images = ImageCrud()
