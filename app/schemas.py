# pydantic-schemas (validation request data)
from pydantic import BaseModel, constr
from datetime import datetime
from typing import List, Optional


class CommentCreate(BaseModel):
    text: str


class CommentUpdate(BaseModel):
    text: str


class CommentResponse(BaseModel):
    id: int
    text: str
    created_at: datetime
    updated_at: datetime
    user_id: int
    post_id: int


class ImageCreate(BaseModel):
    url: str
    qr_code: str
    description: str
    owner_id: int
    tags: Optional[List[constr(min_length=1, max_length=50)]] = []


class ImageResponseSchema(BaseModel):
    id: int
    description: str
    file_url: str
    tags: List[str]
    comments: List[CommentResponse]  

    class Config:
        from_attributes = True 
        #orm_mode = True   for  Pydantic v2
