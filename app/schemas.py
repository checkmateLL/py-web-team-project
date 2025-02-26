from pydantic import BaseModel, EmailStr, Field, constr, HttpUrl, ConfigDict, field_validator, StringConstraints, ValidationInfo, ConfigDict
from datetime import datetime
from typing import Optional, Annotated

class RegisterUser(BaseModel):
    user_name: str
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
    def validate_password(cls, value: str) -> str:
        if value and len(value) < 6:
            raise ValueError("Password must be at least 6 characters long")
        return value


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
    username: Optional[
        Annotated[
            str, 
            StringConstraints(
                min_length=3, 
                max_length=50, 
                pattern="^[a-zA-Z0-9_-]+$"
                )
            ]
        ] = None
    email: Optional[EmailStr] = None
    current_password: Optional[str] = None
    new_password: Optional[Annotated[str, StringConstraints(min_length=6)]] = None
    bio: Optional[Annotated[str, StringConstraints(max_length=500)]] = None    

    @field_validator('new_password')
    @classmethod
    def validate_password_change(cls, new_password: Optional[str], info: ValidationInfo) -> Optional[str]:
        """
        Ensure password change requires current password
        and meets minimum length requirements
        """     
        if new_password is not None:
            values = info.data
            if not values.get('current_password'):
                raise ValueError("Current password must be provided to change password")
                        
            if len(new_password) < 6:
                raise ValueError("New password must be at least 6 characters long")
        
        return new_password

    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "email": "john@example.com",
                "bio": "Python developer and photographer",
                "current_password": "old_password",
                "new_password": "new_password123"
            }
        }
        
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
