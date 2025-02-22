import qrcode
from PIL import Image as Im
import io
import base64

class QRCodeGeneration:
    """
    Service for generating images like QR code
    """

    def __init__(self, url: str):
        if not url:
            raise ValueError('URL cannot be empty')
        self.url = url
    
    def generate(self):
        """
        Generates a QR code from a URL and returns it as a PIL Image.
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(self.url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        return img

class ImageSaver:
    """
    Service for saving images in different formats.
    """
    @staticmethod
    def save_to_bytes(
        image: Im.Image,
        format: str = 'PNG'
    ) -> bytes:
        """
        Save the image to a byte stream in the specified format.
        """
        img_io = io.BytesIO()
        image.save(img_io, format=format)
        img_io.seek(0)
        return img_io.getvalue()

class ImageEncoder:
    """
    Service for encoding images to base64
    """
    @staticmethod
    def encode(image_bytes: bytes) -> str:
        """
        Encodes the image stream to a base64 string.
        """
        return f"data:image/png;base64,{base64.b64encode(image_bytes).decode('utf-8')}"

class ImageGenerator:
    """
    High-level service that uses other services to generate and encode a QR code.
    """
    def generate_qr_code(self, url) -> str:
        """
        Generate a QR from a URL and return it as a base64-encoded string.
        """
        qr_generator = QRCodeGeneration(url)
        qr_image = qr_generator.generate()
        image_bytes = ImageSaver.save_to_bytes(qr_image)
        image_encoder = ImageEncoder()
        
        return image_encoder.encode(image_bytes)

async def get_image_generator() ->ImageGenerator:
    return ImageGenerator()

