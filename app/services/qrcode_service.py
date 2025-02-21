import qrcode
from PIL import Image as Im
import io
import base64

class QRCodeGeneration:
    """
    Service for generating images like QR code
    """

    def __init__(self, url:str):
        if not url:
            raise ValueError('URL cannot be emply')
        self.url = url
    
    def generate(self) -> Im.Image:
        """
        generates a QR code from a URl and return it as base64-ecoded
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

        if isinstance(img, Im.Image):
            return img
        else:
            raise TypeError(
                'Generared QR code is not a PIL Image'
            )

class ImageSaver:
    """
    Service for savig images in different formats.
    """
    @staticmethod
    def save_to_bytes(
        image:Im.Image,
        format:str='PNG'
    ) -> bytes:
        """
        Save the image to a byte stream in the specifies format.
        """
        img_io = io.BytesIO()
        image.save(img_io, format=format)
        img_io.seek(0)
        return img_io.getvalue()

class ImageGenerator:
    """
    Hoght-level service that user other services to generate and encode a QR
    """
    def __init__(self, url:str):
        self.qr_generator = QRCodeGeneration(url)
        self.image_saver = ImageSaver()
        self.image_encode = ImageEncoder()
    
    def generate_qr_code(self) -> str:
        """
        Generate a qr from a URL and returns it as a base64-ecoded string.
        """
        qr_image = self.qr_generator.generate()
        image_bytes = self.image_saver.save_to_bytes(qr_image)
        return self.image_encode.encode(image_bytes)

class ImageEncoder:
    """
    Service to encoding images to base64
    """
    @staticmethod
    def encode(image_bytes:bytes)->str:
        """
        Encodes the image stream to a base64 string.
        """
        return f"data:image/png;base64,{base64.b64encode(image_bytes).decode('utf-8')}"
    
    @staticmethod
    def generate_qr_code(url:str):
        
        
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        pil_img = Im.open(io.BytesIO(img.get_image().tobytes()))

        qr_io = io.BytesIO()
        pil_img.save(qr_io, format="PNG")
        qr_io.seek(0)

        qrcode_url = f"data:image/png;base64,{base64.b64encode(qr_io.getvalue()).decode('utf-8')}"
        return qrcode_url