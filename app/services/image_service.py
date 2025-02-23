import cloudinary  # type: ignore
import cloudinary.uploader  # type: ignore
import cloudinary.api # type: ignore
import cloudinary.exceptions # type: ignore
import cloudinary.utils # type: ignore
from fastapi import HTTPException, UploadFile, status
from abc import ABC, abstractmethod

from app.config import settings
from app.database.models import Image

class Transformation:
    """
    Base class for tarnsformation
    """
    def __init__(self, next_transformations=None):
        self.next_transformations = next_transformations
    
    def apply(self, transformations: dict, active: bool) -> dict:
        """
        Apply transormation if active and pass request to the next
        transformtaions in the chain.
        """
        if active:
            transformations.update(
                self._get_transformation_params()
            )
        if self.next_transformations:
            return self.next_transformations.apply(
                transformations, active
            )
        return transformations
    
    def _get_transformation_params(self) -> dict:
        """
        Returns transformation parameters. Must be implemented by subclasses.
        """
        raise NotImplementedError('Subclass must be implemented this method')

class CropTransformation(Transformation):
    def _get_transformation_params(self) -> dict:
        return {
            'width': 200,
            'height': 200,
            'crop': 'crop',
        }

class BlurTransformation(Transformation):
    def _get_transformation_params(self) -> dict:
        return {
            'effect': 'blur:800'
        }

class CircularTransformation(Transformation):
    def _get_transformation_params(self) -> dict:
        return {
            "radius": "max"
        }

class GrayscaleTransformation(Transformation):
    def _get_transformation_params(self) -> dict:
        return {
            "effect": "grayscale"
        }

class TransformationGenerator:
    """
    Class for generationg tranformation parameters for Cloudinry
    """
    def __init__(self):
        self.transformations_chain = GrayscaleTransformation(
            CircularTransformation(
                BlurTransformation(
                    CropTransformation()
                )
            )
        )
    
    def generate_transformation_string(
            self,
            crop: bool = False,
            blur: bool = False, 
            circular: bool = False, 
            grayscale: bool = False
    ) -> dict:
        """
        Generate a transformation dictionary for Cloudinary

        Args:
            crop (bool): Apply crop transformation
            blur (bool): Apply blur transformation
            circular (bool): Apply circular transformation
            grayscale (bool): Apply grayscale transformation
        
        Returns:
            dict: Combined transformation paramerers
        """
        transformations: dict = {}

        transformations = self.transformations_chain.apply({}, grayscale)
        transformations = self.transformations_chain.apply(transformations, circular)
        transformations = self.transformations_chain.apply(transformations, blur)
        transformations = self.transformations_chain.apply(transformations, crop)

        return transformations

class IcloudinaryService(ABC):

    @abstractmethod
    async def upload_image(self, file, folder) -> dict: ...

    @abstractmethod
    async def transform_image(
        self, 
        image: Image,
        transformation_params: dict | None = None,
        crop: bool = False,
        blur: bool = False,
        circular: bool = False,
        grayscale: bool = False
    ) -> dict: ...

class CloudinaryService(IcloudinaryService):
    """
    Service for working with Cloudinary
    """

    def __init__(self):
        cloudinary.config(
            cloud_name=settings.CLD_NAME,
            api_key=settings.CLD_API_KEY,
            api_secret=settings.CLD_API_SECRET,
        )
        self.transformation_generator = TransformationGenerator()


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
            if not transformation_params and not any([crop, blur, circular, grayscale]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Not transformations were applied."
                )
            
            if not transformation_params:
                transformation_params = self.transformation_generator.generate_transformation_string(
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
        
    async def upload_avatar(self, file: UploadFile) -> dict:
        """
        Upload avatar image to Cloudinary with optimization for avatars.
        
        Args:
            file (UploadFile): Image file to upload.
                    
        Returns:
            dict: Contains:
                - secure_url: URL of the uploaded image
                - public_id: Cloudinary public ID of the image
        """
        try:
            # Add transformation for avatars
            transformation = {
                'width': 400,
                'height': 400,
                'crop': 'fill',
                'gravity': 'face',
                'quality': 'auto',
                'format': 'webp'
            }
            
            result = cloudinary.uploader.upload(
                file.file,
                folder="avatars",
                transformation=transformation,
                resource_type="auto"
            )
            
            return {
                "secure_url": result.get("secure_url"),
                "public_id": result.get("public_id"),
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error uploading avatar to Cloudinary: {str(e)}"
            )

    async def delete_avatar(self, public_id: str):
        """
        Delete avatar from Cloudinary.
        
        Args:
            public_id (str): Cloudinary public ID of the avatar to delete.
        """
        try:
            await cloudinary.uploader.destroy(public_id, resource_type="image")
        except cloudinary.exceptions.Error as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting avatar from Cloudinary: {str(e)}"
            )