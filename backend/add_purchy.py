import json
import os
import boto3
import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta


dynamodb = boto3.resource('dynamodb')
PURCHIES_TABLE_NAME = os.environ.get('PURCHIES_TABLE_NAME','Purchies')
purchies_table = dynamodb.Table(PURCHIES_TABLE_NAME)

def lambda_handler(event, context):
    try:
        if "body" in event:
            body = json.loads(event['body'] or '{}')
        else:
            body = event
        
        account_id = body.get('account_id')
        date_str = body.get('date')
        weight = body.get('weight')
        purchy_id = body.get('purchy_id', str(uuid.uuid4()))
        note = body.get('note', '')

        if not account_id or not date_str or weight is None:
            return {
                'statusCode': 400,
                'body': json.dumps('Missing required fields')
            }
        now = datetime.now(timezone(timedelta(hours=5, minutes=30)))
        purchy_ts = now.isoformat(timespec='seconds')

        item = {
            "account_id": account_id,
            "purchy_ts": purchy_ts,
            "purchy_id": purchy_id,
            "purchy_date": date_str,
            "weight": Decimal(str((weight))),
            "note": note,
            "rate": 405
        }

        purchies_table.put_item(Item=item)
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({"message": "Purchy recorded successfully"})#, "data": item})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error recording purchy: {str(e)}')
        }
