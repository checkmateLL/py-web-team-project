from sqlalchemy import (
    Table, 
    Column, 
    Integer, 
    String, 
    Boolean, 
    DateTime, 
    ForeignKey, 
    func, 
    Enum
)
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase
from app.config import RoleSet
from datetime import datetime

class BaseModel(DeclarativeBase): ...


#asscotiative table [Table-images<-->Table-tags]
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
    role: Mapped[RoleSet] = mapped_column(Enum(RoleSet), default=RoleSet.user, nullable=True)
    is_active : Mapped[bool] = mapped_column(Boolean, default=True)
    register_on : Mapped[datetime] = mapped_column(DateTime, default=func.now())

    images : Mapped[list['Image']] = relationship('Image', back_populates='user')
    comments : Mapped[list['Comment']] = relationship('Comment', back_populates='user')

class Image(BaseModel):
    __tablename__ = 'images'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    description: Mapped[str] = mapped_column(String)
    image_url: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'))

    user: Mapped['User'] = relationship('User', back_populates='images')
    tags: Mapped[list['Tag']] = relationship('Tag', secondary=image_tag_association, back_populates='images')
    comments: Mapped[list['Comment']] = relationship('Comment', back_populates='image')
    transformations: Mapped[list['Transformation']] = relationship('Transformation', back_populates='image')

class Tag(BaseModel):
    __tablename__ = 'tags'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    images: Mapped[list['Image']] = relationship('Image', secondary=image_tag_association, back_populates='tags')

class Comment(BaseModel):
    __tablename__ = 'comments'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'))
    image_id: Mapped[int] = mapped_column(Integer, ForeignKey('images.id'))

    user: Mapped['User'] = relationship('User', back_populates='comments')
    image: Mapped['Image'] = relationship('Image', back_populates='comments')

class Transformation(BaseModel):
    __tablename__ = 'transformations'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transformation_url: Mapped[str] = mapped_column(String, nullable=False)
    qr_code_url: Mapped[str] = mapped_column(String, nullable=False)
    image_id: Mapped[int] = mapped_column(Integer, ForeignKey('images.id'))

    image: Mapped['Image'] = relationship('Image', back_populates='transformations')