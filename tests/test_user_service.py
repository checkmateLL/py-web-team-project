import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException, UploadFile
from io import BytesIO
from starlette.datastructures import Headers

from app.services.user_service import UserService
from app.services.image_service import CloudinaryService
from app.database.models import User


@pytest.fixture
def mock_upload_file():
    content = b"fake image content"
    return UploadFile(
        filename="test.jpg",
        file=BytesIO(content),
        headers=Headers({
            "content-disposition": 'form-data; name="file"; filename="test.jpg"',
            "content-type": "image/jpeg",
        }),
    )


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_cloudinary():
    cloud = AsyncMock(spec=CloudinaryService)
    cloud.upload_avatar = AsyncMock(return_value={
        "secure_url": "https://res.cloudinary.com/test/avatar.jpg",
        "public_id": "avatar_id",
    })
    cloud.delete_avatar = AsyncMock()
    return cloud


@pytest.mark.asyncio
async def test_validate_avatar_file(mock_upload_file):
    # Given
    service = UserService(AsyncMock(), AsyncMock())
    
    # When
    with patch('magic.Magic.from_buffer', return_value="image/jpeg"):
        await service.validate_avatar_file(mock_upload_file)
    
    # Then no exception should be raised


@pytest.mark.asyncio
async def test_validate_avatar_file_invalid_type(mock_upload_file):
    # Given
    service = UserService(AsyncMock(), AsyncMock())
    
    # When/Then
    with patch('magic.Magic.from_buffer', return_value="text/plain"):
        with pytest.raises(HTTPException) as exc_info:
            await service.validate_avatar_file(mock_upload_file)

        assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_validate_avatar_file_too_large():
    # Given
    from app.repository.images import crud_images

    # Create file bigger than 5MB
    mock_file = AsyncMock()
    mock_file.read = AsyncMock(return_value=b"x" * (5 * 1024 * 1024 + 1))
    mock_file.seek = AsyncMock()
    
    # When/Then
    with pytest.raises(HTTPException) as exc_info:
        await crud_images._check_size_file(mock_file)
    
    # Check for the exception
    assert exc_info.value.status_code == 400
    assert "File too large" in exc_info.value.detail


@pytest.mark.asyncio
async def test_update_avatar(mock_db_session, mock_cloudinary, mock_upload_file):
    # Given
    service = UserService(mock_db_session, mock_cloudinary)
    user = MagicMock(spec=User)
    user.id = 1
    user.avatar_url = None
    
    with patch('app.repository.users.crud_users.get_user_by_id', 
               AsyncMock(return_value=user)):
        # When
        with patch('magic.Magic.from_buffer', return_value="image/jpeg"):
            result = await service.update_avatar(1, mock_upload_file)
        
        # Then
        assert result == {"avatar_url": "https://res.cloudinary.com/test/avatar.jpg"}
        mock_cloudinary.upload_avatar.assert_called_once()
        mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_avatar_with_existing_avatar(mock_db_session, mock_cloudinary, mock_upload_file):
    # Given
    service = UserService(mock_db_session, mock_cloudinary)
    user = MagicMock(spec=User)
    user.id = 1
    user.avatar_url = "https://res.cloudinary.com/test/old_avatar.jpg"
    
    with patch('app.repository.users.crud_users.get_user_by_id', 
               AsyncMock(return_value=user)):
        # When
        with patch('magic.Magic.from_buffer', return_value="image/jpeg"):
            result = await service.update_avatar(1, mock_upload_file)
        
        # Then
        assert result == {"avatar_url": "https://res.cloudinary.com/test/avatar.jpg"}
        mock_cloudinary.delete_avatar.assert_called_once()
        mock_cloudinary.upload_avatar.assert_called_once()
        mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_avatar_user_not_found(mock_db_session, mock_cloudinary, mock_upload_file):
    # Given
    service = UserService(mock_db_session, mock_cloudinary)
    
    with patch('app.repository.users.crud_users.get_user_by_id', 
               AsyncMock(return_value=None)):
        # When/Then
        with patch('magic.Magic.from_buffer', return_value="image/jpeg"):
            with pytest.raises(HTTPException) as exc_info:
                await service.update_avatar(999, mock_upload_file)
            assert "User not found" in exc_info.value.detail
            assert "User not found" in exc_info.value.detail