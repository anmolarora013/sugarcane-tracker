import json
import boto3
import os


dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('ACCOUNTS_TABLE_NAME', 'Accounts')
accounts_table = dynamodb.Table(table_name)

def lambda_handler(event, context):
    try:
        print("Event:",json.dumps(event))

        response = accounts_table.scan()
        items = response.get('Items', [])

        active_accounts = [{"account_id": item.get("account_id"),"account_name": item.get("account_name")} for item in items if item.get("is_active", False)]

        active_accounts.sort(key=lambda x: x["account_name"].lower())
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json',"Access-Control-Allow-Origin":"*"},
            'body': json.dumps(active_accounts)
        }
    except Exception as e:
        print("Error:", str(e))
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal Server Error',"error_message": str(e)})
        }

