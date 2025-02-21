from fastapi import (
    APIRouter,
    Body,
    File,
    HTTPException,
    UploadFile,
    status,
    Depends,
    Query,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from fastapi.responses import RedirectResponse

import app.schemas as sch
from app.database.connection import get_conn_db
from app.services.security.auth_service import role_deps
from app.database.models import User
from app.repository.images import crud_images
from app.services.image_service import CloudinaryService

router = APIRouter(tags=["images"])


@router.post("/upload_image")
async def upload_image_endpoint(
    description: str = Body(..., min_length=3, max_length=255),
    file: UploadFile = File(...),
    tags: list[str] = Query(default_factory=list),
    session: AsyncSession = Depends(get_conn_db),
    current_user: User = role_deps.all_users(),
    cloudinary_service: CloudinaryService = Depends(CloudinaryService),
):
    """
    Upload image, added descriptions and regs

    Args:
        description
        file
        tags
        session
        current_user
        cloudinary_service
    Returns
        ImageResponseSchema
    Raises
        HTTPException: If count tegs match 5.
        HTTPException: If Cloudinary not return `secure_url` &
        `public_id`.
        HTTPException: IF file not image.
    """
    if tags and len(tags) > 5:
        raise HTTPException(status_code=400, detail="You can only add up to 5 tags.")

    allowed_types = {"image/jpeg", "image/png", "image/gif"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only JPG, PNG and GIF",
        )

    upload_result = await cloudinary_service.upload_image(file, current_user.email)
    secure_url = upload_result.get("secure_url")
    public_id = upload_result.get("public_id")

    if not secure_url or not public_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cloudinary did not return required data.",
        )

    tags_object = await crud_images.handle_tags(tags, session)

    image_object = await crud_images.create_image(
        secure_url, description, current_user.id, public_id, session
    )

    await crud_images._add_tag_to_image(image_object, tags_object, session)

    return sch.ImageResponseSchema(
        id=image_object.id,
        description=image_object.description,
        image_url=image_object.image_url,
        user_id=image_object.user_id,
        tags=[tag.name for tag in tags_object],
    )


@router.delete("/delete_image/{image_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    image_id: int,
    session: AsyncSession = Depends(get_conn_db),
    current_user: User = role_deps.all_users(),
):
    """
    Deleta image by ID
    """
    try:
        deleted = await crud_images.delete_image(image_id, session, current_user)
        if not deleted:
            raise HTTPException(
                status_code=404, detail="Image not found or access denied"
            )
        return {"message": "Image deleted successfully"}
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.put(
    "/update_image_description/{image_id}/",
    response_model=sch.ImageResponseUpdateSchema,
)
async def update_image_description(
    image_id: int,
    description: str,
    session: AsyncSession = Depends(get_conn_db),
    current_user: User = role_deps.all_users(),
):
    update_image_object = await crud_images.update_image_description(
        image_id, description, session, current_user
    )

    return sch.ImageResponseUpdateSchema(
        id=update_image_object.id,
        description=update_image_object.description,
        image_url=update_image_object.image_url,
        user_id=update_image_object.user_id,
    )


@router.get("/get_image/{image_id}/")
async def get_image_by_id(
    image_id: int,
    session: AsyncSession = Depends(get_conn_db),
    current_user: User = role_deps.all_users(),
):
    """find url by ImageId"""
    image_object = await crud_images.get_image_url(image_id, session)
    if not image_object:
        raise HTTPException(status_code=404, detail="Image not found")
    return RedirectResponse(url=image_object.image_url)


@router.get("/transform_image/")
async def transform_image(
    public_id: str = Query(...),
    crop: bool = Query(False),
    blur: bool = Query(False),
    circular: bool = Query(False),
    grayscale: bool = Query(False),
    cloudinary_service: CloudinaryService = Depends(CloudinaryService),
):
   
    transformations = cloudinary_service.generate_transformation_string(
        crop=crop, 
        blur=blur, 
        circular=circular, 
        grayscale=grayscale
    )
    url = cloudinary_service.generate_transformed_url(public_id, transformations)
    return RedirectResponse(url=url)

   
