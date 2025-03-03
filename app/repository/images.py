from sqlalchemy import insert, desc, func
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
        image_obj: "Image",
        current_user_id: int,
        detail: str = "You dont have permission to perform this action",
    ):
        """
        check permision spesion from ratings.
        """
        if image_obj.user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail
            )

    @staticmethod
    def _has_permission(
        image_obj_user_id: "Image",
        current_user_id: int,
        detail: str = "You dont have permission to perform this action",
    ):
        """
        access permision operation to image or tag.
        """
        if image_obj_user_id == current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail
            )

    @staticmethod
    async def _check_tags_count(tags: list[str]):
        """
        check limit tags when upload image.
        """
        if tags and len(tags) > 5:
            raise HTTPException(
                status_code=400, detail="You can only add up to 5 tags."
            )

    @staticmethod
    async def _check_allowed_types(file):
        """
        check allowed types.
        """
        if file.content_type not in settings.ALLOWED_IMAGE_TYPE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Only JPG, PNG and GIF",
            )

    @staticmethod
    async def get_data_cloudinary(upload_result):
        """
        get data cloudinary.
        """
        secure_url = upload_result.get("secure_url")
        public_id = upload_result.get("public_id")

        if not secure_url or not public_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Cloudinary did not return required data.",
            )
        return secure_url, public_id

    @staticmethod
    async def _check_size_file(
        file,
        detail="File too large. Maximus size is 5MB."
    ):
        """
        Check the size of the uploaded file.

        This function reads the first chunk of the file to determine its size.
        If the file size exceeds the maximum allowed size (5MB), it raises an
        HTTP 400 Bad Request exception.

        Args:
            file: The uploaded file to check.
            detail (str): The error message to include in the exception if the
            file is too large.

        Raises:
            HTTPException: If the file size exceeds the maximum allowed size.
        """
        first_chunk = await file.read(5 * 1024 * 1024 + 1)
        await file.seek(0)

        if len(first_chunk) > 5 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    async def _get_all_tags(self, session: AsyncSession) -> dict[str, Tag]:
        """
        Retrieve all tags from the database.

        This function retrieves all tags from the database, including their
          associated images.

        Args:
            session (AsyncSession): An asynchronous database session.

        Returns:
            dict[str, Tag]: A dictionary of existing tags with tag names
              as keys.

        Raises:
            HTTPException: If a database error occurs.
        """
        try:
            result = await session.execute(
                select(Tag).options(selectinload(Tag.images))
            )
            tags = result.scalars().fetchall()
            existing_tags = {tag.name: tag for tag in tags}
            return existing_tags

        except SQLAlchemyError as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error {str(err)}",
            )

    async def _select_uniqal(
        self,
        tags_name: list[str],
        existings_tags: dict[str, Tag],
        detail="Tags must by a list of strings",
    ):
        """
        Return new tags that are not found in the database.

        This function takes a list of tag names and a dictionary of
          existing tags,
        and returns a set of new tag names that are not found in the
          existing tags.

        Args:
            tags_name (list[str]): A list of tag names to check.
            existings_tags (dict[str, Tag]): A dictionary of existing
              tags with tag names as keys.

        Returns:
            set: A set of new tag names that are not found in the
              existing tags.

        Raises:
            HTTPException: If the provided tags_name is not a list.
        """
        if not isinstance(tags_name, list):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=detail
                )
        new_tags_name = set(tags_name) - set(existings_tags.keys())
        return new_tags_name

    async def _create_new_tag(
        self,
        new_tag_names,
        session,
    ):
        """
        Create new tags in the database.

        This function inserts new tag names into the database and
          returns the created tag objects.

        Args:
            new_tag_names (set): A set of new tag names to create.
            session (AsyncSession): An asynchronous database session.

        Returns:
            list[Tag]: A list of newly created Tag objects.

        Raises:
            HTTPException: If an error occurs during the creation of new tags.
        """
        if not new_tag_names:
            return []
        try:
            query = (
                insert(Tag)
                .values([{"name": name} for name in new_tag_names])
                .returning(Tag.id)
            )
            result = await session.execute(query)
            tag_ids = result.scalars().all()
            if not tag_ids:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create new tags",
                )
            new_tags = await session.execute(
                select(Tag).where(Tag.id.in_(tag_ids))
                )
            return new_tags.scalars().all()
        except SQLAlchemyError as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database eror {str(err)}",
            )

    async def handle_tags(self, tags_names: list[str], session: AsyncSession):
        """
        Handle tags for an image.

        This function processes the provided tag names, retrieves existing
          tags from the database,
        creates new tags if necessary, and returns a list of tag objects
          corresponding to the provided tag names.

        Args:
            tags_names (list[str]): A list of tag names to handle.
            session (AsyncSession): An asynchronous database session.

        Returns:
            list[Tag]: A list of Tag objects corresponding to the
              provided tag names.

        Raises:
            HTTPException: If an error occurs during the tag handling process.
        """
        existing_tags = await self._get_all_tags(session)
        new_tag_names = await self._select_uniqal(tags_names, existing_tags)
        if new_tag_names:
            new_tags = await self._create_new_tag(new_tag_names, session)
            existing_tags.update({tag.name: tag for tag in new_tags})

        return [existing_tags[name] for name in tags_names
                if name in existing_tags
                ]

    async def _add_tag_to_image(self, image_object, tags_object, session):
        """
        Add tags to an image.

        This function adds tags to an image object and updates the database.
        It ensures that the tags are added uniquely to the image.

        Args:
            image_object (Image): The image object to which tags will be added.
            tags_object (list[Tag]): A list of tag objects to add to the image.
            session (AsyncSession): An asynchronous database session.

        Raises:
            HTTPException: If an error occurs during the database operation.
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
                detail=f"Failed to update image tags: {str(error)}",
            )


class ImageCrud(CrudTags):

    async def create_image(
        self,
        url: str,
        description: str,
        user_id: int,
        public_id,
        session: AsyncSession,
    ) -> Image:
        session
        """
        Create a new image record in the database.

        This function creates a new image record in the database with
          the provided URL, description, user ID, and public ID.

        Args:
            url (str): The URL of the image.
            description (str): The description of the image.
            user_id (int): The ID of the user who uploaded the image.
            public_id (str): The public ID of the image in Cloudinary.
            session (AsyncSession): An asynchronous database session.

        Returns:
            Image: The newly created Image object.

        Raises:
            HTTPException: If an error occurs during the creation of the
              image record.
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
                detail=f"Error creating image record in database {str(err)}",
            )

    async def update_image_description(
        self,
        image_id,
        description,
        session: AsyncSession,
        current_user: User,
    ):
        """
        Update the description of an image.

        This function updates the description of an image in the database.
        It ensures that only the owner of the image can perform this action.

        Args:
            image_id (int): The ID of the image to update.
            description (str): The new description for the image.
            session (AsyncSession): An asynchronous database session.
            current_user (User): The current user performing the update.

        Returns:
            Image: The updated Image object.

        Raises:
            HTTPException: If the image with the specified ID does not exist
              or if the current user does not have permission to update
                the image.
        """
        try:
            image_obj = await self.get_image_obj(image_id, session)

            self.check_permission(
                image_obj=image_obj, current_user_id=current_user.id
                )

            image_obj.description = description
            await session.commit()
            await session.refresh(image_obj)

            return image_obj

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def update_image_description_admin(
        self,
        image_id,
        description,
        session: AsyncSession,
        _: User,
    ):
        """
        Update the description of an image (available to moderators and
        administrators).

        Args:
            image_id (int): The ID of the image to update.
            description (str): The new description for the image.
            session (AsyncSession): An asynchronous database session.
            current_user (User): The current user performing the update.

        Returns:
            Image: The updated Image object.

        Raises:
            HTTPException: If the image with the specified ID does not exist
              or if the current user does not have permission to update
                the image.
        """
        try:
            image_obj = await self.get_image_obj(image_id, session)
            image_obj.description = description
            await session.commit()
            await session.refresh(image_obj)

            return image_obj

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def delete_image(
        self, image_id: int, session: AsyncSession, current_user: User
    ):
        """
        Delete an image by its ID (available to image owners).

        This function deletes an image from the database and Cloudinary.
        It ensures that only the owner of the image can perform this action.

        Args:
            image_id (int): The ID of the image to delete.
            session (AsyncSession): An asynchronous database session.
            current_user (User): The current user performing the deletion.

        Returns:
            bool: True if the image was successfully deleted.

        Raises:
            HTTPException: If the image with the specified ID does not
              exist or if the current user does not have permission to
                delete the image.
        """
        image_obj = await self.get_image_obj(image_id, session)

        if not image_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
            )
        self.check_permission(
            image_obj=image_obj,
            current_user_id=current_user.id
            )
        try:
            cloudinary.uploader.destroy(image_obj.public_id)

        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error deleting image form Cloudinary",
            )
        try:
            await session.delete(image_obj)
            await session.commit()
            return True
        except SQLAlchemyError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error deleting image from database",
            )

    async def delete_image_admin(
        self, image_id: int, session: AsyncSession, _: User
    ):
        """
        Delete an image by its ID (available to administrators).

        This function deletes an image from the database and Cloudinary.
        It ensures that only administrators can perform this action.

        Args:
            image_id (int): The ID of the image to delete.
            session (AsyncSession): An asynchronous database session.
            current_user (User): The current user performing the deletion.

        Returns:
            bool: True if the image was successfully deleted.

        Raises:
            HTTPException: If the image with the specified ID does not
              exist or if the current user is not an administrator.
        """
        try:

            image_obj = await self.get_image_obj(image_id, session)
            cloudinary.uploader.destroy(image_obj.public_id)

            await session.delete(image_obj)
            await session.commit()
            return True
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def get_image_url(self, image_id: int, session: AsyncSession):
        """
        Get an image object by its ID.

        This function retrieves an image object from the database based
        on its unique ID.
        If the image is not found, it raises an HTTP 404 Not Found exception.

        Args:
            image_id (int): The ID of the image to retrieve.
            session (AsyncSession): An asynchronous database session.

        Returns:
            Image: The Image object if found.

        Raises:
            HTTPException: If the image with the specified ID does not exist.
        """
        image_obj = await self.get_image_obj(image_id, session)
        return image_obj

    async def get_image_obj(self, image_id: int, session: AsyncSession):
        """
        Get an image object by its ID.

        This function retrieves an image object from the database based
          on its unique ID.
        If the image is not found, it raises an HTTP 404 Not Found exception.

        Args:
            image_id (int): The ID of the image to retrieve.
            session (AsyncSession): An asynchronous database session.

        Returns:
            Image: The Image object if found.

        Raises:
            HTTPException: If the image with the specified ID does not exist.
        """
        image = await session.get(Image, image_id)
        if not image:
            raise HTTPException(status_code=404, detail="Image not found")
        return image

    async def get_images_by_user_id(self, user_id: int, session: AsyncSession):
        """
        Create a new transformation record for an image.

        This function creates a new transformation record in the database,
          which includes the transformed URL,
        QR code URL, and the associated image ID.

        Args:
            transformed_url (dict): A dictionary containing the transformed
            URL.
            qr_code_url (str): The URL of the QR code.
            image_id (int): The ID of the image being transformed.
            session (AsyncSession): An asynchronous database session.

        Returns:
            dict: A dictionary containing the transformation details.

        Raises:
            HTTPException: If an error occurs during the creation of the
              transformation record.
        """
        result = await session.execute(
            select(Image).where(Image.user_id == user_id)
            )
        return result.scalars().all()

    async def create_transformed_images(
        self, transformed_url, qr_code_url, image_id, session: AsyncSession
    ):

        try:
            new_transformation = Transformation(
                transformation_url=transformed_url["transformed_url"],
                qr_code_url=qr_code_url,
                image_id=image_id,
            )

            session.add(new_transformation)
            await session.commit()
            await session.refresh(new_transformation)

            return {
                "transformation_url": transformed_url,
                "qr_code_url": qr_code_url,
                "image_id": image_id,
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
        query: str | None = None,
        tag: str | None = None,
        order_by: str = "date",
    ):
        """
        Search for images by description or tag.
        Ability to sort by rating or upload date.

        This function searches for images based on the provided query and tag.
        It can also sort the results by rating or upload date.

        Args:
            session (AsyncSession): An asynchronous database session.
            query (str | None): A search query for the image description.
            tag (str | None): A search query for the image tags.
            order_by (str): The sorting criteria. Can be "rating"
              or "date". Default is "date".

        Returns:
            list: A list of Image objects that match the search criteria.

        Raises:
            HTTPException: If an error occurs during the search operation.
        """
        try:
            stmt = select(Image).options(joinedload(
                Image.tags
                )).group_by(Image.id)

            if query:
                stmt = stmt.filter(
                    Image.description.ilike(f"%{query}%")
                    )

            if tag:
                stmt = stmt.join(Image.tags).filter(
                    Tag.name.ilike(f"%{tag}%")
                    )

            if order_by == "rating":
                stmt = stmt.order_by(desc(
                    func.coalesce(Image.average_rating, 0)
                    ))
            elif order_by == "date":
                stmt = stmt.order_by(desc(Image.created_at))

            result = await session.execute(stmt)
            images = result.scalars().unique().all()
            return images

        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error searching images: {str(err)}",
            )

    async def get_all_images(self, session: AsyncSession):
        """
        Get all images uploaded by all users.

        This function retrieves all images from the database.

        Args:
            session (AsyncSession): An asynchronous database session.

        Returns:
            list: A list of Image objects representing all images in the
              database.
        """
        result = await session.execute(select(Image))
        return result.scalars().all()

    async def search_by_user(self, username: str, session: AsyncSession):
        """
        Search images by username (available to moderators and administrators).

        This function searches for images associated with a specific user by
          their username.
        It performs a case-insensitive search and returns a list of matching
          images.

        Args:
            username (str): The username of the user to search for.
            session (AsyncSession): An asynchronous database session.

        Returns:
            list: A list of Image objects that match the search criteria.

        Raises:
            HTTPException: If an error occurs during the search operation.
        """
        try:
            result = await session.execute(
                select(Image).join(User).filter(
                    User.username.ilike(f"{username}")
                    )
            )
            images = result.scalars().all()
            return images

        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error searching images by user: {str(err)}",
            )


crud_images = ImageCrud()
