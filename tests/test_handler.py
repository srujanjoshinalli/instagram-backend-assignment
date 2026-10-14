import base64
import json
from unittest.mock import patch

from src import handler


def test_upload_image_returns_201():
    image_bytes = b"fake-image-content"

    event = {
        "httpMethod": "POST",
        "path": "/images",
        "body": json.dumps({
            "owner_id": "user-123",
            "filename": "photo.png",
            "content_type": "image/png",
            "image_base64": base64.b64encode(image_bytes).decode("utf-8"),
            "caption": "My photo",
        }),
    }

    with patch.object(handler.service, "upload_image") as upload:
        upload.return_value = {"image_id": "img-123"}

        result = handler.lambda_handler(event, None)

    assert result["statusCode"] == 201
    assert json.loads(result["body"])["image_id"] == "img-123"

    upload.assert_called_once_with(
        owner_id="user-123",
        filename="photo.png",
        content_type="image/png",
        image_bytes=image_bytes,
        caption="My photo",
    )


def test_upload_image_rejects_invalid_base64():
    event = {
        "httpMethod": "POST",
        "path": "/images",
        "body": json.dumps({
            "owner_id": "user-123",
            "filename": "photo.png",
            "content_type": "image/png",
            "image_base64": "not-valid-base64!!!",
        }),
    }

    result = handler.lambda_handler(event, None)

    assert result["statusCode"] == 400
    assert "Base64" in json.loads(result["body"])["error"]


def test_upload_image_rejects_invalid_json():
    event = {
        "httpMethod": "POST",
        "path": "/images",
        "body": "{invalid json",
    }

    result = handler.lambda_handler(event, None)

    assert result["statusCode"] == 400