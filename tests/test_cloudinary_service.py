import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers
from io import BytesIO

from app.services.image_service import CloudinaryService, TransformationGenerator
from app.database.models import Image


@pytest.fixture
def mock_image():
    image = MagicMock(spec=Image)
    image.public_id = "test_public_id"
    image.id = 1
    return image


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


@pytest.mark.asyncio
async def test_upload_image(mock_upload_file):
    # Given
    service = CloudinaryService()
    
    # When
    with patch('cloudinary.uploader.upload', return_value={
        'secure_url': 'https://res.cloudinary.com/test/image.jpg',
        'public_id': 'test_id',
    }):
        result = await service.upload_image(mock_upload_file, "test_folder")
    
    # Then
    assert result == {
        'secure_url': 'https://res.cloudinary.com/test/image.jpg',
        'public_id': 'test_id',
    }


@pytest.mark.asyncio
async def test_upload_image_error(mock_upload_file):
    # Given
    service = CloudinaryService()
    
    # When/Then
    with patch('cloudinary.uploader.upload', side_effect=Exception("Upload failed")):
        with pytest.raises(HTTPException) as exc_info:
            await service.upload_image(mock_upload_file, "test_folder")
        assert exc_info.value.status_code == 500
        assert "Error uploading file" in exc_info.value.detail


@pytest.mark.asyncio
async def test_transform_image(mock_image):
    # Given
    service = CloudinaryService()
    
    # When
    with patch('cloudinary.uploader.explicit', return_value={
        'public_id': 'test_id',
        'eager': [{'secure_url': 'https://res.cloudinary.com/test/transformed.jpg'}]
    }):
        result = await service.transform_image(
            mock_image, 
            crop=True, 
            blur=True, 
            circular=True,
            grayscale=True
        )
    
    # Then
    assert result['transformed_url'] == 'https://res.cloudinary.com/test/transformed.jpg'
    assert result['public_id'] == 'test_id'
    assert result['original_image_id'] == 1


@pytest.mark.asyncio
async def test_transform_image_error(mock_image):
    # Given
    service = CloudinaryService()
    
    # When/Then
    with patch('cloudinary.uploader.explicit', side_effect=Exception("Transform failed")):
        with pytest.raises(HTTPException) as exc_info:
            await service.transform_image(
                mock_image, 
                crop=True,
                blur=False,
                circular=False,
                grayscale=False
            )
        assert exc_info.value.status_code == 500
        assert "Cloudinary transformation error" in exc_info.value.detail


@pytest.mark.asyncio
async def test_upload_avatar(mock_upload_file):
    # Given
    service = CloudinaryService()
    
    # When
    with patch('cloudinary.uploader.upload', return_value={
        'secure_url': 'https://res.cloudinary.com/test/avatar.jpg',
        'public_id': 'avatar_id',
    }):
        result = await service.upload_avatar(mock_upload_file)
    
    # Then
    assert result == {
        'secure_url': 'https://res.cloudinary.com/test/avatar.jpg',
        'public_id': 'avatar_id',
    }


@pytest.mark.asyncio
async def test_delete_avatar():
    # Given
    import cloudinary
    service = CloudinaryService()
    
    # When
    with patch('cloudinary.uploader.destroy', return_value={"result": "ok"}) as mock_destroy:        
        async def async_mock(*args, **kwargs):
            return mock_destroy(*args, **kwargs)        
        
        with patch.object(
            cloudinary.uploader, 'destroy', 
            side_effect=async_mock
        ):            
            await service.delete_avatar("test_public_id")            
            
            mock_destroy.assert_called_once_with("test_public_id", resource_type="image")
    
def test_transformation_generator():
    # Given
    generator = TransformationGenerator()
    
    # When
    params = generator.generate_transformation_string(
        crop=True,
        blur=True,
        circular=True,
        grayscale=True
    )
    
    # Then
    assert 'crop' in params
    assert 'effect' in params
    assert 'radius' in params