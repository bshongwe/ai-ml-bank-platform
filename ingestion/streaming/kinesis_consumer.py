"""
AWS Kinesis Consumer for Fraud Transaction Streaming
Reads from Kinesis stream, batches events, writes to S3 Bronze.
"""
import json
import boto3
from datetime import datetime, timezone
from pathlib import Path
import os
from typing import List, Dict, Any

KINESIS_STREAM = os.getenv('KINESIS_STREAM_NAME', 'fraud-transactions')
S3_BUCKET = os.getenv('BRONZE_S3_BUCKET', 'bank-datalake-bronze')
S3_PREFIX = 'payments_raw'
BATCH_SIZE = 1000
BATCH_INTERVAL_SEC = 60
DLQ_BUCKET = os.getenv('DLQ_S3_BUCKET', 'bank-datalake-dlq')


class KinesisConsumer:
    """Consume Kinesis stream and batch to S3 Bronze."""

    def __init__(self):
        self.kinesis = boto3.client('kinesis')
        self.s3 = boto3.client('s3')
        self.batch = []
        self.last_flush = datetime.now(timezone.utc)

    def get_shard_iterator(self, stream_name: str, shard_id: str) -> str:
        """Get shard iterator for reading stream."""
        response = self.kinesis.get_shard_iterator(
            StreamName=stream_name,
            ShardId=shard_id,
            ShardIteratorType='LATEST'
        )
        return response['ShardIterator']

    def read_records(self, shard_iterator: str) -> tuple:
        """Read records from Kinesis shard."""
        response = self.kinesis.get_records(
            ShardIterator=shard_iterator,
            Limit=BATCH_SIZE
        )
        return response['Records'], response.get('NextShardIterator')

    def parse_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Kinesis record to Bronze schema."""
        data = json.loads(record['Data'])
        return {
            'event_id': data.get('event_id'),
            'event_type': data.get('event_type', 'payment_authorised'),
            'event_time': data.get('event_time'),
            'source_system': data.get('source_system', 'cards'),
            'payload': data.get('payload', {}),
            'kinesis_sequence': record['SequenceNumber'],
            'kinesis_timestamp': record['ApproximateArrivalTimestamp'].isoformat()
        }

    def write_to_s3(self, records: List[Dict[str, Any]]) -> None:
        """Write batch to S3 Bronze as JSONL."""
        if not records:
            return

        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        key = f"{S3_PREFIX}/fraud_events_{timestamp}.json"
        
        jsonl_data = '\n'.join(json.dumps(r) for r in records)
        
        self.s3.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=jsonl_data.encode('utf-8'),
            ContentType='application/x-ndjson'
        )
        print(f"Wrote {len(records)} records to s3://{S3_BUCKET}/{key}")

    def write_to_dlq(self, record: Dict[str, Any], error: str) -> None:
        """Write failed record to Dead Letter Queue."""
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        key = f"dlq/fraud_events_{timestamp}.json"
        
        dlq_record = {
            'record': record,
            'error': error,
            'failed_at': datetime.now(timezone.utc).isoformat()
        }
        
        self.s3.put_object(
            Bucket=DLQ_BUCKET,
            Key=key,
            Body=json.dumps(dlq_record).encode('utf-8')
        )
        print(f"Wrote failed record to DLQ: {error}")

    def should_flush(self) -> bool:
        """Check if batch should be flushed."""
        elapsed = (datetime.now(timezone.utc) - self.last_flush).total_seconds()
        return len(self.batch) >= BATCH_SIZE or elapsed >= BATCH_INTERVAL_SEC

    def flush_batch(self) -> None:
        """Flush current batch to S3."""
        if self.batch:
            self.write_to_s3(self.batch)
            self.batch = []
            self.last_flush = datetime.now(timezone.utc)

    def consume(self, stream_name: str = KINESIS_STREAM) -> None:
        """Main consumer loop."""
        response = self.kinesis.list_shards(StreamName=stream_name)
        shards = response['Shards']
        
        for shard in shards:
            shard_id = shard['ShardId']
            shard_iterator = self.get_shard_iterator(stream_name, shard_id)
            
            while shard_iterator:
                records, shard_iterator = self.read_records(shard_iterator)
                
                for record in records:
                    try:
                        parsed = self.parse_record(record)
                        self.batch.append(parsed)
                    except Exception as e:
                        self.write_to_dlq(record, str(e))
                
                if self.should_flush():
                    self.flush_batch()


if __name__ == '__main__':
    consumer = KinesisConsumer()
    consumer.consume()
