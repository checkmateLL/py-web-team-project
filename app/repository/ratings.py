from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status
from app.database.models import Rating, Image
from sqlalchemy.sql import func
from abc import ABC, abstractmethod

from app.repository.images import crud_images

class BaseRatingCrud(ABC):

    @abstractmethod
    async def _update_average_rating(
        self,
        image: Image,
        image_id: int,
        session: AsyncSession
    ):
        """Update average rating for image."""
        ...
    
    @abstractmethod
    async def _create_rating(
        self,
        image_id: int,
        user_id: int,
        value: int,
        session: AsyncSession
    ):
        """Create a rating object."""
        ...
    
    @abstractmethod
    async def _get_average_rating(
        self,
        image_id: int,
        session: AsyncSession
    ) -> float:
        """Get average rating for image."""
        ...
    
    @abstractmethod
    async def _get_existing_rating(
        self,
        image_id: int,
        user_id: int,
        session: AsyncSession,
        detail: str
    ):
        """Get existing rating for image."""
        ...
    
    @abstractmethod
    async def _get_rating_object(
        self,
        rating_id: int,
        session: AsyncSession,
        detail: str
    ):
        """Get rating object by ID."""
        ...
    
    @abstractmethod
    async def add_rating(
        self,
        image_id: int,
        user_id: int,
        value: int,
        session: AsyncSession
    ):
        """Add a rating to an image."""
        ...
    
    @abstractmethod
    async def delete_rating(
        self,
        rating_id: int,
        session: AsyncSession
    ):
        """Delete a rating."""
        ...


class RatingCrud(BaseRatingCrud):
    
    async def _update_average_rating(
        self,
        image: Image,
        image_id: int,
        session: AsyncSession
    ):
        """
        Update average rating for image.
        """
        avg_rating = await self._get_average_rating(image_id, session)
        image.average_rating = avg_rating

        session.add(image)
        await session.commit()
        await session.refresh(image)

    async def _create_rating(
        self,
        image_id: int,
        user_id: int,
        value: int,
        session: AsyncSession
    ):
        new_rating = Rating(
            image_id=image_id,
            user_id=user_id,
            value=value
        )    
        session.add(new_rating)
        await session.commit()
        return new_rating
    

    async def _get_average_rating(
        self, 
        image_id: int, 
        session: AsyncSession
    ) -> float:
        """
        returned AVG rating bu image.
        """
        avg_result = await session.execute(
            select(func.avg(Rating.value)).filter(Rating.image_id == image_id)
        )
        return avg_result.scalar() or 0.0
    
    async def _get_existing_rating(
            self, 
            image_id: int, 
            user_id: int, 
            session: AsyncSession,
            detail='You have already rated this image.'
        ):
            result = await session.execute(
                select(Rating).filter(
                    Rating.image_id == image_id, Rating.user_id == user_id)
                )
            existing_rating = result.scalar_one_or_none()

            if existing_rating:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail=detail)
            
            return existing_rating

    async def add_rating(
            self, 
            image_id: int, 
            user_id: int, 
            value: int, 
            session: AsyncSession
        ):
        """
        Adds a rating to a photo. 
        Checks if the user has not rated before and if this is not their photo.
        """
        image = await crud_images.get_image_obj(image_id, session)

        crud_images._has_permission(
            image_obj_user_id=image.user_id,
            current_user_id=user_id)
        
        await self._get_existing_rating(
            image_id=image_id, 
            user_id=user_id, 
            session=session
        )

        await self._create_rating(
            image_id=image_id,
            user_id=user_id,
            value=value,
            session=session
        )

        await self._update_average_rating(
            image=image,
            image_id=image_id,
            session=session
        )

        await session.commit()
        await session.refresh(image)

        return {
            "message": "Rating added successfully", 
            "average_rating": image.average_rating
            }
    
    async def _get_rating_object(
            self,
            rating_id: int,
            session: AsyncSession,
            detail='Rating not found.'
    ):
        result = await session.execute(select(Rating).filter(Rating.id == rating_id))
        rating = result.scalar_one_or_none()

        if not rating:
            raise HTTPException(
                status_code=404, 
                detail=detail
            )
        return rating
        
    async def delete_rating(self, rating_id:int, session: AsyncSession):
        """
        Delete rating (available to moderators and administrators).
        """
        rating_object = await self._get_rating_object(rating_id, session)
        await session.delete(rating_object)

        image = await crud_images.get_image_obj(
            rating_object.image_id,
            session
        )
        
        await session.commit()
        
        await self._update_average_rating(
            image=image,
            image_id=rating_object.image_id,
            session=session
        )

        return {
            "message": "Rating deleted successfully"
        }

crud_ratings = RatingCrud()
