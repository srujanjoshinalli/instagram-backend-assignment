
import uuid
from datetime import datetime, timezone
from botocore.exceptions import ClientError
import base64
import json


class ImageService:
    def __init__(self, s3_client, dynamodb_table, bucket_name):
        self.s3 = s3_client
        self.table = dynamodb_table
        self.bucket_name = bucket_name

    def upload_image(self, owner_id, filename, content_type,
                     image_bytes, caption=""):
        if not owner_id or not filename or not content_type:
            raise ValueError("owner_id, filename and content_type are required")

        if not image_bytes:
            raise ValueError("Image cannot be empty")

        if not content_type.startswith("image/"):
            raise ValueError("Only image content types are supported")

        image_id = str(uuid.uuid4())
        s3_key = f"images/{owner_id}/{image_id}"
        created_at = datetime.now(timezone.utc).isoformat()

        item = {
            "image_id": image_id,
            "owner_id": owner_id,
            "filename": filename,
            "content_type": content_type,
            "s3_key": s3_key,
            "size_bytes": len(image_bytes),
            "caption": caption,
            "created_at": created_at,
        }

        # Upload to S3 first.
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=s3_key,
            Body=image_bytes,
            ContentType=content_type,
        )

        try:
            self.table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(image_id)",
            )
        except Exception:
            # Best-effort rollback if metadata persistence fails.
            try:
                self.s3.delete_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                )
            except Exception:
                # Production systems should log and reconcile this failure.
                pass
            raise

        return item

    def get_image_metadata(self, image_id):
        response = self.table.get_item(
            Key={"image_id": image_id}
        )
        item = response.get("Item")

        if not item:
            raise ImageNotFoundError(image_id)

        return item

    def download_image(self, image_id):
        item = self.get_image_metadata(image_id)

        response = self.s3.get_object(
            Bucket=self.bucket_name,
            Key=item["s3_key"],
        )

        return {
            "metadata": item,
            "body": response["Body"].read(),
            "content_type": item["content_type"],
        }

    def delete_image(self, image_id):
        item = self.get_image_metadata(image_id)

        # Delete metadata only after S3 deletion succeeds.
        self.s3.delete_object(
            Bucket=self.bucket_name,
            Key=item["s3_key"],
        )

        self.table.delete_item(
            Key={"image_id": image_id},
            ConditionExpression="attribute_exists(image_id)",
        )

    def list_images(
        self,
        owner_id=None,
        content_type=None,
        limit=20,
        next_token=None,
    ):
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")

        # At least one filter is required to avoid a full table scan.
        if not owner_id and not content_type:
            raise ValueError(
                "Provide owner_id or content_type"
            )

        if owner_id:
            query_args = {
                "IndexName": "OwnerCreatedAtIndex",
                "KeyConditionExpression": "owner_id = :owner",
                "ExpressionAttributeValues": {
                    ":owner": owner_id,
                },
                "Limit": limit,
                "ScanIndexForward": False,
            }
        else:
            query_args = {
                "IndexName": "ContentTypeCreatedAtIndex",
                "KeyConditionExpression": "content_type = :type",
                "ExpressionAttributeValues": {
                    ":type": content_type,
                },
                "Limit": limit,
                "ScanIndexForward": False,
            }

        if owner_id and content_type:
            query_args["FilterExpression"] = (
                "content_type = :type"
            )
            query_args["ExpressionAttributeValues"][":type"] = (
                content_type
            )

        if next_token:
            try:
                decoded = base64.urlsafe_b64decode(
                    next_token.encode("utf-8")
                )
                query_args["ExclusiveStartKey"] = json.loads(
                    decoded.decode("utf-8")
                )
            except Exception as exc:
                raise ValueError("Invalid next_token") from exc

        response = self.table.query(**query_args)

        last_key = response.get("LastEvaluatedKey")
        encoded_token = None

        if last_key:
            encoded_token = base64.urlsafe_b64encode(
                json.dumps(last_key).encode("utf-8")
            ).decode("utf-8")

        return {
            "items": response.get("Items", []),
            "next_token": encoded_token,
        }


class ImageNotFoundError(Exception):
    pass