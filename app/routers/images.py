from datetime import datetime
from fastapi import (
    APIRouter, 
    Body, 
    File, 
    HTTPException, 
    UploadFile, 
    status, 
    Depends, 
    Query
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from fastapi.responses import RedirectResponse

import app.schemas as sch
from app.database.connection import get_conn_db
from app.services.security.auth_service import role_deps
from app.services.qrcode_service import ImageGenerator, get_image_generator
from app.database.models import User
from app.repository.images import crud_images
from app.services.image_service import CloudinaryService

router = APIRouter(tags=['images'])

@router.post("/upload_image")
async def upload_image_endpoint(
    description: str = Body(..., min_length=3, max_length=255),
    file: UploadFile = File(...),
    tags: list[str] = Query(default_factory=list),
    session: AsyncSession = Depends(get_conn_db),
    current_user: User =  role_deps.all_users(),
    cloudinary_service: CloudinaryService = Depends(CloudinaryService)
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
        raise HTTPException(
            status_code=400, 
            detail="You can only add up to 5 tags."
        )

    allowed_types = {"image/jpeg", "image/png", "image/gif"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid file type. Only JPG, PNG and GIF'
        )

    upload_result = await cloudinary_service.upload_image(
        file=file, 
        folder=current_user.email
    )
    secure_url = upload_result.get("secure_url")
    public_id = upload_result.get("public_id")

    if not secure_url or not public_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cloudinary did not return required data."
        )

    tags_object = await crud_images.handle_tags(
        tags_names=tags, 
        session=session
    )

    image_object = await crud_images.create_image(
        url=secure_url,
        description=description,
        user_id=current_user.id,
        public_id=public_id,
        session=session
    )
    
    await crud_images._add_tag_to_image(image_object,tags_object,session)

    return sch.ImageResponseSchema(
        id=image_object.id,
        description=image_object.description,
        image_url=image_object.image_url,
        user_id=image_object.user_id,
        created_at=image_object.created_at,
        tags=[tag.name for tag in tags_object] 
    )

@router.delete(
        "/delete_image/{image_id}/", 
        status_code=status.HTTP_204_NO_CONTENT
    )
async def delete_image(
    image_id: int, 
    session: AsyncSession = Depends(get_conn_db), 
    current_user: User = role_deps.all_users()):
    """
    Deleta image by ID
    """
    try:
        deleted = await crud_images.delete_image(image_id, session, current_user)

        if not deleted:
            raise HTTPException(
                status_code=404, 
                detail="Image not found or access denied"
            )
        return {
            "message": "Image deleted successfully"
        }
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Unexpected error: {str(e)}"
        )

@router.post('/{image_id}/add_tags')
async def add_tags_to_image(
    image_id:int,
    tags:list[str] = Body(..., embed=True),
    session:AsyncSession = Depends(get_conn_db),
    current_user = role_deps.all_users()
):
    """
    add extra tag
    """
    user_image = await crud_images.get_image_obj(
        image_id=image_id,
        session=session
        )
    
    crud_images.check_permission(
        image_obj=user_image, 
        current_user_id=current_user.id 
    )

    existing_tags = {tag.name for tag in user_image.tags}
    new_tags = set(tags) - existing_tags
    if len(existing_tags) + len(new_tags) > 5:
        raise HTTPException(
            status_code=400, 
            detail="An image can have up to 5 tags"
        )

    tags_object = await crud_images.handle_tags(tags, session)
    await crud_images._add_tag_to_image(user_image, tags_object,session)

    return sch.ImageResponseSchema(
        id=user_image.id,
        description=user_image.description,
        image_url=user_image.image_url,
        user_id=user_image.user_id,
        created_at=user_image.created_at,
        tags=[tag.name for tag in user_image.tags] 
    )


@router.get('/image-info')
async def get_image_info(
    image_id:int,
    session:AsyncSession = Depends(get_conn_db),
    current_user:User = role_deps.all_users(),
):
    """
    get info about image
    """

    image_object = await crud_images.get_image_obj(
        image_id=image_id,
        session=session,
    )
    crud_images.check_permission(
        image_obj=image_object, 
        current_user_id=current_user.id 
    )
    
    return sch.ImageResponseSchema(
        id=image_object.id,
        description=image_object.description,
        image_url=image_object.image_url,
        user_id=image_object.user_id,
        created_at=image_object.created_at,
        tags=[tag.name for tag in image_object.tags] 
    )

