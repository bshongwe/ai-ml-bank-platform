"""
AWS Lambda Handler for Kinesis Stream Processing
Triggered by Kinesis, batches events, writes to S3 Bronze.
"""
import json
import boto3
from botocore.config import Config
import base64
from datetime import datetime, timezone
import os
from typing import Dict, Any, List

S3_BUCKET = os.getenv('BRONZE_S3_BUCKET', 'bank-datalake-bronze')
S3_PREFIX = 'payments_raw'
DLQ_BUCKET = os.getenv('DLQ_S3_BUCKET', 'bank-datalake-dlq')
AWS_ACCOUNT_ID = os.getenv('AWS_ACCOUNT_ID')

# Lambda timeout: 60s total
# Budget: 5s parse + 15s S3 write + 10s DLQ + 30s buffer
s3_client = boto3.client('s3', config=Config(
    connect_timeout=5,
    read_timeout=10,
    retries={'max_attempts': 2}
))


def parse_kinesis_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Parse Kinesis record to Bronze schema."""
    data_bytes = base64.b64decode(record['kinesis']['data'])
    data = json.loads(data_bytes)
    
    return {
        'event_id': data.get('event_id'),
        'event_type': data.get('event_type', 'payment_authorised'),
        'event_time': data.get('event_time'),
        'source_system': data.get('source_system', 'cards'),
        'payload': data.get('payload', {}),
        'kinesis_sequence': record['kinesis']['sequenceNumber'],
        'kinesis_timestamp': record['kinesis']['approximateArrivalTimestamp']
    }


def write_to_s3(records: List[Dict[str, Any]]) -> str:
    """Write batch to S3 Bronze as JSONL."""
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    key = f"{S3_PREFIX}/fraud_events_{timestamp}.json"
    
    jsonl_data = '\n'.join(json.dumps(r) for r in records)
    
    put_params = {
        'Bucket': S3_BUCKET,
        'Key': key,
        'Body': jsonl_data.encode('utf-8'),
        'ContentType': 'application/x-ndjson',
        'ServerSideEncryption': 'AES256'
    }
    if AWS_ACCOUNT_ID:
        put_params['ExpectedBucketOwner'] = AWS_ACCOUNT_ID
    
    try:
        s3_client.put_object(**put_params)
    except Exception as e:
        print(f"S3 write timeout/error: {e}")
        raise
    
    return f"s3://{S3_BUCKET}/{key}"


def write_to_dlq(record: Dict[str, Any], error: str) -> None:
    """Write failed record to Dead Letter Queue."""
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
    key = f"dlq/fraud_events_{timestamp}.json"
    
    dlq_record = {
        'record': record,
        'error': error,
        'failed_at': datetime.now(timezone.utc).isoformat()
    }
    
    put_params = {
        'Bucket': DLQ_BUCKET,
        'Key': key,
        'Body': json.dumps(dlq_record).encode('utf-8')
    }
    if AWS_ACCOUNT_ID:
        put_params['ExpectedBucketOwner'] = AWS_ACCOUNT_ID
    
    try:
        s3_client.put_object(**put_params)
    except Exception as e:
        print(f"DLQ write failed: {e}")
        raise


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for Kinesis stream processing.
    Batches records and writes to S3 Bronze.
    
    Timeout budget (60s Lambda limit):
    - Parse records: ~5s (1000 records)
    - S3 write: 15s max (5s connect + 10s read)
    - DLQ writes: 10s
    - Buffer: 30s for retries
    """
    records = event.get('Records', [])
    parsed_records = []
    failed_count = 0
    
    for record in records:
        try:
            parsed = parse_kinesis_record(record)
            parsed_records.append(parsed)
        except Exception as e:
            failed_count += 1
            try:
                write_to_dlq(record, str(e))
            except Exception as dlq_error:
                print(f"DLQ write failed: {dlq_error}")
            print(f"Failed to parse record: {e}")
    
    if parsed_records:
        try:
            s3_path = write_to_s3(parsed_records)
            print(f"Wrote {len(parsed_records)} records to {s3_path}")
        except Exception as e:
            print(f"S3 write failed, records lost: {e}")
            raise
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'processed': len(parsed_records),
            'failed': failed_count,
            'total': len(records)
        })
    }
