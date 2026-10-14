
import os
import boto3
from botocore.exceptions import ClientError

ENDPOINT = os.getenv(
    "AWS_ENDPOINT_URL",
    "http://localhost:4566",
)
REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
BUCKET = os.getenv("IMAGE_BUCKET", "image-storage-local")
TABLE_NAME = os.getenv("IMAGE_TABLE", "Images")

session = boto3.Session(region_name=REGION)

s3 = session.client("s3", endpoint_url=ENDPOINT)
dynamodb = session.client("dynamodb", endpoint_url=ENDPOINT)

try:
    s3.create_bucket(Bucket=BUCKET)
    print(f"Created S3 bucket: {BUCKET}")
except ClientError as exc:
    if exc.response["Error"]["Code"] in (
        "BucketAlreadyExists",
        "BucketAlreadyOwnedByYou",
    ):
        print(f"S3 bucket already exists: {BUCKET}")
    else:
        raise

try:
    dynamodb.create_table(
        TableName=TABLE_NAME,
        KeySchema=[
            {"AttributeName": "image_id", "KeyType": "HASH"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "image_id", "AttributeType": "S"},
            {"AttributeName": "owner_id", "AttributeType": "S"},
            {"AttributeName": "created_at", "AttributeType": "S"},
            {"AttributeName": "content_type", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "OwnerCreatedAtIndex",
                "KeySchema": [
                    {"AttributeName": "owner_id", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": "ContentTypeCreatedAtIndex",
                "KeySchema": [
                    {"AttributeName": "content_type", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    print(f"Created DynamoDB table: {TABLE_NAME}")
except ClientError as exc:
    if exc.response["Error"]["Code"] == "ResourceInUseException":
        print(f"DynamoDB table already exists: {TABLE_NAME}")
    else:
        raise
