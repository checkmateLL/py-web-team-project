from datetime import datetime
from fastapi import (
    APIRouter, 
    Body, 
    File, 
    HTTPException,
    Path, 
    UploadFile, 
    status, 
    Depends, 
    Query,
    Request
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
from app.config import settings
from app.utils.rate_limit import rate_limited

router = APIRouter(tags=['images'])

@router.post(
        "/upload_image",
        response_model=sch.ImageResponseSchema,
        summary='Upload image'
)
@rate_limited(
    max_calls=settings.RL_TIMES_UPLOAD_PHOTO, 
    time_frame=settings.RL_MINUTES_UPLOAD_PHOTO
)
async def upload_image_endpoint(
    request: Request,
    description: str = Body(
        ..., 
        min_length=3, 
        max_length=255,
        description='Image Description (3 - 255 symbol).'
        ),
    file: UploadFile = File(
        ...,
        description='Image file (to 5MB).'
        ),
    tags: list[str] = Query(default_factory=list, description='List tags, max 5 tags'),
    session: AsyncSession = Depends(get_conn_db),
    current_user: User =  role_deps.all_users(),
    cloudinary_service: CloudinaryService = Depends(CloudinaryService),
):
    """
    Upload image

    ## Description:
    - Check file size.
    - Max 5 tag.
    - Upload file to Cloudinary.
    - Save metadate in database.

    ## Errors:
    - **400**: file to big, fail format, to many tags.
    - **500**: error upload in Cloudinary.
    """
    await crud_images._check_size_file(file)
    await crud_images._check_allowed_types(file)
    await crud_images._check_tags_count(tags)

    upload_result = await cloudinary_service.upload_image(
        file=file, 
        folder=current_user.email
    )
    secure_url, public_id = await crud_images.get_data_cloudinary(upload_result)
  
    tags_object = await crud_images.handle_tags(tags_names=tags,session=session)
         
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
        status_code=status.HTTP_204_NO_CONTENT,
        responses={
            204: {"description": "Image deleted successfully"},
            404: {"description": "Image not found or access denied"},
            500: {"description": "Database error or unexpected error occurred"}
        }
)
async def delete_image(
    image_id: int = Path(..., gt=0, description="The ID of the image to delete"), 
    session: AsyncSession = Depends(get_conn_db), 
    current_user: User = role_deps.all_users()):
    """
    Delete an image by its ID. Owner image permission

    ### Parameters:
    - **image_id**: The ID of the image to delete. Must be greater than 0.
    - **current_user**: The currently authenticated user (automatically injected).

    ### Returns:
    - **204 No Content**: If the image was successfully deleted.
    - **404 Not Found**: If the image does not exist or the user does not have 
    permission to delete it.
    - **500 Internal Server Error**: If a database error or unexpected error occurs.

    ### Example:
    - **Request**: `DELETE /images/delete_image/1/`
    - **Response**: 204 No Content
    """
    try:
        deleted = await crud_images.delete_image(image_id, session, current_user)

        if not deleted:
            raise HTTPException(
                status_code=404, 
                detail="Image not found or access denied"
            )
        return {"message": "Image deleted successfully"}
    
    except HTTPException:
        raise

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Detabese error occurred'
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Unexpected error occurred'
        )
    
@router.post(
    '/{image_id}/add_tags',
    response_model=sch.ImageResponseSchema,
    responses={
        200: {"description": "Tags added successfully"},
        400: {"description": "An image can have up to 5 tags"},
        403: {"description": "Permission denied"},
        404: {"description": "Image not found"},
        500: {"description": "Internal server error"}
    }
    )
