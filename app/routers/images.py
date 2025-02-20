# routes by upload images & transformations
from fastapi import APIRouter, File, HTTPException, UploadFile, status, Depends, Query
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import RedirectResponse

import app.schemas as sch
from app.database.connection import get_conn_db
from app.services.security.auth_service import role_deps
from app.database.models import User
from app.repository.images import crud_images
from app.services.image_service import CloudinaryService

router = APIRouter(tags=['images'])

@router.post("/upload_image")
async def upload_image_endpoint(
    description: str,
    file: UploadFile = File(...),
    tags: list[str] = Query(default_factory=list),
    session: AsyncSession = Depends(get_conn_db),
    current_user: User =  role_deps.all_users(),
    cloudinary_service: CloudinaryService = Depends(CloudinaryService)
):
    
    if tags and len(tags) > 5:
        raise HTTPException(
            status_code=400, 
            detail="You can only add up to 5 tags."
        )

    upload_result = await cloudinary_service.upload_image(
        file, 
        current_user.email
    )
    secure_url = upload_result.get("secure_url")
    public_id = upload_result.get("public_id")

    if not secure_url or not public_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cloudinary did not return required data."
        )

    tags_object = await crud_images.handle_tags(tags,session)

    image_object = await crud_images.create_image(
        secure_url,
        description,
        current_user.id,
        public_id,
        session
    )
    
    await crud_images._add_tag_to_image(image_object,tags_object,session)

    return {
        'id':image_object.id,
        'description':image_object.description,
        'image_url':image_object.image_url,
        'owner_id':image_object.user_id,
        'tags':[tag for tag in tags_object]
    }
    # return sch.ImageResponseSchema(
    #     id=image_object.id,
    #     description=image_object.description,
    #     image_url=image_object.image_url,  
    #     user_id=image_object.user_id,
    #     tags=image_object.tags
    # ).model_dump(by_alias=True)

@router.delete("/delete_image/{image_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    image_id: int, 
    session: AsyncSession = Depends(get_conn_db), 
    current_user: User = role_deps.all_users()):
    await crud_images.delete_image(
        image_id, 
        session, 
        current_user
    )

@router.put(
        "/update_image_description/{image_id}/",
        response_model=sch.ImageResponseSchema
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
    return {}
    # return sch.ImageResponseSchema(
    #     id=update_image_object.id,
    #     description=update_image_object.description,
    #     image_url=update_image_object.image_url,  
    #     user_id=update_image_object.user_id,
    #     tags=update_image_object.tags
    # ).model_dump(by_alias=True)
    

@router.get("/get_image/{image_id}/")
async def get_image_by_id(
    image_id: int, 
    session: AsyncSession = Depends(get_conn_db),
    current_user: User = role_deps.all_users()
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


