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