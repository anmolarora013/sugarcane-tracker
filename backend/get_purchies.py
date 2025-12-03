import os
import json
import math
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr
import boto3
from datetime import datetime, timezone

# Config from env
PURCHIES_TABLE = os.environ.get("PURCHIES_TABLE_NAME", "Purchies")
ACCOUNTS_TABLE = os.environ.get("ACCOUNTS_TABLE_NAME", "Accounts")

# CORS (dev '*' is OK; set specific origin in production)
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
}

dynamodb = boto3.resource("dynamodb")
p_table = dynamodb.Table(PURCHIES_TABLE)
dynamodb_client = boto3.client("dynamodb")  # for batch_get_item

def decimal_to_native(obj):
    if isinstance(obj, list):
        return [decimal_to_native(i) for i in obj]
    if isinstance(obj, dict):
        return {k: decimal_to_native(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return float(obj)
    return obj

def build_response(status_code, body_obj=None):
    body = "" if body_obj is None else json.dumps(decimal_to_native(body_obj))
    return {
        "statusCode": status_code,
        "headers": { "Content-Type": "application/json", **CORS_HEADERS },
        "body": body
    }

def chunk_list(lst, n):
    """Yield successive n-sized chunks from list."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def batch_get_accounts(account_ids):
    """Return dict mapping account_id -> account_name using BatchGetItem with chunking (max 100 keys)."""
    if not account_ids:
        return {}

    result_map = {}
    # DynamoDB BatchGetItem limit: 100 items per request
    for chunk in chunk_list(list(account_ids), 100):
        keys = [{"account_id": {"S": aid}} for aid in chunk]
        request_items = {
            ACCOUNTS_TABLE: {
                "Keys": keys,
                "ProjectionExpression": "account_id, account_name"
            }
        }

        resp = dynamodb_client.batch_get_item(RequestItems=request_items)
        # parse returned items
        responses = resp.get("Responses", {}).get(ACCOUNTS_TABLE, [])
        for item in responses:
            # item is in DynamoDB JSON format, convert safely
            aid = item.get("account_id", {}).get("S")
            aname = item.get("account_name", {}).get("S") if item.get("account_name") else None
            if aid:
                result_map[aid] = aname

        # handle UnprocessedKeys (retry simple backoff)
        unprocessed = resp.get("UnprocessedKeys", {})
        retries = 0
        while unprocessed and retries < 3:
            resp2 = dynamodb_client.batch_get_item(RequestItems=unprocessed)
            responses2 = resp2.get("Responses", {}).get(ACCOUNTS_TABLE, [])
            for item in responses2:
                aid = item.get("account_id", {}).get("S")
                aname = item.get("account_name", {}).get("S") if item.get("account_name") else None
                if aid:
                    result_map[aid] = aname
            unprocessed = resp2.get("UnprocessedKeys", {})
            retries += 1

    return result_map

def lambda_handler(event, context):
    try:
        # Preflight support
        if event.get("httpMethod") == "OPTIONS":
            return build_response(200, None)

        params = event.get("queryStringParameters") or {}
        account_id = (params.get("account_id") or "ALL").strip()
        from_date = params.get("from")  # 'YYYY-MM-DD' or None
        to_date = params.get("to")      # 'YYYY-MM-DD' or None

        # Build purchy_ts bounds (simple YYYY-MM-DD -> start/end of day)
        if from_date:
            from_ts = f"{from_date}T00:00:00Z"
        else:
            from_ts = "0000-01-01T00:00:00Z"

        if to_date:
            to_ts = f"{to_date}T23:59:59Z"
        else:
            to_ts = "9999-12-31T23:59:59Z"

        items = []

        # Query or Scan
        if account_id and account_id.upper() != "ALL":
            resp = p_table.query(
                KeyConditionExpression=Key("account_id").eq(account_id) & Key("purchy_ts").between(from_ts, to_ts),
                ScanIndexForward=False
            )
            items.extend(resp.get("Items", []))
            while "LastEvaluatedKey" in resp:
                resp = p_table.query(
                    KeyConditionExpression=Key("account_id").eq(account_id) & Key("purchy_ts").between(from_ts, to_ts),
                    ExclusiveStartKey=resp["LastEvaluatedKey"],
                    ScanIndexForward=False
                )
                items.extend(resp.get("Items", []))
        else:
            resp = p_table.scan(
                FilterExpression=Attr("purchy_ts").between(from_ts, to_ts)
            )
            items.extend(resp.get("Items", []))
            while "LastEvaluatedKey" in resp:
                resp = p_table.scan(
                    FilterExpression=Attr("purchy_ts").between(from_ts, to_ts),
                    ExclusiveStartKey=resp["LastEvaluatedKey"]
                )
                items.extend(resp.get("Items", []))

        # Collect unique account_ids from items
        account_ids = set()
        for it in items:
            aid = it.get("account_id")
            if aid:
                account_ids.add(aid)

        # Batch-get account names from Accounts table
        account_map = batch_get_accounts(account_ids)  # returns {account_id: account_name}

        # Compute totals and merge account_name into items
        total_weight = Decimal("0")
        total_amount = Decimal("0")
        merged_items = []

        for it in items:
            # ensure weight/rate/amount are Decimal where possible
            weight = it.get("weight")
            rate = it.get("rate")
            amount = it.get("amount")
            purchy_id = it.get("purchy_id")

            # Normalize numeric types -> Decimal or None
            try:
                if isinstance(weight, (int, float, str)):
                    weight = Decimal(str(weight)) if weight != "" else None
                elif isinstance(weight, Decimal):
                    pass
                else:
                    weight = None
            except Exception:
                weight = None

            try:
                if isinstance(rate, (int, float, str)):
                    rate = Decimal(str(rate)) if rate != "" else None
                elif isinstance(rate, Decimal):
                    pass
                else:
                    rate = None
            except Exception:
                rate = None

            try:
                if isinstance(amount, (int, float, str)):
                    amount = Decimal(str(amount)) if amount != "" else None
                elif isinstance(amount, Decimal):
                    pass
                else:
                    amount = None
            except Exception:
                amount = None

            if amount is None and weight is not None and rate is not None:
                amount = weight * rate

            if weight is not None:
                total_weight += weight
            if amount is not None:
                total_amount += amount

            # merge account_name from account_map if not present in item
            merged = dict(it)  # shallow copy
            if "account_name" not in merged or merged.get("account_name") in (None, ""):
                merged["account_name"] = account_map.get(merged.get("account_id"))  # may be None

            # keep weight/rate/amount as Decimal for decimal_to_native
            if weight is not None:
                merged["weight"] = weight
            if rate is not None:
                merged["rate"] = rate
            if amount is not None:
                merged["amount"] = amount
            if purchy_id is not None:
                merged["purchy_id"] = purchy_id

            merged_items.append(merged)

        response_body = {
            "count": len(merged_items),
            "total_weight": total_weight,
            "total_amount": total_amount,
            "items": merged_items
        }

        return build_response(200, response_body)

    except Exception as e:
        # log and return 500
        print("Error in get_purchies:", str(e))
        import traceback
        traceback.print_exc()
        return build_response(500, {"message": "Internal server error", "error": str(e)})

