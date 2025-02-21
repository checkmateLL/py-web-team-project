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
    bio: Optional[str] = None
    avatar_url: Optional[str] = None

    @classmethod
    def from_orm(cls, obj):
        return cls(
            id=obj.id,
            username=obj.username,
            email=obj.email,         
            is_active=obj.is_active,
            role=obj.role.value,    
            created_at=obj.register_on,
            bio=obj.bio,
            avatar_url=obj.avatar_url
        )

    class Config:
        from_attributes = True

class UserProfileResponse(BaseModel):
    username: str
    created_at: datetime
    total_images: int
    total_comments: int
    total_ratings_given: int
    member_since: str  # Human readable format
    avatar_url: Optional[str] = None
    bio: Optional[str] = None

    class Config:
        from_attributes = True

class UserProfileEdit(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = None

class UserProfileFull(ResponseUser):
    total_images: int
    total_comments: int
    total_ratings_given: int
    member_since: str
    
class ResponseLogin(BaseModel):
    access_token: str
    refresh_token:str
    token_type: str

class CommentCreate(BaseModel):
    text: constr(min_length=1, max_length=500)


class CommentUpdate(BaseModel):
    text: constr(min_length=1, max_length=500)


class CommentResponse(BaseModel):
    id: int
    text: str
    created_at: datetime
    updated_at: datetime
    user_id: int
    image_id: int

    class Config:
        from_attributes = True

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

