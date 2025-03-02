import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Image, Tag, User
from app.repository.images import crud_images


@pytest.fixture
def mock_session():
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def mock_image():
    image = MagicMock(spec=Image)
    image.id = 1
    image.description = "Test Image"
    image.image_url = "https://example.com/test.jpg"
    image.user_id = 1
    image.public_id = "test_public_id"
    image.tags = []
    return image


@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = 1
    user.username = "testuser"
    user.email = "test@example.com"
    return user


@pytest.mark.asyncio
async def test_check_permission():
    # Given
    image = MagicMock()
    image.user_id = 1
    
    # When/Then
    # Should not raise exception when user is the owner
    crud_images.check_permission(image, 1)
    
    # Should raise exception when user is not the owner
    with pytest.raises(HTTPException) as exc_info:
        crud_images.check_permission(image, 2)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_check_tags_count():
    # When/Then
    # Should not raise exception when tags count <= 5
    await crud_images._check_tags_count(["tag1", "tag2", "tag3", "tag4", "tag5"])
    
    # Should raise exception when tags count > 5
    with pytest.raises(HTTPException) as exc_info:
        await crud_images._check_tags_count(["tag1", "tag2", "tag3", "tag4", "tag5", "tag6"])
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_check_allowed_types():
    # Given
    file = MagicMock(spec=UploadFile)
    
    # When/Then
    # Should not raise exception for allowed types
    for content_type in ["image/jpeg", "image/png", "image/gif"]:
        file.content_type = content_type
        await crud_images._check_allowed_types(file)
    
    # Should raise exception for disallowed types
    file.content_type = "text/plain"
    with pytest.raises(HTTPException) as exc_info:
        await crud_images._check_allowed_types(file)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_get_data_cloudinary():
    # Given
    upload_result = {
        "secure_url": "https://example.com/test.jpg",
        "public_id": "test_public_id"
    }
    
    # When
    secure_url, public_id = await crud_images.get_data_cloudinary(upload_result)
    
    # Then
    assert secure_url == "https://example.com/test.jpg"
    assert public_id == "test_public_id"


@pytest.mark.asyncio
async def test_get_data_cloudinary_missing_data():
    # Given
    upload_result = {"other_key": "value"}
    
    # When/Then
    with pytest.raises(HTTPException) as exc_info:
        await crud_images.get_data_cloudinary(upload_result)
    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_check_size_file():
    # Given
    file = AsyncMock(spec=UploadFile)
    file.read = AsyncMock(return_value=b"small file")
    file.seek = AsyncMock()
    
    # When
    await crud_images._check_size_file(file)
    
    # Then
    file.read.assert_called_once()
    file.seek.assert_called_once_with(0)


@pytest.mark.asyncio
async def test_check_size_file_too_large():
    # Given
    file = AsyncMock(spec=UploadFile)
    # Create a file larger than 5MB
    file.read = AsyncMock(return_value=b"x" * (5 * 1024 * 1024 + 1))
    file.seek = AsyncMock()
    
    # When/Then
    with pytest.raises(HTTPException) as exc_info:
        await crud_images._check_size_file(file)
    assert exc_info.value.status_code == 400
    assert "File too large" in exc_info.value.detail


@pytest.mark.asyncio
async def test_create_image(mock_session, mock_user):
    # Given
    url = "https://example.com/test.jpg"
    description = "Test Image"
    public_id = "test_public_id"
    
    # When
    result = await crud_images.create_image(
        url=url,
        description=description,
        user_id=mock_user.id,
        public_id=public_id,
        session=mock_session
    )
    
    # Then
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()
    mock_session.refresh.assert_called_once()
    assert result.image_url == url
    assert result.description == description
    assert result.user_id == mock_user.id
    assert result.public_id == public_id


@pytest.mark.asyncio
async def test_handle_tags(mock_session):
    # Given
    tags_names = ["tag1", "tag2", "tag3"]
    
    mock_tags = []
    for name in tags_names:
        tag = MagicMock()
        tag.name = name
        mock_tags.append(tag)

    # Setup mock for _get_all_tags
    existing_tags = {tag.name: tag for tag in mock_tags}
    with patch.object(crud_images, '_get_all_tags', 
                     AsyncMock(return_value=existing_tags)):
        # Setup mock for _select_uniqal
        with patch.object(crud_images, '_select_uniqal', 
                         AsyncMock(return_value=set(tags_names))):
            # Setup mock for _create_new_tag
            mock_tags = [MagicMock(spec=Tag, name=name) for name in tags_names]
            with patch.object(crud_images, '_create_new_tag', 
                             AsyncMock(return_value=mock_tags)):
                # When
                result = await crud_images.handle_tags(tags_names, mock_session)
                
                # Then
                assert len(result) == len(tags_names)
                for tag in result:
                    assert tag.name in tags_names