@router.put(
        "/update_image_description/{image_id}/",
        response_model=sch.ImageResponseUpdateSchema
    )
async def update_image_description(
    image_id: int, 
    description: str, 
    session: AsyncSession = Depends(get_conn_db), 
    current_user: User = role_deps.all_users()
    ):
    update_image_object = await crud_images.update_image_description(
        image_id, 
        description, 
        session, 
        current_user
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
    _: User = role_deps.all_users(),
):
    """find url by ImageId"""
    image_object= await crud_images.get_image_url(
        image_id, 
        session)
    if not image_object:
        raise HTTPException(
            status_code=404, 
            detail="Image not found"
    )
    return RedirectResponse(url=image_object.image_url)


@router.post(
        "/transform_image/{image_id}/", 
        response_model=sch.TransformationResponseSchema,
        status_code=status.HTTP_200_OK
    )
async def transform_image(
    image_id: int, 
    transformation_params: sch.TransformationParameters = Body(...),
    session: AsyncSession = Depends(get_conn_db), 
    current_user: User = role_deps.all_users(),
    cloudinary_service: CloudinaryService = Depends(CloudinaryService),
    qr_service: ImageGenerator = Depends(get_image_generator)
):
    """
    Transform image using given transformation parameters and generate QR code.

    Args:
        image_id (int): ID of the image to transform.
        transformation_params (dict): Dictionary with parameters for the 
        image transformation.
        session (AsyncSession): The database session to interact with the database.
        current_user (User): The user making the request.
        cloudinary_service (CloudinaryService): Service for image transformation.
        qr_service (ImageGenerator): Service for generating a QR code for the image.

    Returns:
        TransformationResponseSchema: Contains transformation URL, QR code URL,
        and image ID.

    Raises:
        HTTPException: If the image cannot be found or the transformation fails.
    """
    current_image = await crud_images.get_image_obj(
        image_id=image_id,
        session=session
    )
    
    crud_images.check_permission(
        image_obj=current_image,
        current_user_id=current_user.id
        
    )

    ts_url = await cloudinary_service.transform_image(
        image=current_image,
        crop=transformation_params.crop,
        blur=transformation_params.blur,
        circular=transformation_params.circular,
        grayscale=transformation_params.grayscale
    )

    qrcode_url = qr_service.generate_qr_code(current_image.image_url)

    data = await crud_images.create_transformed_images(
        transformed_url=ts_url,
        qr_code_url=qrcode_url,
        image_id=current_image.id,
        session=session
    )
    return data

@router.get("/my_images/", response_model=list[sch.ImageResponseSchema])
async def get_user_images(
    session: AsyncSession = Depends(get_conn_db),
    current_user: User = role_deps.all_users(),
):
    """
    Get all images uploaded by the current user.

    Args:
        session: Database session.
        current_user: Current authenticated user.

    Returns:
        List of ImageResponseSchema objects containing image details.
    """
    images = await crud_images.get_images_by_user_id(current_user.id, session)
    if not images:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You have no images."
        )
    return [
        sch.ImageResponseSchema(
            id=image.id,
            description=image.description,
            image_url=image.image_url,
            user_id=image.user_id,
            tags=[tag.name for tag in image.tags],
            average_rating=getattr(image, 'average_rating', 0.0),
            created_at=getattr(image, 'created_at', datetime.now())
        )
        for image in images
    ]

@router.get("/search_images/", response_model=list[sch.ImageResponseSchema])
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
    images = await crud_images.search_images(session ,query, tag, order_by)
    return [sch.ImageResponseSchema(
        id=img.id,
        description=img.description,
        image_url=img.image_url,
        user_id=img.user_id,
        tags=[tag.name for tag in img.tags],
        average_rating=img.average_rating,
        created_at=img.created_at
    ) for img in images]