async def add_tags_to_image(
    image_id: int = Path(..., gt=0, description='The ID of the image to add tags to.'),
    tags:list[str] = Body(..., embed=True, dedcriptions='List if tags to add to the image.'),
    session:AsyncSession = Depends(get_conn_db),
    current_user = role_deps.all_users()
):
    """
    Add extra tags to an image. Image owner permission.

    ### Parameters:
    - **image_id**: The ID of the image to add tags to. Must be greater than 0.
    - **tags**: A list of tags to add to the image.
    - **current_user**: The currently authenticated user (automatically injected).

    ### Returns:
    - **200 OK**: Tags added successfully. Returns the updated image details.
    - **400 Bad Request**: If the image already has 5 tags or the new tags exceed the limit.
    - **403 Forbidden**: If the current user does not have permission to add tags to the image.
    - **404 Not Found**: If the image does not exist.
    - **500 Internal Server Error**: If an unexpected error occurs.

    ### Example:
    - **Request**: `POST /images/1/add_tags`
      ```json
      {
        "tags": ["nature", "landscape"]
      }
      ```
    - **Response**: 200 OK
      ```json
      {
        "id": 1,
        "description": "A beautiful landscape",
        "image_url": "https://example.com/image.jpg",
        "user_id": 1,
        "created_at": "2023-10-01T12:00:00",
        "tags": ["nature", "landscape", "travel"]
      }
      ```
    """
    try:
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
    
    except HTTPException:
        raise

    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Unexpected error occured: {str(err)}'
        )

