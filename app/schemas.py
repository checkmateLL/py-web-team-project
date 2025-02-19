from pydantic import BaseModel, EmailStr
from datetime import datetime

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
    user_id: int
    image_id: int

class CommentUpdate(BaseModel):
    text: str

class CommentResponse(BaseModel):
    id: int
    text: str
    created_at: datetime
    updated_at: datetime
    user_id: int
    image_id: int
    
    class Config:
        from_attributes = True