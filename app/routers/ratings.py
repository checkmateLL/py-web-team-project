# api by rating system
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_conn_db
from app.database.models import User
from app.repository.ratings import crud_ratings

router = APIRouter(tags=['ratings'])

@router.post("/rate_image/{image_id}/")
async def rate_image(
    image_id: int, 
    value: int, 
    session: AsyncSession = Depends(get_conn_db), 
    current_user: User = Depends(role_deps.all_users())
):
    """
    Add rating to image.
    """
    if value < 1 or value > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5.")

    return await crud_ratings.add_rating(image_id, current_user.id, value, session)

@router.delete("/delete_rating/{rating_id}/")
async def delete_rating(
    rating_id: int, 
    session: AsyncSession = Depends(get_conn_db), 
    current_user: User = Depends(role_deps.moderators_and_admins())
):
    """
    Delete rating(Only moderators and admins).
    """
    return await crud_ratings.delete_rating(rating_id, session)
