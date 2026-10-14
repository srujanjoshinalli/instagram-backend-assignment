import pytest
from unittest.mock import Mock

from src.services.image_service import ImageService


def test_upload_image_saves_to_s3_and_dynamodb():
    s3 = Mock()
    table = Mock()

    service = ImageService(
        s3_client=s3,
        dynamodb_table=table,
        bucket_name="test-bucket",
    )

    result = service.upload_image(
        owner_id="user123",
        filename="photo.jpg",
        content_type="image/jpeg",
        image_bytes=b"fake-image-bytes",
        caption="My photo",
    )

    assert result["owner_id"] == "user123"
    assert result["filename"] == "photo.jpg"
    assert result["caption"] == "My photo"
    assert result["size_bytes"] == len(b"fake-image-bytes")

    s3.put_object.assert_called_once()
    table.put_item.assert_called_once()


def create_service():
    s3 = Mock()
    table = Mock()
    service = ImageService(s3, table, "test-bucket")
    return service, s3, table


def test_upload_rejects_empty_image():
    service, s3, table = create_service()

    with pytest.raises(ValueError, match="Image cannot be empty"):
        service.upload_image(
            owner_id="user123",
            filename="photo.jpg",
            content_type="image/jpeg",
            image_bytes=b"",
        )

    s3.put_object.assert_not_called()
    table.put_item.assert_not_called()


def test_upload_rejects_non_image_content_type():
    service, s3, table = create_service()

    with pytest.raises(ValueError, match="Only image content types"):
        service.upload_image(
            owner_id="user123",
            filename="document.pdf",
            content_type="application/pdf",
            image_bytes=b"some-bytes",
        )

    s3.put_object.assert_not_called()
    table.put_item.assert_not_called()


def test_upload_cleans_up_s3_if_metadata_write_fails():
    service, s3, table = create_service()
    table.put_item.side_effect = RuntimeError("DynamoDB unavailable")

    with pytest.raises(RuntimeError, match="DynamoDB unavailable"):
        service.upload_image(
            owner_id="user123",
            filename="photo.jpg",
            content_type="image/jpeg",
            image_bytes=b"fake-image",
        )

    s3.put_object.assert_called_once()
    s3.delete_object.assert_called_once()



def test_list_images_by_owner():
    service, _, table = create_service()

    table.query.return_value = {
        "Items": [
            {"image_id": "img-1", "owner_id": "user123"}
        ]
    }

    result = service.list_images(owner_id="user123")

    assert len(result["items"]) == 1
    assert result["items"][0]["image_id"] == "img-1"
    assert result["next_token"] is None

    table.query.assert_called_once()
    assert table.query.call_args.kwargs["IndexName"] == (
        "OwnerCreatedAtIndex"
    )


def test_list_images_rejects_missing_filters():
    service, _, _ = create_service()

    with pytest.raises(ValueError, match="Provide owner_id"):
        service.list_images()


def test_list_images_rejects_invalid_limit():
    service, _, _ = create_service()

    with pytest.raises(ValueError, match="limit must be"):
        service.list_images(owner_id="user123", limit=0)


def test_list_images_returns_pagination_token():
    service, _, table = create_service()

    table.query.return_value = {
        "Items": [{"image_id": "img-1"}],
        "LastEvaluatedKey": {
            "image_id": "img-1",
            "owner_id": "user123",
            "created_at": "2026-10-14T10:00:00+00:00",
        },
    }

    result = service.list_images(owner_id="user123")

    assert result["next_token"] is not None
    assert isinstance(result["next_token"], str)


def test_get_image_metadata_success():
    service, _, table = create_service()
    table.get_item.return_value = {
        "Item": {"image_id": "img-1", "owner_id": "user123"}
    }

    result = service.get_image_metadata("img-1")

    assert result["image_id"] == "img-1"
    table.get_item.assert_called_once_with(
        Key={"image_id": "img-1"}
    )


def test_get_image_metadata_not_found():
    from src.services.image_service import ImageNotFoundError

    service, _, table = create_service()
    table.get_item.return_value = {}

    with pytest.raises(ImageNotFoundError):
        service.get_image_metadata("missing")


def test_download_image_success():
    service, s3, table = create_service()
    table.get_item.return_value = {
        "Item": {
            "image_id": "img-1",
            "s3_key": "images/user123/img-1",
            "content_type": "image/jpeg",
        }
    }

    body = Mock()
    body.read.return_value = b"fake-image-bytes"
    s3.get_object.return_value = {"Body": body}

    result = service.download_image("img-1")

    assert result["body"] == b"fake-image-bytes"
    assert result["content_type"] == "image/jpeg"
    s3.get_object.assert_called_once()


def test_delete_image_success():
    service, s3, table = create_service()
    table.get_item.return_value = {
        "Item": {
            "image_id": "img-1",
            "s3_key": "images/user123/img-1",
        }
    }

    service.delete_image("img-1")

    s3.delete_object.assert_called_once_with(
        Bucket="test-bucket",
        Key="images/user123/img-1",
    )
    table.delete_item.assert_called_once_with(
        Key={"image_id": "img-1"},
        ConditionExpression="attribute_exists(image_id)",
    )