"""
Setup DynamoDB tables with explicit KMS encryption.
"""
import boto3


def create_encrypted_tables():
    """Create DynamoDB tables with KMS encryption."""
    dynamodb = boto3.client('dynamodb')
    
    # API nonces table
    try:
        dynamodb.create_table(
            TableName='api_nonces',
            KeySchema=[
                {'AttributeName': 'client_id', 'KeyType': 'HASH'},
                {'AttributeName': 'nonce', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'client_id', 'AttributeType': 'S'},
                {'AttributeName': 'nonce', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST',
            SSESpecification={
                'Enabled': True,
                'SSEType': 'KMS',
                'KMSMasterKeyId': 'alias/dynamodb-encryption-key'
            },
            TimeToLiveSpecification={
                'Enabled': True,
                'AttributeName': 'ttl'
            }
        )
        print("Created api_nonces table with KMS encryption")
    except dynamodb.exceptions.ResourceInUseException:
        print("api_nonces table already exists")
    
    # Rate limits table
    try:
        dynamodb.create_table(
            TableName='api_rate_limits',
            KeySchema=[
                {'AttributeName': 'client_id', 'KeyType': 'HASH'},
                {'AttributeName': 'minute', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'client_id', 'AttributeType': 'S'},
                {'AttributeName': 'minute', 'AttributeType': 'N'}
            ],
            BillingMode='PAY_PER_REQUEST',
            SSESpecification={
                'Enabled': True,
                'SSEType': 'KMS',
                'KMSMasterKeyId': 'alias/dynamodb-encryption-key'
            },
            TimeToLiveSpecification={
                'Enabled': True,
                'AttributeName': 'ttl'
            }
        )
        print("Created api_rate_limits table with KMS encryption")
    except dynamodb.exceptions.ResourceInUseException:
        print("api_rate_limits table already exists")


if __name__ == '__main__':
    create_encrypted_tables()
