import cloudinary  # type: ignore
import cloudinary.uploader  # type: ignore
import cloudinary.api
import cloudinary.exceptions
import cloudinary.utils
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
            api_secret=settings.CLD_API_SECRET,
        )

    def generate_transformation_string(
        self, 
        crop=False, 
        blur=False, 
        circular=False, 
        grayscale=False
    ) -> dict:
        """
        Generate a transformation dictionary for Cloudinary.
        
        Args:
            crop (bool): Apply 200x200 crop
            blur (bool): Apply blur effect
            circular (bool): Make image circular
            grayscale (bool): Convert to grayscale
            
        Returns:
            dict: Combined transformation parameters
        """
        transformations = {}
        if crop:
            transformations.update({"width": 200, "height": 200, "crop": "crop"})
        if blur:
            transformations.update({"effect": "blur:800"})
        if circular:
            transformations.update({"radius": "max"})
        if grayscale:
            transformations.update({"effect": "grayscale"})
        return transformations

    async def upload_image(
        self, 
        file: UploadFile, 
        folder: str
    ) -> dict:
        """
        Upload image to Cloudinary.

        Args:
            file (UploadFile): Image file to upload.
            folder (str): Folder in Cloudinary where the image will be uploaded.
        
        Returns:
            dict: Contains:
                - secure_url: URL of the uploaded image
                - public_id: Cloudinary public ID of the image

        Raises:
            HTTPException: If upload to Cloudinary fails.
                Status Code: 500 Internal Server Error.
                Detail includes specific error message from Cloudinary.
        """
        try:
            result = cloudinary.uploader.upload(file.file, folder=folder)
            return {
                "secure_url": result.get("secure_url"),
                "public_id": result.get("public_id"),
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error uploading file to Cloudinary: {str(e)}"
            )

    async def transform_image(
        self, 
        image: Image,
        transformation_params: dict | None = None,
        crop: bool = False,
        blur: bool = False,
        circular: bool = False,
        grayscale: bool = False
    ) -> dict:
        """
        Transforms an image using Cloudinary.

        Args:
            image (Image): Image model instance containing the public_id
            transformation_params (dict, optional): Custom transformation parameters
            crop (bool): Apply 200x200 crop
            blur (bool): Apply blur effect
            circular (bool): Make image circular
            grayscale (bool): Convert to grayscale

        Returns:
            dict: Contains:
                - transformed_url: URL of the transformed image
                - public_id: Cloudinary public ID
                - original_image_id: Database ID of original image

        Raises:
            HTTPException: If transformation fails or Cloudinary returns an error
        """
        try:
            # If no custom params provided, generate from boolean flags
            if transformation_params is None:
                transformation_params = self.generate_transformation_string(
                    crop=crop,
                    blur=blur,
                    circular=circular,
                    grayscale=grayscale
                )

            transformed_image = cloudinary.uploader.explicit(
                image.public_id,
                type="upload",
                eager=[transformation_params]
            )
            eager_transformations = transformed_image.get("eager", [])
            transformed_url = eager_transformations[0].get("secure_url") if eager_transformations else None
            
            if not transformed_url:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Cloudinary did not return a transformed image"
                )

            return {
                "transformed_url": transformed_url,
                "public_id": transformed_image.get("public_id"),
                "original_image_id": image.id
            }
        
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Cloudinary transformation error: {str(e)}"
            )