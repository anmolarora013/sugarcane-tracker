import os
import json
import base64
import traceback
from decimal import Decimal
import boto3

# Config
TABLE = os.environ.get("PURCHIES_TABLE_NAME")

# CORS headers (use exact origin in production instead of "*")
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
}

dynamodb = boto3.resource("dynamodb")
client = boto3.client("dynamodb")
table = dynamodb.Table(TABLE)


# ---------- Helpers ----------

def parse_event_body(event):
    """
    Robust parsing of event['body'] for API Gateway proxy and Lambda test events.
    Returns (body_dict_or_none, error_message_or_none)
    """
    raw = event.get("body")
    if raw is None:
        return None, None

    # Already a dict (some test harnesses)
    if isinstance(raw, dict):
        return raw, None

    # bytes -> decode
    if isinstance(raw, (bytes, bytearray)):
        try:
            raw = raw.decode("utf-8")
        except Exception as e:
            return None, f"Failed to decode bytes body: {e}"

    # base64 encoded payload
    if event.get("isBase64Encoded"):
        try:
            decoded = base64.b64decode(raw)
            raw = decoded.decode("utf-8")
        except Exception as e:
            return None, f"Failed to base64-decode body: {e}"

    # string json
    if isinstance(raw, str):
        raw = raw.strip()
        if raw == "":
            return None, None
        try:
            obj = json.loads(raw)
            return obj, None
        except json.JSONDecodeError as e:
            return None, f"JSON decode error: {e.msg} at pos {e.pos}"
        except Exception as e:
            return None, f"Unknown JSON parse error: {str(e)}"

    return None, "Unsupported body type"


def decimalize(value):
    """Convert numeric value (str/int/float) to Decimal or return None if invalid/empty."""
    if value is None or value == "":
        return None
    try:
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float, str)):
            return Decimal(str(value))
    except Exception:
        return None
    return None


