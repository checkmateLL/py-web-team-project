# routes by upload images & transformations

from fastapi import APIRouter, File, UploadFile, HTTPException, status, Depends, Query
from typing import List, Optional
from app.services.image_service import upload_image_service
from app.database.connection import get_conn_db
from app.services.auth_service import get_current_user  # уточнить импорт!
from app.database.models import User
from app.templates.schemas import ImageCreate

router = APIRouter(tags=['images'])

@router.post("/upload_image/",
             response_model=ImageCreate,
             status_code=status.HTTP_201_CREATED)
async def upload_file(description: str,
                      file: UploadFile = File(...),
                      tags: Optional[List[str]] = Query([]),
                      db: AsyncSession = Depends(get_conn_db),
                      current_user: User = Depends(get_current_user)) -> dict:
    if current_user.role not in [RoleSet.user, RoleSet.admin, RoleSet.moderator]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to upload images")

    if len(tags) > 5:
        raise HTTPException(status_code=400, detail="You can only add up to 5 tags.")

    try:
        # Upload file to Cloudinary
        result = await upload_image_service(description, file, tags, db, current_user)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



