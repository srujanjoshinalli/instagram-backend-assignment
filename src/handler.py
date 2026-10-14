import base64
import binascii
import json
import logging
import os
from decimal import Decimal

from src.config import create_aws_resources
from src.services.image_service import (
    ImageService,
    ImageNotFoundError,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3, table = create_aws_resources()

service = ImageService(
    s3_client=s3,
    dynamodb_table=table,
    bucket_name=os.getenv("IMAGE_BUCKET", "image-storage-local"),
)


def json_serializer(value):
    if isinstance(value, Decimal):
        # Convert whole-number Decimal values to int,
        # and fractional values to float.
        if value % 1 == 0:
            return int(value)
        return float(value)

    raise TypeError(
        f"Object of type {type(value).__name__} is not JSON serializable"
    )


def response(status_code, body=None, headers=None, is_base64=False):
    result = {
        "statusCode": status_code,
        "headers": headers or {"Content-Type": "application/json"},
        "body": (
            body
            if isinstance(body, str)
            else json.dumps(body or {}, default=json_serializer)
        ),
    }

    if is_base64:
        result["isBase64Encoded"] = True

    return result


def lambda_handler(event, context):
    method = event.get("httpMethod", "")
    path = event.get("path", "")
    params = event.get("queryStringParameters") or {}
    path_params = event.get("pathParameters") or {}

    try:
        # POST /images - Upload an image
        if method == "POST" and path == "/images":
            raw_body = event.get("body")

            if not raw_body:
                return response(400, {"error": "Request body is required"})

            if event.get("isBase64Encoded", False):
                try:
                    raw_body = base64.b64decode(
                        raw_body, validate=True
                    ).decode("utf-8")
                except (binascii.Error, UnicodeDecodeError, ValueError):
                    return response(400, {"error": "Invalid request body encoding"})

            try:
                payload = json.loads(raw_body)
            except (json.JSONDecodeError, TypeError):
                return response(400, {"error": "Request body must be valid JSON"})

            if not isinstance(payload, dict):
                return response(400, {"error": "Request body must be a JSON object"})

            image_base64 = payload.get("image_base64")
            if not isinstance(image_base64, str) or not image_base64:
                return response(400, {"error": "image_base64 is required"})

            try:
                image_bytes = base64.b64decode(
                    image_base64, validate=True
                )
            except (binascii.Error, ValueError):
                return response(400, {"error": "image_base64 must be valid Base64"})

            result = service.upload_image(
                owner_id=payload.get("owner_id"),
                filename=payload.get("filename"),
                content_type=payload.get("content_type"),
                image_bytes=image_bytes,
                caption=payload.get("caption", ""),
            )

            return response(201, result)

        # GET /images - List images
        if method == "GET" and path == "/images":
            result = service.list_images(
                owner_id=params.get("owner_id"),
                content_type=params.get("content_type"),
                limit=int(params.get("limit", "20")),
                next_token=params.get("next_token"),
            )
            return response(200, result)

        # GET /images/{image_id}/download
        if method == "GET" and path.endswith("/download"):
            image_id = path_params.get("image_id")
            result = service.download_image(image_id)

            return response(
                200,
                base64.b64encode(result["body"]).decode("utf-8"),
                headers={
                    "Content-Type": result["content_type"],
                    "Content-Disposition": "inline",
                },
                is_base64=True,
            )

        # GET /images/{image_id} - Get metadata
        if method == "GET" and path_params.get("image_id"):
            return response(
                200,
                service.get_image_metadata(path_params["image_id"]),
            )

        # DELETE /images/{image_id}
        if method == "DELETE" and path_params.get("image_id"):
            service.delete_image(path_params["image_id"])
            return {
                "statusCode": 204,
                "headers": {},
                "body": "",
            }

        return response(404, {"error": "Route not found"})

    except ImageNotFoundError:
        return response(404, {"error": "Image not found"})
    except (ValueError, TypeError) as exc:
        return response(400, {"error": str(exc)})
    except Exception:
        logger.exception("Request failed")
        return response(500, {"error": "Internal server error"})