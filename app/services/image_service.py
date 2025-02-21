import cloudinary  # type: ignore
import cloudinary.uploader  # type: ignore
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
            api_secret=settings.CLD_API_SECRET
        )

    async def upload_image(
            self,
            file: UploadFile,
            folder: str
    ) -> dict:
        """
        Upload image to Cloudinary

        Args:
                file (UploadFile): ImageFile, with nead upload.
                folder (str): Folder in Cloudinary, with well be upload image.

        Returns:
            dict: consistense URL uploaded image & publicID.
                Excemple returned value:
                {
                    "secure_url": "https://res.cloudinary.com/.../image.jpg",
                    "public_id": "folder/image"
                }

        Raises:
            HTTPException: If hapen upload error file in Cloudinary.
                StatusCode: 500 Internal Server Error.
                Detail error have message about current error by Cloudinary.
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
                public_id: str,
                transformations: str
        ) -> dict:
            """
            Transform an image in Cloudinary based on the public ID with specific transformations.

            Args:
                    public_id (str): The Cloudinary public ID of the image to be transformed.
                    transformations (str): The transformation string to apply.

            Returns:
                dict: Contains the transformed image URL and public ID.
                    
            Raises:
                HTTPException: If there's an error applying transformations.
            """
            try:
                # Generate the URL with transformations
                url = cloudinary.CloudinaryImage(public_id).build_url(transformation=transformations)

                return {
                    "secure_url": url,
                    "public_id": public_id
                }
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error transforming image in Cloudinary: " + str(e)
                )

    @staticmethod
    def generate_transformation_string(
                crop: bool = False,
                blur: bool = False,
                circular: bool = False,
                grayscale: bool = False
        ) -> str:
            """
            Generate transformation string for Cloudinary based on requested options.

            Args:
                crop (bool): Apply crop transformation.
                blur (bool): Apply blur effect.
                round (bool): Make image round (circular crop).
                grayscale(bool): Apply a grayscale.

            Returns:
                str: Transformation string to use in Cloudinary upload.
            """
            transformations = []

            if crop:
                transformations.append("crop")
            if blur:
                transformations.append("blur:500")  # Set blur level (0-1000)
            if circular:
                transformations.append("radius_max")
            if grayscale:
                transformations.append("effect:grayscale")  # Example: could be other effects

            return ",".join(transformations)    
            
