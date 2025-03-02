import pytest
from unittest.mock import patch
from PIL import Image as PILImage
import io
import base64

from app.services.qrcode_service import (
    QRCodeGeneration, 
    ImageSaver, 
    ImageEncoder, 
    ImageGenerator
)


@pytest.fixture
def sample_qr_code():    
    img = PILImage.new('RGB', (50, 50), color='white')
    return img


def test_qrcode_generation():
    # Given
    url = "https://example.com/test"
    
    # When
    with patch('qrcode.QRCode.make_image', return_value=PILImage.new('RGB', (50, 50))):
        generator = QRCodeGeneration(url)
        result = generator.generate()
    
    # Then
    assert isinstance(result, PILImage.Image)


def test_qrcode_generation_empty_url():
    # When/Then
    with pytest.raises(ValueError):
        QRCodeGeneration("")


def test_image_saver(sample_qr_code):
    # When
    result = ImageSaver.save_to_bytes(sample_qr_code)
    
    # Then
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_image_encoder():
    # Given
    test_bytes = b"test image bytes"
    
    # When
    encoded = ImageEncoder.encode(test_bytes)
    
    # Then
    assert encoded.startswith("data:image/png;base64,")
    assert base64.b64decode(encoded.split(",")[1]) == test_bytes


def test_image_generator():
    # Given
    url = "https://example.com/test"
    generator = ImageGenerator()
    
    # When
    with patch('app.services.qrcode_service.QRCodeGeneration.generate', 
               return_value=PILImage.new('RGB', (50, 50))):
        result = generator.generate_qr_code(url)
    
    # Then
    assert isinstance(result, str)
    assert result.startswith("data:image/png;base64,")