import cloudinary  # type: ignore
import cloudinary.uploader  # type: ignore
import cloudinary.api
import cloudinary.exceptions
import cloudinary.utils
from fastapi import HTTPException, UploadFile, status

from app.config import settings


class CloudinaryService:
    """
    Service for work with Cloudinary
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
    ):
        transformations = []
        if crop:
            transformations.append({"width": 200, "height": 200, "crop": "crop"})
        if blur:
            transformations.append({"effect": "blur:800"})
        if circular:
            transformations.append({"radius": "max"})
        if grayscale:
            transformations.append({"effect": "grayscale"})
        return transformations   
 
    def generate_transformed_url(
            self, 
            public_id, 
            transformations
    ):
        """
        Generate a URL for an image with transformations.

        Args:
            public_id (str): The public ID of the image.
            transformations (list): List of transformation dictionaries.

        Returns:
            str: The URL of the transformed image.
        """
        try:
            # ГGenerate a URL for an image with transformations
            url, _ = cloudinary.utils.cloudinary_url(
                public_id,
                transformation=transformations
            )
            folder = "/".join(public_id.split("/")[:-1])  # get folder from id
            if not folder:
                folder = None  # If folder is not return None

            # put transformed image in the same folder
            transformed_image = cloudinary.uploader.upload(
                url,  
                public_id=public_id,  
                folder=folder  
            )

        # return url of the transformed image
            return transformed_image.get("secure_url")
        
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Error generating URL: {str(e)}"
            )   

    async def upload_image(self, file: UploadFile, folder: str) -> dict:
        """
        Upload image to Cloudinary

        Args:
                file (UploadFile): ImageFile, with nead upload.
                folder (str): Folder in Cloudinary, with well be upload image.
        
        Returns:
            dict: consistense URL uploaded image & publicID

        Raises:
            HTTPException: If hapen upload error file in Cloudinary.
                StatusCode: 500 Internal Server Error.
                Detail error have message about current error by Cloudinary.
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
                detail="Error uploading file to Cloudinary: " + str(e),
            )
        

