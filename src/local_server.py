import base64
import json

from fastapi import FastAPI, Request
from fastapi.responses import Response

from src.handler import lambda_handler

app = FastAPI(title="Image Storage API")


@app.api_route(
    "/{full_path:path}",
    methods=["GET", "POST", "DELETE", "PUT", "PATCH"],
)
async def dispatch(full_path: str, request: Request):
    body_bytes = await request.body()
    content_type = request.headers.get("content-type", "")

    event = {
        "httpMethod": request.method,
        "path": "/" + full_path,
        "pathParameters": {},
        "queryStringParameters": dict(request.query_params) or None,
        "headers": dict(request.headers),
        "body": None,
        "isBase64Encoded": False,
    }

    if body_bytes:
        if content_type.startswith("application/json"):
            event["body"] = body_bytes.decode("utf-8")
        else:
            event["body"] = base64.b64encode(body_bytes).decode("utf-8")
            event["isBase64Encoded"] = True

    # Extract image_id for routes such as /images/{image_id}
    parts = full_path.strip("/").split("/")
    if len(parts) >= 2 and parts[0] == "images":
        event["pathParameters"]["image_id"] = parts[1]

    result = lambda_handler(event, None)

    response_body = result.get("body", "")
    headers = result.get("headers", {})

    if result.get("isBase64Encoded"):
        response_body = base64.b64decode(response_body)

    return Response(
        content=response_body,
        status_code=result.get("statusCode", 200),
        headers=headers,
    )
