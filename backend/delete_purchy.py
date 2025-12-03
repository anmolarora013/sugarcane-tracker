import os
import json
import boto3
import traceback

# CONFIG
TABLE_NAME = os.environ.get("PURCHIES_TABLE_NAME", "Purchies")

# CORS - during dev '*' is easiest. For production set exact origin.
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
}

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


def lambda_handler(event, context):
    try:
        # Handle preflight
        if event.get("httpMethod") == "OPTIONS":
            return {"statusCode": 200, "headers": CORS_HEADERS, "body": ""}

        # Accept keys either from queryStringParameters or JSON body (API Gateway proxy)
        params = event.get("queryStringParameters") or {}
        body = {}
        if event.get("body"):
            try:
                body = json.loads(event["body"])
            except Exception:
                # If body is present but not JSON, ignore
                body = {}

        account_id = params.get("account_id") or body.get("account_id")
        purchy_ts = params.get("purchy_ts") or body.get("purchy_ts")

        if not account_id or not purchy_ts:
            return {
                "statusCode": 400,
                "headers": CORS_HEADERS,
                "body": json.dumps({"message": "account_id and purchy_ts are required"}),
            }

        # Attempt deletion
        try:
            resp = table.delete_item(
                Key={"account_id": account_id, "purchy_ts": purchy_ts},
                ConditionExpression="attribute_exists(purchy_ts)"
            )
        except table.meta.client.exceptions.ConditionalCheckFailedException:
            return {
                "statusCode": 404,
                "headers": CORS_HEADERS,
                "body": json.dumps({"message": "Purchy not found"}),
            }

        # If delete succeeded, return 200 with optional JSON
        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps({"message": "Deleted successfully"})
        }

    except Exception as e:
        # Log the full stack to CloudWatch for debugging
        tb = traceback.format_exc()
        print("Exception in delete_purchy:", str(e))
        print(tb)
        # Return a 502 with error (502 is appropriate when integration failed)
        return {
            "statusCode": 502,
            "headers": CORS_HEADERS,
            "body": json.dumps({"message": "Internal delete error", "error": str(e)})
        }