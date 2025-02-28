from pydantic import BaseModel, EmailStr, Field, constr, HttpUrl, ConfigDict, field_validator, StringConstraints, ValidationInfo, ConfigDict, validator
from datetime import datetime
from typing import Optional, Annotated

USERNAME_PATTERN = "^[a-zA-Z0-9_-]+$"
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 50

PASSWORD_MIN_LENGTH = 6
PASSWORD_MAX_LENGTH = 100

def validate_username(username: str) -> str:
    """Validate username according to standard rules"""
    import re
    
    if username is None:
        return None
        
    if not username:
        raise ValueError("Username cannot be empty")
        
    if len(username) < USERNAME_MIN_LENGTH:
        raise ValueError(f"Username must be at least {USERNAME_MIN_LENGTH} characters long")
        
    if len(username) > USERNAME_MAX_LENGTH:
        raise ValueError(f"Username cannot exceed {USERNAME_MAX_LENGTH} characters")
        
    if not re.match(USERNAME_PATTERN, username):
        raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        
    return username

def validate_password(password: str) -> str:
    """Validate password according to standard rules"""
    if not password:
        raise ValueError("Password cannot be empty")
        
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters long")
        
    if len(password) > PASSWORD_MAX_LENGTH:
        raise ValueError(f"Password cannot exceed {PASSWORD_MAX_LENGTH} characters")
    
    if not any(char.isdigit() for char in password):
        raise ValueError("Password must contain at least one digit")
        
    if not any(char.isupper() for char in password):
        raise ValueError("Password must contain at least one uppercase letter")
        
    return password

class RegisterUser(BaseModel):
    user_name: Annotated[str, StringConstraints(min_length=USERNAME_MIN_LENGTH, 
                                              max_length=USERNAME_MAX_LENGTH,
                                            pattern=USERNAME_PATTERN)]
    email: EmailStr
    password: str

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "user_name": "john_doe",
                "email": "john@example.com",
                "password": "123456"
            }
        }
    )

    @field_validator("password")
    @classmethod
    def validate_user_password(cls, value: str) -> str:
        return validate_password(value)


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

    model_config = ConfigDict(
        from_attributes= True
    )


class UserProfileResponse(BaseModel):
    username: str
    email: EmailStr
    created_at: datetime
    avatar_url: Optional[HttpUrl] = None
    bio: Optional[str] = None
    total_images: int
    total_comments: int
    total_ratings_given: int
    member_since: str
    
    @field_validator('avatar_url', mode='before')
    @classmethod
    def validate_avatar_url(cls, v):
        if v is None:
            return "https://example.com/default-avatar.jpg"  # placeholder for future real example of avatar
        return v

class UserProfileEdit(BaseModel):
    username: Optional[Annotated[str, StringConstraints(
        min_length=USERNAME_MIN_LENGTH, 
        max_length=USERNAME_MAX_LENGTH, 
        pattern=USERNAME_PATTERN)]] = None
    bio: Optional[Annotated[str, StringConstraints(max_length=500)]] = None    

    @field_validator("username")
    @classmethod
    def validate_profile_username(cls, value: str) -> str:
        if value is None:
            return None
        return validate_username(value)
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_doe",                
                "bio": "Python developer and photographer"               
            }
        }

class EmailSchemaUpdate(BaseModel):
    new_email: EmailStr

class UserEmail(BaseModel):
    user_email: EmailStr

class ChangePasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)

    @field_validator('new_password')
    def validate_new_password(cls, value):
        return validate_password(value)
    
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
    text: Annotated[str, StringConstraints(min_length=1, max_length=500)]


class CommentUpdate(BaseModel):
    text: Annotated[str, StringConstraints(min_length=1, max_length=500)]


class CommentResponse(BaseModel):
    id: int
    text: str
    created_at: datetime
    updated_at: datetime
    user_id: int
    image_id: int

    model_config = ConfigDict(
        from_attributes= True
    )

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
    average_rating: Optional[float] = 0.0
    #created_at: datetime
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    model_config = ConfigDict(
        from_attributes=True
    )

class ImageResponseUpdateSchema(BaseModel):
    id: int
    description: str
    file_url: str = Field(..., alias="image_url") 
    owner_id: int = Field(..., alias="user_id")

    model_config = ConfigDict(
        from_attributes= True
    )

class TransformationParameters(BaseModel):
    crop: bool = False
    blur: bool = False
    circular: bool = False
    grayscale: bool = False
    transformation_params: dict = {}
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "crop": True,
                "blur": False,
                "circular": True,
                "grayscale": False,
                "transformation_params": {}
            }
        }
    )
   
class TransformationURLSchema(BaseModel):
    transformed_url: str
    public_id: str
    original_image_id: int

class TransformationResponseSchema(BaseModel):
    transformation_url: TransformationURLSchema
    qr_code_url: str
    image_id: int

    model_config = ConfigDict(
        from_attributes= True
    )

class RatingCreate(BaseModel):
    value: float = Field(ge=1, le=5, description="Rating value between 1 and 5")
    image_id: int

class RatingResponse(BaseModel):
    id: int
    value: float
    created_at: datetime
    user_id: int
    image_id: int

    model_config = ConfigDict(
        from_attributes=True
    )

class UserProfileWithLogout(UserProfileFull):    
    require_logout: bool = False
    message: Optional[str] = None

class RequestEmail(BaseModel):
    email: EmailStr
