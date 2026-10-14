import os
import uuid

import boto3
import pytest

from src.services.image_service import ImageService


@pytest.fixture
def service():
    endpoint = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
    region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    bucket_name = os.getenv("IMAGE_BUCKET", "image-storage-local")
    table_name = os.getenv("IMAGE_TABLE", "Images")

    session = boto3.Session(
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
        region_name=region,
    )

    s3 = session.client("s3", endpoint_url=endpoint)
    dynamodb = session.resource("dynamodb", endpoint_url=endpoint)
    table = dynamodb.Table(table_name)

    return ImageService(
        s3_client=s3,
        dynamodb_table=table,
        bucket_name=bucket_name,
    )


@pytest.mark.integration
def test_upload_download_and_delete_image(service):
    owner_id = f"test-owner-{uuid.uuid4()}"
    image_bytes = b"fake-image-content"

    # Upload
    uploaded = service.upload_image(
        owner_id=owner_id,
        filename="test.png",
        content_type="image/png",
        image_bytes=image_bytes,
        caption="Integration test",
    )

    image_id = uploaded["image_id"]

    try:
        # Verify metadata was persisted
        metadata = service.get_image_metadata(image_id)
        assert metadata["owner_id"] == owner_id
        assert metadata["filename"] == "test.png"

        # Verify image bytes can be downloaded
        result = service.download_image(image_id)
        assert result["body"] == image_bytes
        assert result["content_type"] == "image/png"

    finally:
        # Delete the uploaded image and its metadata
        service.delete_image(image_id)

    with pytest.raises(Exception):
        service.get_image_metadata(image_id)