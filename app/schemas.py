from pydantic import BaseModel, EmailStr, Field, constr
from datetime import datetime
from typing import Optional, Annotated

class RegisterUser(BaseModel):
    user_name: str
    email: EmailStr
    password: str

class ResponseUser(BaseModel):
    id: int
    username: str
    email: EmailStr
    is_active: bool
    role: str  
    created_at: datetime

    @classmethod
    def from_orm(cls, obj):
        return cls(
            id=obj.id,
            username=obj.username,
            email=obj.email,         
            is_active=obj.is_active,
            role=obj.role.value,    
            created_at=obj.register_on 
        )

    class Config:
        from_attributes = True
    
class ResponseLogin(BaseModel):
    access_token: str
    refresh_token:str
    token_type: str

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

Tag = Annotated[str, constr(
    min_length=1,
    max_length=50
)]

class ImageCreate(BaseModel):
    url: str
    qr_code: str
    description: str
    owner_id: int
    tags: Optional[list[Tag]] = []

class ImageResponseSchema(BaseModel):
    id: int
    description: str
    file_url: str = Field(..., alias="image_url") 
    owner_id: int = Field(..., alias="user_id")
    tags: list  
    class Config:

        from_attributes = True  

class ImageResponseUpdateSchema(BaseModel):
    id: int
    description: str
    file_url: str = Field(..., alias="image_url") 
    owner_id: int = Field(..., alias="user_id")

    class Config:
        from_attributes = True  