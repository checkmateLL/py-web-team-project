from fastapi import APIRouter, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.images import crud_images
from app.database.connection import get_conn_db
from app.services.security.auth_service import role_deps
from app.database.models import User
import app.schemas as sch

router = APIRouter(tags=['search'])

@router.get("/search_images/", response_model=list[sch.ImageResponseSchema])
async def search_images(
    query: str = Query(None, description="Search by description"),
    tag: str = Query(None, description="Filter by tag"),
    order_by: str = Query("date", description="Sort by 'date' or 'rating'"),
    session: AsyncSession = Depends(get_conn_db),
    _: User = role_deps.all_users(),
):
    """
    Search for images by description or tag with the ability to sort by rating or upload date.

    ### Arguments:
    - **query** (str, optional): Search query to filter images by their description.
    - **tag** (str, optional): Filter images by a specific tag.
    - **order_by** (str, default "date"): Sort images by either 'date' (upload date) or 'rating' (average rating).
    - **session** (AsyncSession): The database session for interacting with the database.
    - **_** (User): The current authenticated user making the request.

    ### Returns:
    A list of `ImageResponseSchema` objects containing the following image details:
    - **id**: ID of the image.
    - **description**: Description of the image.
    - **image_url**: URL of the image.
    - **user_id**: ID of the user who uploaded the image.
    - **tags**: List of tags associated with the image.
    - **average_rating**: Average rating of the image.
    - **created_at**: Date and time when the image was uploaded.

    ### Errors:
    - `400 Bad Request`: If the `order_by` parameter is not 'date' or 'rating'.

    ### Example response:
    ```json
    [
        {
            "id": 1,
            "description": "A beautiful sunset",
            "image_url": "http://example.com/sunset.jpg",
            "user_id": 123,
            "tags": ["nature", "sunset"],
            "average_rating": 4.5,
            "created_at": "2025-02-28T14:00:00"
        },
        {
            "id": 2,
            "description": "A mountain view",
            "image_url": "http://example.com/mountain.jpg",
            "user_id": 123,
            "tags": ["nature", "mountain"],
            "average_rating": 4.0,
            "created_at": "2025-02-25T10:30:00"
        }
    ]
    ```

    ### Query Parameters:
    - **query**: Optional query string to search image descriptions (e.g., "sunset", "mountain").
    - **tag**: Optional tag to filter images (e.g., "nature", "travel").
    - **order_by**: Sort images by either `date` (upload date) or `rating` (average rating).

    **Note**: If the `order_by` value is invalid (not 'date' or 'rating'), a `400 Bad Request` error will be raised.
    """
    images = await crud_images.search_images(session ,query, tag, order_by)

    if not images:
        return []
    
    return [sch.ImageResponseSchema(
        id=img.id,
        description=img.description,
        image_url=img.image_url,
        user_id=img.user_id,
        tags=[tag.name for tag in img.tags],
        average_rating=img.average_rating,
        created_at=img.created_at
    ) for img in images]
