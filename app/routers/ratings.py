from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_conn_db
from app.database.models import User
from app.repository.ratings import crud_ratings

from app.services.security.auth_service import role_deps

router = APIRouter(tags=['ratings'])

@router.post("/rate_image/{image_id}/")
async def rate_image(
    image_id: int, 
    value: int, 
    session: AsyncSession = Depends(get_conn_db), 
    current_user: User = role_deps.all_users(),
    detail='Rating must be between 1 and 5.'
):
    """
    Add rating to image.
    """
    if value < 1 or value > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=detail
        )

    return await crud_ratings.add_rating(image_id, current_user.id, value, session)
