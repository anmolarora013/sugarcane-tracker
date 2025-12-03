import json
import os
import uuid
from datetime import datetime, timezone, timedelta
import boto3

dynamodb = boto3.resource('dynamodb')
ACCOUNTS_TABLE_NAME = os.environ.get('ACCOUNTS_TABLE_NAME', 'Accounts')
accounts_table = dynamodb.Table(ACCOUNTS_TABLE_NAME)

def lambda_handler(event, context):
    # TODO implement
    try:
        if "body" in event:
            body = json.loads(event['body'] or "{}")
        else:
            body = event
        
        account_name = body.get('account_name')
        
        if not account_name:
            return {
                'statusCode': 400,
                'body': json.dumps('account_name is required')
            }
        
        account_id = str(uuid.uuid4())
        ist = timezone(timedelta(hours=5, minutes=30))
        now = datetime.now(ist)
        created_at = now.isoformat(timespec='seconds')

        item = {
            'account_id': account_id,
            'account_name': account_name,
            'created_at': created_at,
            'is_active': True
        }

        accounts_table.put_item(Item=item)

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "message": "Account created successfully",
                "account": item
            })
        }
    except Exception as e:
        print("Error in add_account:", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"message":"Internal server error","error":str(e)})
        }
    