@router.get('/image-info/{image_id}', response_model=sch.ImageResponseSchema)
async def get_image_info(
    image_id:int = Path(..., gt=0, description="The ID of the image"),
    session:AsyncSession = Depends(get_conn_db),
    current_user:User = role_deps.all_users(),
):
    """
    Get information about an image. Image owner permission.

    - **image_id**: The ID of the image whose information is requested.
    - Returns detailed information about the image, including its description, URL, 
    associated user ID, creation date, and tags.

    **Permissions**:
    - The user must have the necessary permissions to access the image.
    - If the user does not have access, an error will be raised.

    ### Response schema:
    - `id`: The unique identifier of the image.
    - `description`: The description of the image.
    - `image_url`: The URL where the image is stored.
    - `user_id`: The ID of the user who uploaded the image.
    - `created_at`: The creation date of the image.
    - `tags`: A list of tags associated with the image.

    ### Example response:
    ```json
    {
        "id": 1,
        "description": "A beautiful sunset over the mountains.",
        "image_url": "http://example.com/images/1.jpg",
        "user_id": 123,
        "created_at": "2025-02-28T12:00:00",
        "tags": ["sunset", "mountains", "nature"]
    }
    ```

    **Errors**:
    - `401 Unauthorized`: If the user is not authorized to access the image.
    - `403 Forbidden`: If the user does not have permission to view the image.
    - `404 Not Found`: If the image with the given `image_id` does not exist.
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
    description: str = Body(
        ..., 
        min_length=3, 
        max_length=255,
        description='Image Description (3 - 255 symbol).'
        ), 
    image_id: int = Path(..., gt=0, description="The ID of the image"),
    session: AsyncSession = Depends(get_conn_db), 
    current_user: User = role_deps.all_users()
    ):
    """
    Update the description of an image.

    - **image_id**: The ID of the image to update.
    - **description**: A new description for the image, with a length between 3 and 255 characters.

    **Permissions**:
    - The user must have permission to update the image description.
    - If the user does not have permission, an error will be raised.

    ### Request body:
    - `description`: The new description for the image (3-255 characters).

    ### Response schema:
    - `id`: The unique identifier of the image.
    - `description`: The updated description of the image.
    - `image_url`: The URL where the image is stored.
    - `user_id`: The ID of the user who uploaded the image.

    ### Example request:
    ```json
    {
        "description": "A beautiful view of the ocean at sunset."
    }
    ```

    ### Example response:
    ```json
    {
        "id": 1,
        "description": "A beautiful view of the ocean at sunset.",
        "image_url": "http://example.com/images/1.jpg",
        "user_id": 123
    }
    ```

    **Errors**:
    - `400 Bad Request`: If the description is too short or too long.
    - `401 Unauthorized`: If the user is not authorized to update the image description.
    - `403 Forbidden`: If the user does not have permission to update the image.
    - `404 Not Found`: If the image with the given `image_id` does not exist.
    """
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
    image_id: int = Path(..., gt=0, description="The ID of the image"),
    session: AsyncSession = Depends(get_conn_db),
    _: User = role_deps.all_users(),
):
    """
    Get the image URL by its ID. Not permission owner image.

    - **image_id**: The ID of the image to retrieve the URL for.

    ### Response:
    - Redirects to the URL where the image is stored.

    ### Errors:
    - `404 Not Found`: If the image with the given `image_id` does not exist.
    
    ### Example response:
    A redirect response will send the client to the image URL, e.g.:
    ```http
    HTTP/1.1 302 Found
    Location: http://example.com/images/1.jpg
    ```

    **Note**: If the image is not found, the server will respond with a `404 Not Found` error.
    """
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
@rate_limited(
    max_calls=settings.RL_TIMES_TF_IMAGE,
    time_frame=settings.RL_MINUTES_TF_IMAGE
)
async def transform_image(
    request: Request,
    image_id: int = Path(..., gt=0, description="The ID of the image"),
    transformation_params: sch.TransformationParameters = Body(...),
    session: AsyncSession = Depends(get_conn_db), 
    current_user: User = role_deps.all_users(),
    cloudinary_service: CloudinaryService = Depends(CloudinaryService),
    qr_service: ImageGenerator = Depends(get_image_generator),
    ):
    """
    Transform an image using the specified transformation parameters and generate a QR code for it.

    ### Arguments:
    - **image_id** (int): The ID of the image to transform.
    - **transformation_params** (TransformationParameters): Transformation parameters such as cropping, 
      blurring, circular cropping, and grayscale options.
    - **session** (AsyncSession): The database session used to interact with the database.
    - **current_user** (User): The user making the request, whose permissions will be checked.
    - **cloudinary_service** (CloudinaryService): Service responsible for applying transformations to the image.
    - **qr_service** (ImageGenerator): Service responsible for generating the QR code for the transformed image.

    ### Returns:
    A `TransformationResponseSchema` object containing:
    - **transformed_image_url**: The URL of the transformed image.
    - **qr_code_url**: The URL of the generated QR code for the image.
    - **image_id**: The ID of the transformed image in the database.

    ### Example request:
    ```json
    {
        "crop": {"width": 100, "height": 100, "x": 10, "y": 10},
        "blur": 5,
        "circular": true,
        "grayscale": true
    }
    ```

    ### Example response:
    ```json
    {
        "transformed_image_url": "https://res.cloudinary.com/image.jpg",
        "qr_code_url": "https://api.qrserver.com/v1/create-qr-code/?data=https://res.cloudinary.com/image.jpg",
        "image_id": 1
    }
    ```

    ### Errors:
    - `400 Bad Request`: If the transformation parameters are invalid.
    - `401 Unauthorized`: If the user is not authorized to transform the image.
    - `403 Forbidden`: If the user does not have permission to modify the image.
    - `404 Not Found`: If the image with the given `image_id` does not exist.
    - `422 Unprocessable Entity`: If the transformation fails due to incorrect parameters or a service issue.
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
    ts_url
    qrcode_url = qr_service.generate_qr_code(ts_url['transformed_url'])

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
    Get all images uploaded by the current authenticated user.

    ### Arguments:
    - **session** (AsyncSession): The database session for interacting with the database.
    - **current_user** (User): The currently authenticated user making the request.

    ### Returns:
    A list of `ImageResponseSchema` objects containing the following image details:
    - **id**: ID of the image.
    - **description**: Description of the image.
    - **image_url**: URL of the image.
    - **user_id**: ID of the user who uploaded the image.
    - **tags**: List of tags associated with the image.
    - **average_rating**: Average rating of the image (defaults to 0.0 if not available).
    - **created_at**: Date and time when the image was uploaded (defaults to the current time if not available).

    ### Errors:
    - `404 Not Found`: If the user has no uploaded images.

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

    **Note**: If the user has no images, the response will return a `404 Not Found` error with the message "You have no images."
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