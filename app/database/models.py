from sqlalchemy import (
    Table, 
    Column, 
    Integer, 
    String, 
    Boolean, 
    DateTime, 
    ForeignKey, 
    func, 
    Enum,
    Float
)
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase
from app.config import RoleSet
from datetime import datetime

class BaseModel(DeclarativeBase): ...


image_tag_association = Table('image_tag', BaseModel.metadata,
    Column('image_id', Integer, ForeignKey('images.id')),
    Column('tag_id', Integer, ForeignKey('tags.id'))
)

class User(BaseModel):
    __tablename__ = 'users'
    id : Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=False, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash : Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[RoleSet] = mapped_column(Enum(RoleSet), default=RoleSet.user, nullable=False)
    is_active : Mapped[bool] = mapped_column(Boolean, default=True)
    register_on : Mapped[datetime] = mapped_column(DateTime, default=func.now())
    bio: Mapped[str] = mapped_column(String(500), nullable=True)
    avatar_url: Mapped[str] = mapped_column(String, nullable=True)

    images : Mapped[list['Image']] = relationship('Image', back_populates='user', lazy='selectin')
    comments : Mapped[list['Comment']] = relationship('Comment', back_populates='user', lazy='selectin')

class Image(BaseModel):
    __tablename__ = 'images'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    description: Mapped[str] = mapped_column(String)
    image_url: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'))
    public_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    user: Mapped['User'] = relationship('User', back_populates='images', lazy='selectin')
    tags: Mapped[list['Tag']] = relationship('Tag', secondary=image_tag_association, back_populates='images', lazy='selectin')
    comments: Mapped[list['Comment']] = relationship('Comment', back_populates='image', lazy='selectin')
    transformations: Mapped[list['Transformation']] = relationship('Transformation', back_populates='image',lazy='selectin')

class Tag(BaseModel):
    __tablename__ = 'tags'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    images: Mapped[list['Image']] = relationship('Image', secondary=image_tag_association, back_populates='tags', lazy='selectin')

class Comment(BaseModel):
    __tablename__ = 'comments'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'))
    image_id: Mapped[int] = mapped_column(Integer, ForeignKey('images.id'))

    user: Mapped['User'] = relationship('User', back_populates='comments', lazy='selectin')
    image: Mapped['Image'] = relationship('Image', back_populates='comments', lazy='selectin')

class Transformation(BaseModel):
    __tablename__ = 'transformations'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transformation_url: Mapped[str] = mapped_column(String, nullable=False)
    qr_code_url: Mapped[str] = mapped_column(String, nullable=False)
    image_id: Mapped[int] = mapped_column(Integer, ForeignKey('images.id'))

    image: Mapped['Image'] = relationship('Image', back_populates='transformations', lazy='selectin')

class Rating(BaseModel):
    __tablename__ = 'ratings'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'))
    image_id: Mapped[int] = mapped_column(Integer, ForeignKey('images.id'))

    user: Mapped['User'] = relationship('User', back_populates='ratings', lazy='selectin')
    image: Mapped['Image'] = relationship('Image', back_populates='ratings', lazy='selectin')

User.ratings = relationship('Rating', back_populates='user', lazy='selectin')
Image.ratings = relationship('Rating', back_populates='image', lazy='selectin')