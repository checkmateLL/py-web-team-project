import cloudinary  # type: ignore
import cloudinary.uploader  # type: ignore
from fastapi import HTTPException, UploadFile, status

from app.config import settings
from app.database.models import Image
from app.schemas import TransformationResponseSchema

class CloudinaryService:
    """
    Service for working with Cloudinary
    """
    def __init__(self):
        cloudinary.config(
            cloud_name=settings.CLD_NAME,
            api_key=settings.CLD_API_KEY,
            api_secret=settings.CLD_API_SECRET
        )

    async def upload_image(
        self, file: UploadFile, folder: str
    ) -> dict:
        """
        Uploads an image to Cloudinary.
        """
        try:
            result = cloudinary.uploader.upload(
                file.file,
                folder=folder
            )
            return {
                "secure_url": result.get("secure_url"),
                "public_id": result.get("public_id")
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error uploading file to Cloudinary: " + str(e)
            )

    async def transform_image(
        self, 
        image:Image,
        transformation_params : dict
    ):
        """
        Transforms an image using Cloudinary, generates a QR code, 
        and saves the transformation to the database.
        """
        try:
            transformed_image = cloudinary.uploader.explicit(
                image.public_id,
                type="upload",
                eager=[transformation_params]
            )
            eager_transformations = transformed_image.get("eager", [])
            transformed_url = eager_transformations[0].get("secure_url") if eager_transformations else None
            
            if not transformed_url:
                raise HTTPException(
                    status_code=500, 
                    detail="Cloudinary did not return a transformed image"
                )
            return {
                "transformed_url": transformed_url,
                "public_id": transformed_image.get("public_id"),
                "original_image_id": image.id
            }
        
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Cloudinary transformation error: {str(e)}"
            )
