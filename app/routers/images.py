# routes by upload images & transformations

from fastapi import APIRouter, File, UploadFile, HTTPException, status, Depends, Query
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.image_service import upload_image
from app.database.connection import get_conn_db
from app.services.auth_service import get_current_user  # уточнить импорт!
from app.database.models import User
from app.templates.schemas import ImageResponseSchema
from app.repository.images import delete_image, update_image_description, get_image_by_url

router = APIRouter(tags=['images'])

@router.post("/upload_image/",
             response_model=ImageResponseSchema,
             status_code=status.HTTP_201_CREATED)
async def upload_image(description: str,
                      file: UploadFile = File(...),
                      tags: Optional[List[str]] = Query([]),
                      db: AsyncSession = Depends(get_conn_db),
                      current_user: User = Depends(get_current_user)) -> dict:
    return await upload_image(description, file, tags, db, current_user)

@router.delete("/delete_image/{image_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(image_id: int, db: AsyncSession = Depends(get_conn_db), current_user: User = Depends(get_current_user)):
    await delete_image(image_id, db, current_user)

@router.put("/update_image_description/{image_id}/", response_model=ImageResponseSchema)
async def update_image_description(image_id: int, description: str, db: AsyncSession = Depends(get_conn_db), current_user: User = Depends(get_current_user)):
    return await update_image_description(image_id, description, db, current_user)

@router.get("/get_image/{image_url}/", response_model=ImageResponseSchema)
async def get_image_by_url(image_url: str, db: AsyncSession = Depends(get_conn_db)):
    return await get_image_by_url(image_url, db)



