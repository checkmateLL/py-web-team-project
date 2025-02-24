from fastapi import APIRouter, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime


from app.repository.images import crud_images
from app.database.connection import get_conn_db
from app.services.security.auth_service import role_deps
from app.database.models import User
import app.schemas as sch

router = APIRouter(tags=['/serch'])

@router.get("/images/", response_model=list[sch.ImageResponseSchema])
async def search_images(
    query: str = Query(None, description="Search by description"),
    tag: str = Query(None, description="Filter by tag"),
    order_by: str = Query("date", description="Sort by 'date' or 'rating'"),
    session: AsyncSession = Depends(get_conn_db),
    _: User = role_deps.all_users(),
):
    """
    Search for images by description or tag.
    Ability to sort by rating or upload date.
    """
    images = await crud_images.search_images(query, tag, order_by, session)
    return [sch.ImageResponseSchema(
        id=img.id,
        description=img.description,
        image_url=img.image_url,
        user_id=img.user_id,
        tags=[tag.name for tag in img.tags],
        average_rating=img.average_rating,
        created_at=img.created_at
    ) for img in images]

@router.get("/by_user/", response_model=list[sch.ImageResponseSchema])
async def search_images_by_user(
    username: str = Query(..., description="Username to search images"),
    session: AsyncSession = Depends(get_conn_db),
    _: User = role_deps.admin_moderator(),
):
    """
    Search images by user (available to moderators and administrators).
    """
    images = await crud_images.search_by_user(username, session)
    return [sch.ImageResponseSchema(
        id=img.id,
        description=img.description,
        image_url=img.image_url,
        user_id=img.user_id,
        tags=[tag.name for tag in img.tags],
        average_rating=getattr(img, 'average_rating', 0.0),
        created_at=getattr(img, 'created_at', datetime.now())
    ) for img in images]
