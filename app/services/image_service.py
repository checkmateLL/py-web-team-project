import cloudinary  # type: ignore
import cloudinary.uploader  # type: ignore
from fastapi import HTTPException, UploadFile, status
import qrcode
import io
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.config import settings, RoleSet
from app.database.models import Image, Transformation
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
        self, image_id: int, transformation_params: dict, db: AsyncSession, current_user
    ) -> TransformationResponseSchema:
        """
        Transforms an image using Cloudinary, generates a QR code, and saves the transformation to the database.
        """
        result = await db.execute(select(Image).filter(Image.id == image_id))
        image = result.scalar_one_or_none()

        if not image:
            raise HTTPException(status_code=404, detail="Image not found.")

        if image.user_id != current_user.id and current_user.role != RoleSet.admin:
            raise HTTPException(status_code=403, detail="You don't have permission to transform this image.")

        try:
            transformed_image = cloudinary.uploader.explicit(
                image.public_id,  #використовую public_id
                type="upload",
                eager=[transformation_params]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Cloudinary transformation error: {str(e)}")

        transformed_url = transformed_image["eager"][0]["secure_url"]

        qr = qrcode.make(transformed_url)
        qr_io = io.BytesIO()
        qr.save(qr_io, format="PNG")
        qr_code_url = f"data:image/png;base64,{qr_io.getvalue().hex()}"

        new_transformation = Transformation(
            transformation_url=transformed_url,
            qr_code_url=qr_code_url,
            image_id=image_id
        )
        db.add(new_transformation)
        await db.commit()
        await db.refresh(new_transformation)

        return TransformationResponseSchema(
            transformation_url=transformed_url,
            qr_code_url=qr_code_url,
            image_id=image_id
        )