def decimal_to_native(obj):
    """Recursively convert Decimal to float for JSON serialization."""
    if isinstance(obj, list):
        return [decimal_to_native(i) for i in obj]
    if isinstance(obj, dict):
        return {k: decimal_to_native(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        # Convert to float — can be changed to str() if precision must be preserved
        return float(obj)
    return obj


def to_ddb_value(v):
    """Convert a Python primitive (str, int, float, Decimal) to DynamoDB attribute value format for client.transact_write_items."""
    if v is None:
        return None
    if isinstance(v, str):
        return {"S": v}
    if isinstance(v, bool):
        return {"BOOL": v}
    if isinstance(v, Decimal):
        return {"N": str(v)}
    if isinstance(v, (int, float)):
        return {"N": str(v)}
    # fallback to string
    return {"S": str(v)}


def api_response(status_code, body_obj=None):
    """Return API Gateway proxy integration response with CORS headers.
       body_obj will be JSON-serialized; if None, return empty body (useful for OPTIONS and some success responses)."""
    if body_obj is None:
        body = ""
    else:
        body = json.dumps(decimal_to_native(body_obj))
    return {"statusCode": status_code, "headers": CORS_HEADERS, "body": body}


# ---------- Lambda handler ----------

def lambda_handler(event, context):
    try:
        # # Preflight (CORS)
        # if event.get("httpMethod") == "OPTIONS":
        #     return api_response(200, None)

         # Only accept PUT for this Lambda
        method = event.get("httpMethod")
        if method != "PUT":
            return api_response(405, {"message": "Method Not Allowed"})

        # Parse body robustly
        body, err = parse_event_body(event)
        if err:
            return api_response(400, {"message": "Invalid JSON body", "error": err})
        if body is None:
            return api_response(400, {"message": "Request body required"})

        # Required identifiers to locate the existing record
        old_account_id = body.get("account_id")  # current partition key of the item
        purchy_ts = body.get("purchy_ts")       # sort key (must be provided)
        if not old_account_id or not purchy_ts:
            return api_response(400, {"message": "account_id and purchy_ts are required to identify the purchy"})

        # Allowed update fields (per your request)
        # This Lambda accepts a special field `new_account_id` to move item to another account.
        new_account_id = body.get("new_account_id")
        # For convenience, accept account_id_new aliases (older variants)
        if not new_account_id:
            new_account_id = body.get("new_account_id")

        purchy_id = body.get("purchy_id")    # purchy_number
        date = body.get("date")              # purchy_date (YYYY-MM-DD)
        weight = body.get("weight")          # numeric

        # Read existing item
        get_resp = table.get_item(Key={"account_id": old_account_id, "purchy_ts": purchy_ts})
        existing = get_resp.get("Item")
        if not existing:
            return api_response(404, {"message": "Purchy not found"})

        # If moving partition (account change) and target differs:
        if new_account_id and new_account_id != old_account_id:
            # Build new item by copying existing and applying allowed updates
            new_item = dict(existing)  # shallow copy
            new_item["account_id"] = new_account_id
            new_item["purchy_ts"] = purchy_ts  # keep same timestamp

            # Apply updates
            if purchy_id is not None:
                if purchy_id == "" or purchy_id is None:
                    new_item.pop("purchy_id", None)
                else:
                    new_item["purchy_id"] = str(purchy_id)

            if date is not None:
                if date == "" or date is None:
                    new_item.pop("date", None)
                else:
                    new_item["date"] = str(date)

            if weight is not None:
                wdec = decimalize(weight)
                if wdec is None:
                    new_item.pop("weight", None)
                else:
                    new_item["weight"] = wdec

            # Prepare Put and Delete for TransactWriteItems
            put_item_map = {}
            for k, v in new_item.items():
                # do not include None values
                if v is None:
                    continue
                av = to_ddb_value(v)
                if av is not None:
                    put_item_map[k] = av

            delete_key = {"account_id": {"S": old_account_id}, "purchy_ts": {"S": purchy_ts}}

            try:
                client.transact_write_items(
                    TransactItems=[
                        {"Put": {"TableName": TABLE, "Item": put_item_map}},
                        {"Delete": {"TableName": TABLE, "Key": delete_key, "ConditionExpression": "attribute_exists(purchy_ts)"}}
                    ]
                )
            except client.exceptions.TransactionCanceledException as e:
                # Transaction failed; log and return error
                print("TransactionCanceledException:", str(e))
                return api_response(500, {"message": "Transaction cancelled", "error": str(e)})
            except Exception as e:
                print("TransactWriteItems exception:", str(e))
                traceback.print_exc()
                return api_response(500, {"message": "Internal error during move", "error": str(e)})

            # Return the new_item (convert Decimal to native)
            return api_response(200, {"message": "Updated (moved) successfully", "item": new_item})

        # --- else: account unchanged -> UpdateItem for allowed attributes ---

        update_expressions = []
        expr_attr_vals = {}
        expr_attr_names = {}
        remove_attrs = []
        idx = 0

        def add_set(name, value):
            nonlocal idx
            idx += 1
            ph_name = f"#n{idx}"
            ph_val = f":v{idx}"
            expr_attr_names[ph_name] = name
            expr_attr_vals[ph_val] = value
            update_expressions.append(f"{ph_name} = {ph_val}")

        # DATE
        if date is not None:
            if date == "" or date is None:
                remove_attrs.append("date")
            else:
                add_set("date", date)

        # PURCHY_ID
        if purchy_id is not None:
            if purchy_id == "" or purchy_id is None:
                remove_attrs.append("purchy_id")
            else:
                add_set("purchy_id", str(purchy_id))

        # WEIGHT
        if weight is not None:
            wdec = decimalize(weight)
            if wdec is None:
                remove_attrs.append("weight")
            else:
                add_set("weight", wdec)

        if not update_expressions and not remove_attrs:
            return api_response(400, {"message": "No valid updates provided"})

        set_expr = ""
        remove_expr = ""
        if update_expressions:
            set_expr = "SET " + ", ".join(update_expressions)
        if remove_attrs:
            remove_expr = " REMOVE " + ", ".join(remove_attrs)

        final_expr = (set_expr + remove_expr).strip()
        if not final_expr:
            return api_response(400, {"message": "No valid updates after processing"})

        # build update params; DynamoDB resource expects ExpressionAttributeValues to be native Python types (Decimals allowed)
        update_params = {
            "Key": {"account_id": old_account_id, "purchy_ts": purchy_ts},
            "UpdateExpression": final_expr,
            "ConditionExpression": "attribute_exists(purchy_ts)",
            "ReturnValues": "ALL_NEW"
        }
        if expr_attr_names:
            update_params["ExpressionAttributeNames"] = expr_attr_names
        if expr_attr_vals:
            update_params["ExpressionAttributeValues"] = expr_attr_vals

        # Remove None entries (just in case)
        update_params = {k: v for k, v in update_params.items() if v is not None}

        try:
            resp = table.update_item(**update_params)
            new_attrs = resp.get("Attributes", {})
            return api_response(200, {"message": "Updated successfully", "item": new_attrs})
        except table.meta.client.exceptions.ConditionalCheckFailedException:
            return api_response(404, {"message": "Purchy not found"})
        except Exception as e:
            print("UpdateItem exception:", str(e))
            traceback.print_exc()
            return api_response(500, {"message": "Internal update error", "error": str(e)})

    except Exception as e:
        print("Unhandled exception in handler:", str(e))
        traceback.print_exc()
        return api_response(500, {"message": "Internal server error", "error": str(e)})