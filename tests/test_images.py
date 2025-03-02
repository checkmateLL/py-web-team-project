from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
import pytest
from starlette.datastructures import Headers
from fastapi import UploadFile

from app.main import app
from app.services.image_service import CloudinaryService


@pytest.fixture
def mock_cloudinary_service():
    mock = MagicMock(spec=CloudinaryService)
    mock.upload_image = AsyncMock(
        return_value={
            "secure_url": "http://example.com/test.jpg",
            "public_id": "test.jpg",
        }
    )
    return mock


@pytest.mark.asyncio
async def test_upload_images(
    client: TestClient, db_session, mock_cloudinary_service: MagicMock
):
    # Override the CloudinaryService dependency
    app.dependency_overrides[
        CloudinaryService] = lambda: mock_cloudinary_service

    # Define test data
    description = "Test image"
    tags = ["test", "image"]
    file_content = b"fake image content"
    file = UploadFile(
        filename="test.jpg",
        file=BytesIO(file_content),
        headers=Headers(
            {
                "content-disposition": (
                    'form-data; name="file"; filename="test.jpg"'
                ),
                "content-type": "image/jpeg",
            }
        ),
    )
    file.size = len(file_content)
    user_email = "deadpool@example.com"
    user_password = "New123"
    login_data = {"username": user_email, "password": user_password}

    # Login to get access token
    response_login = client.post("/app/auth/login", data=login_data)
    assert response_login.status_code == 200
    access_token = response_login.json()["access_token"]

    # Mock the upload_image method to return a known result
    mock_cloudinary_service.upload_image.return_value = {
        "secure_url": "http://example.com/test.jpg",
        "public_id": "test.jpg",
    }

    # Upload the image
    response = client.post(
        "/app/img/upload_image",
        params={"tags": tags},
        data={"description": description},
        files={"file": (file.filename, file_content, "image/jpeg")},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    # Check if the response is successful
    assert (
        response.status_code == 200
    )

    # Check if the upload_image method was called
    assert mock_cloudinary_service.upload_image.call_count == 1

    # Additional checks for the response data
    response_data = response.json()
    assert response_data["id"] is not None
    assert response_data["description"] == description
    assert response_data["image_url"] == "http://example.com/test.jpg"
    assert response_data["user_id"] is not None
    assert response_data["created_at"] is not None
    assert response_data["tags"] == tags


@pytest.mark.asyncio
async def test_upload_images_fail_tags(
        client, db_session, mock_cloudinary_service):
    app.dependency_overrides[
        CloudinaryService] = lambda: mock_cloudinary_service

    description = "Test image"
    tags = ["test", "image", "fail", "tags", "foo", "baz", "bar"]

    file_content = b"fake image content"
    file = UploadFile(
        filename="test.jpg",
        file=BytesIO(file_content),
        headers=Headers(
            {
                "content-disposition": (
                    'form-data; name="file"; filename="test.jpg"'
                ),
                "content-type": "image/jpeg",
            }
        ),
    )
    file.size = len(file_content)

    user_email = "deadpool@example.com"
    user_password = "New123"

    login_data = {"username": user_email, "password": user_password}

    response_login = client.post("/app/auth/login", data=login_data)
    assert response_login.status_code == 200
    access_token = response_login.json()["access_token"]

    response = client.post(
        "/app/img/upload_image",
        params={"tags": tags},
        data={"description": description},
        files={"file": (file.filename, file_content, "image/jpeg")},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert mock_cloudinary_service.upload_image.call_count == 0

    assert response.status_code == 400
    assert response.json()["detail"] == "You can only add up to 5 tags."


@pytest.mark.asyncio
async def test_upload_images_fail_file_content(
    client, db_session, mock_cloudinary_service
):
    app.dependency_overrides[
        CloudinaryService] = lambda: mock_cloudinary_service

    description = "Test image"
    tags = ["test", "image", "fail"]
    file_content = b"fake image content"
    file = UploadFile(
        filename="test.txt",
        file=BytesIO(file_content),
        headers=Headers(
            {
                "content-disposition": (
                    'form-data; name="file"; filename="test.txt"'
                ),
                "content-type": "text/txt",
            }
        ),
    )
    file.size = len(file_content)

    user_email = "deadpool@example.com"
    user_password = "New123"

    login_data = {"username": user_email, "password": user_password}

    response_login = client.post("/app/auth/login", data=login_data)
    assert response_login.status_code == 200
    access_token = response_login.json()["access_token"]

    response = client.post(
        "/app/img/upload_image",
        params={"tags": tags},
        data={"description": description},
        files={"file": (file.filename, file_content, "text/txt")},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert mock_cloudinary_service.upload_image.call_count == 0

    assert response.status_code == 400
    assert response.json()[
        "detail"] == "Invalid file type. Only JPG, PNG and GIF"


@pytest.mark.asyncio
async def test_delete_image(client, db_session):

    user_email = "deadpool@example.com"
    user_password = "New123"

    login_data = {"username": user_email, "password": user_password}

    response_login = client.post("/app/auth/login", data=login_data)
    assert response_login.status_code == 200
    access_token = response_login.json()["access_token"]

    with patch("cloudinary.uploader.destroy") as mock_destroy:
        mock_destroy.return_value = {"result": "ok"}

        response = client.delete(
            f"/app/img/delete_image/{1}/",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 204
