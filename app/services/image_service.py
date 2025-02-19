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
