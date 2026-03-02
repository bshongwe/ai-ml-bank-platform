"""
AWS Infrastructure as Code (Terraform-style Python)
Defines Kinesis stream, Lambda function, S3 buckets, IAM roles.
"""
import boto3
import json
from pathlib import Path

# Infrastructure configuration
STREAM_CONFIG = {
    'StreamName': 'fraud-transactions',
    'ShardCount': 2,
    'RetentionPeriodHours': 24
}

LAMBDA_CONFIG = {
    'FunctionName': 'fraud-stream-processor',
    'Runtime': 'python3.11',
    'Handler': 'lambda_handler.lambda_handler',
    'Timeout': 60,
    'MemorySize': 512,
    'Environment': {
        'BRONZE_S3_BUCKET': 'bank-datalake-bronze',
        'DLQ_S3_BUCKET': 'bank-datalake-dlq',
        'AWS_ACCOUNT_ID': None  # Set dynamically during deployment
    }
}

S3_BUCKETS = [
    'bank-datalake-bronze',
    'bank-datalake-dlq'
]


def create_kinesis_stream():
    """Create Kinesis data stream."""
    kinesis = boto3.client('kinesis')
    try:
        kinesis.create_stream(
            StreamName=STREAM_CONFIG['StreamName'],
            ShardCount=STREAM_CONFIG['ShardCount'],
            StreamModeDetails={'StreamMode': 'PROVISIONED'}
        )
        print(f"Created Kinesis stream: {STREAM_CONFIG['StreamName']}")
    except kinesis.exceptions.ResourceInUseException:
        print(f"Stream {STREAM_CONFIG['StreamName']} already exists")


def create_s3_buckets():
    """Create S3 buckets for Bronze and DLQ."""
    s3 = boto3.client('s3')
    sts = boto3.client('sts')
    account_id = sts.get_caller_identity()['Account']
    
    for bucket in S3_BUCKETS:
        try:
            s3.create_bucket(Bucket=bucket)
            s3.put_bucket_encryption(
                Bucket=bucket,
                ExpectedBucketOwner=account_id,
                ServerSideEncryptionConfiguration={
                    'Rules': [{
                        'ApplyServerSideEncryptionByDefault': {
                            'SSEAlgorithm': 'AES256'
                        }
                    }]
                }
            )
            print(f"Created S3 bucket: {bucket}")
        except s3.exceptions.BucketAlreadyOwnedByYou:
            print(f"Bucket {bucket} already exists")


def create_lambda_role():
    """Create IAM role for Lambda with Kinesis and S3 permissions."""
    iam = boto3.client('iam')
    role_name = 'fraud-stream-lambda-role'
    
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }
    
    try:
        response = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy)
        )
        role_arn = response['Role']['Arn']
        
        iam.attach_role_policy(
            RoleName=role_name,
            PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaKinesisExecutionRole'
        )
        
        iam.attach_role_policy(
            RoleName=role_name,
            PolicyArn='arn:aws:iam::aws:policy/AmazonS3FullAccess'
        )
        
        print(f"Created IAM role: {role_arn}")
        return role_arn
    except iam.exceptions.EntityAlreadyExistsException:
        response = iam.get_role(RoleName=role_name)
        return response['Role']['Arn']


def create_lambda_function(role_arn: str):
    """Create Lambda function for stream processing."""
    lambda_client = boto3.client('lambda')
    sts = boto3.client('sts')
    
    account_id = sts.get_caller_identity()['Account']
    
    # Package lambda_handler.py as deployment package
    lambda_code = Path('ingestion/streaming/lambda_handler.py').read_bytes()
    
    env_vars = LAMBDA_CONFIG['Environment'].copy()
    env_vars['AWS_ACCOUNT_ID'] = account_id
    
    try:
        response = lambda_client.create_function(
            FunctionName=LAMBDA_CONFIG['FunctionName'],
            Runtime=LAMBDA_CONFIG['Runtime'],
            Role=role_arn,
            Handler=LAMBDA_CONFIG['Handler'],
            Code={'ZipFile': lambda_code},
            Timeout=LAMBDA_CONFIG['Timeout'],
            MemorySize=LAMBDA_CONFIG['MemorySize'],
            Environment={'Variables': env_vars}
        )
        print(f"Created Lambda function: {response['FunctionArn']}")
        return response['FunctionArn']
    except lambda_client.exceptions.ResourceConflictException:
        response = lambda_client.get_function(
            FunctionName=LAMBDA_CONFIG['FunctionName']
        )
        return response['Configuration']['FunctionArn']


def create_event_source_mapping(lambda_arn: str, stream_arn: str):
    """Map Kinesis stream to Lambda trigger."""
    lambda_client = boto3.client('lambda')
    
    try:
        response = lambda_client.create_event_source_mapping(
            EventSourceArn=stream_arn,
            FunctionName=lambda_arn,
            StartingPosition='LATEST',
            BatchSize=1000,
            MaximumBatchingWindowInSeconds=60
        )
        print(f"Created event source mapping: {response['UUID']}")
    except lambda_client.exceptions.ResourceConflictException:
        print("Event source mapping already exists")


def deploy_infrastructure():
    """Deploy complete streaming infrastructure."""
    print("Deploying fraud streaming infrastructure...")
    
    create_s3_buckets()
    create_kinesis_stream()
    
    role_arn = create_lambda_role()
    lambda_arn = create_lambda_function(role_arn)
    
    kinesis = boto3.client('kinesis')
    stream_desc = kinesis.describe_stream(
        StreamName=STREAM_CONFIG['StreamName']
    )
    stream_arn = stream_desc['StreamDescription']['StreamARN']
    
    create_event_source_mapping(lambda_arn, stream_arn)
    
    print("\nInfrastructure deployment complete!")
    print(f"Kinesis Stream: {STREAM_CONFIG['StreamName']}")
    print(f"Lambda Function: {LAMBDA_CONFIG['FunctionName']}")
    print(f"Bronze Bucket: s3://{S3_BUCKETS[0]}")
    print(f"DLQ Bucket: s3://{S3_BUCKETS[1]}")


if __name__ == '__main__':
    deploy_infrastructure()
