from sqlalchemy import insert, select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status
import cloudinary
import cloudinary.uploader 
import cloudinary.api
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.database.models import Image, Transformation, User, Tag

class CrudTags:
    """
    Spesial class from Tag operations.
    """
    @staticmethod
    def check_permission(
        image_obj: 'Image',
        current_user_id: int,
        detail: str = 'You dont have permission to perform this action'
    ):
        if image_obj.user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail
            )
        
    @staticmethod
    def _has_permission(
        image_obj_user_id: 'Image',
        current_user_id: int,
        detail: str = 'You dont have permission to perform this action'
    ):
        if image_obj_user_id == current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail
            )
    
    @staticmethod
    async def _check_tags_count(
        tags: list[str]
    ):
        if tags and len(tags) > 5:
            raise HTTPException(
                status_code=400, 
                detail="You can only add up to 5 tags."
            )
    
    @staticmethod
    async def _check_allowed_types(file):
        if file.content_type not in settings.ALLOWED_IMAGE_TYPE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid file type. Only JPG, PNG and GIF'
            )

    @staticmethod
    async def get_data_cloudinary(upload_result):
        secure_url = upload_result.get("secure_url")
        public_id = upload_result.get("public_id")

        if not secure_url or not public_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Cloudinary did not return required data."
            )
        return secure_url, public_id
    
    @staticmethod
    async def _check_size_file(
        file,
        detail='File too large. Maximus size is 5MB.'
        ):
        first_chunk = await file.read(5 * 1024 * 1024 + 1)
        await file.seek(0)

        if len(first_chunk) > 5 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=detail
            )
        
    async def _get_all_tags(
            self,
            session : AsyncSession
    ) -> dict[str,Tag]:
        """
        Get all tags from database
        # feature: use redis cache, optimisation process
        """
        try:
            result = await session.execute(
                select(Tag).options(selectinload(Tag.images))
            )
            tags = result.scalars().fetchall()
            existing_tags = {
                tag.name: tag for tag in tags
            }
            return existing_tags
        
        except SQLAlchemyError as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Database error {str(err)}'
            )

    async def _select_uniqal(
            self,
            tags_name : list[str],
            existings_tags : dict[str, Tag],
            detail='Tags must by a list of strings'
    ):
        """
        Return new tag with not find in database
        """
        if not isinstance(tags_name, list):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=detail
            )
        new_tags_name = set(tags_name) - set(existings_tags.keys())
        return new_tags_name
    
    async def _create_new_tag(
        self,
        new_tag_names,
        session,
    ):
        """
        Create new tag in database and return it
        """
        if not new_tag_names:
            return []
        try:
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
            if not tag_ids:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail='Failed to create new tags'
                )
            new_tags = await session.execute(select(Tag).where(Tag.id.in_(tag_ids)))
            return new_tags.scalars().all()
        except SQLAlchemyError as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Database eror {str(err)}'
            )
        
    async def handle_tags(
            self,
            tags_names:list[str], session:AsyncSession
    ):
        """
        Work with list object Tag. Added new and return listTag
        """
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
        """
        Bind tag to image
        """
        if not isinstance(tags_object, list):
            tags_object = [tags_object]
        try:
            image_object.tags = list(set(image_object.tags + tags_object))
            session.add(image_object)
            await session.commit()
            await session.refresh(image_object)
        except SQLAlchemyError as error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Failed to update image tags: {str(error)}'
            )
    
class ImageCrud(CrudTags):
    """
    Spesial class from Image CRUD operations.
    """

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
            image_obj = await self.get_image_obj(image_id, session)
           
            self.check_permission(
                image_obj=image_obj, 
                current_user_id=current_user.id 
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
        """
        Deleting image in cloudinary and database. Permision image owner.
        """
        image_obj = await self.get_image_obj(image_id,session)

        if not image_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Image not found'
            )

        self.check_permission(
            image_obj=image_obj,
            current_user_id=current_user.id
        )
        try:
            cloudinary.uploader.destroy(image_obj.public_id)

        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Error deleting image form Cloudinary'
            )

        try:
            await session.delete(image_obj)
            await session.commit()
            return True
        except SQLAlchemyError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Error deleting image from database'
            )
        
    async def delete_image_admin(
            self,
            image_id: int, 
            session: AsyncSession, 
            current_user: User
        ):
        try:
            
            image_obj = await self.get_image_obj(image_id,session)
            
            cloudinary.uploader.destroy(image_obj.public_id)

            await session.delete(image_obj)
            await session.commit()
            return True
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def get_image_url(
            self,
            image_id:int,
            session:AsyncSession
    ):
        image_obj = await self.get_image_obj(image_id,session)
        return image_obj

    async def get_image_obj(
            self,
            image_id:int,
            session:AsyncSession
    ):
        image = await session.get(Image, image_id)
        if not image:
            raise HTTPException(
                status_code=404, 
                detail="Image not found"
            )
        return image
    
    async def get_images_by_user_id(
            self,
            user_id: int, 
            session: AsyncSession
            ):
        """
        Get all images uploaded by a specific user.

        Args:
            user_id: ID of the user.
            session: Database session.

        Returns:
            List of Image objects.
        """
        result = await session.execute(select(Image).where(Image.user_id == user_id))
        return result.scalars().all()
    
    async def create_transformed_images(
            self, 
            transformed_url,
            qr_code_url,
            image_id,
            session:AsyncSession):
        
        try:
            new_transformation = Transformation(
                transformation_url=transformed_url['transformed_url'],
                qr_code_url=qr_code_url,
                image_id=image_id
            )

            session.add(new_transformation)
            await session.commit()
            await session.refresh(new_transformation)

            return {
                "transformation_url": transformed_url,
                "qr_code_url": qr_code_url,
                "image_id": image_id
            }
        
        except SQLAlchemyError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Database error occurred: {str(e)}"
            )
    
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"An unexpected error occurred: {str(e)}"
            )

        
    async def search_images(
            self,
            session: AsyncSession,
            query: str|None = None,
            tag: str|None = None,
            order_by: str = "date",
    ):
        """
        Search for images by description or tag.
        Ability to sort by rating or upload date.
        """
        try:
            stmt = select(Image).options(joinedload(Image.tags))

            if query:
                stmt = stmt.filter(Image.description.ilike(f"%{query}%"))

            if tag:
                stmt = stmt.join(Image.tags).filter(Tag.name.ilike(f"%{tag}%"))

            if order_by == "rating":
                stmt.order_by(desc(func.coalesce(Image.average_rating, 0)))
            elif order_by == "date":
                stmt = stmt.order_by(desc(Image.created_at))

            result = await session.execute(stmt)
            images = result.scalars().all()

            return images
    
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error searching images: {str(err)}"
            )        

    async def get_all_images(
            self, 
            session: AsyncSession
            ):
        """
        Get all images uploaded by all users.

        Args:
            session: Database session.

        Returns:
            List of Image objects.
        """
        result = await session.execute(select(Image))
        return result.scalars().all()

    async def search_by_user(
            self,
            username: str,
            session: AsyncSession
    ):
        """
        Search images by username (available to moderators and administrators).
        """
        try:
            result = await session.execute(
                select(Image).join(User).filter(User.username.ilike(f"{username}"))
            )
            images = result.scalars().all()
            return images
        
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error searching images by user: {str(err)}"
            )        

crud_images = ImageCrud()
