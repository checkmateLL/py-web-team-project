# request from rating system
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status
from app.database.models import Rating, Image
from sqlalchemy.sql import func

class RatingCrud:
    async def add_rating(self, image_id: int, user_id: int, value: int, session: AsyncSession):
        """
        Adds a rating to a photo. 
        Checks if the user has not rated before and if this is not their photo.
        """
        result = await session.execute(select(Image).filter(Image.id == image_id))
        image = result.scalar_one_or_none()
        
        if not image:
            raise HTTPException(status_code=404, detail="Image not found.")

        if image.user_id == user_id:
            raise HTTPException(status_code=403, detail="You cannot rate your own image.")

        result = await session.execute(select(Rating).filter(Rating.image_id == image_id, Rating.user_id == user_id))
        existing_rating = result.scalar_one_or_none()

        if existing_rating:
            raise HTTPException(status_code=400, detail="You have already rated this image.")

        new_rating = Rating(image_id=image_id, user_id=user_id, value=value)
        session.add(new_rating)

        avg_result = await session.execute(
            select(func.avg(Rating.value)).filter(Rating.image_id == image_id)
        )
        avg_rating = avg_result.scalar() or 0.0
        image.average_rating = avg_rating

        await session.commit()
        await session.refresh(image)

        return {"message": "Rating added successfully", "average_rating": avg_rating}
    
    async def delete_rating(self, rating_id:int, session: AsyncSession):
        """
        Delete rating (available to moderators and administrators).
        """
        result = await session.execute(select(Rating).filter(Rating.id == rating_id))
        rating = result.scalar_one_or_none()

        if not rating:
            raise HTTPException(status_code=404, detail="Rating not found.")

        await session.delete(rating)

        # Оновлюємо середній рейтинг зображення після видалення
        avg_result = await session.execute(
            select(func.avg(Rating.value)).filter(Rating.image_id == rating.image_id)
        )
        avg_rating = avg_result.scalar() or 0.0

        result = await session.execute(select(Image).filter(Image.id == rating.image_id))
        image = result.scalar_one_or_none()

        if image:
            image.average_rating = avg_rating
            await session.commit()
            await session.refresh(image)

        return {"message": "Rating deleted successfully"}

crud_ratings = RatingCrud()
