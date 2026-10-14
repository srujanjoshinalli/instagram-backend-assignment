
import os
import boto3


AWS_ENDPOINT_URL = os.getenv(
    "AWS_ENDPOINT_URL",
    "http://localhost:4566",
)

AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
BUCKET_NAME = os.getenv("IMAGE_BUCKET", "image-storage-local")
TABLE_NAME = os.getenv("IMAGE_TABLE", "Images")


def create_aws_resources():
    session = boto3.Session(region_name=AWS_REGION)

    s3 = session.client(
        "s3",
        endpoint_url=AWS_ENDPOINT_URL,
    )

    dynamodb = session.resource(
        "dynamodb",
        endpoint_url=AWS_ENDPOINT_URL,
    )

    table = dynamodb.Table(TABLE_NAME)

    return s3, table