"""AWS Kinesis → Lambda → S3 Bronze streaming pipeline.

Components:
- kinesis_consumer.py: Long-running consumer for direct Kinesis reading
- lambda_handler.py: AWS Lambda function for event-driven processing
- deploy_infrastructure.py: Infrastructure deployment script

Architecture:
1. Transaction events → Kinesis stream (fraud-transactions)
2. Lambda triggered every 1-min or 1000 records (whichever first)
3. Lambda batches events → S3 Bronze (JSONL format)
4. Failed records → DLQ bucket for replay
5. S3KeySensor in fraud_streaming_dag.py detects new files

Security:
- ExpectedBucketOwner prevents bucket confusion attacks
- Server-side encryption (AES256) on S3
- AWS account ID dynamically injected during deployment

Deployment:
```bash
python ingestion/streaming/deploy_infrastructure.py
```

Production Usage:
- Lambda auto-scales with Kinesis throughput
- At-least-once delivery guaranteed
- DLQ for failed record replay
"""

from .kinesis_consumer import KinesisConsumer
from .lambda_handler import lambda_handler

__all__ = ['KinesisConsumer', 'lambda_handler']

# Security: ExpectedBucketOwner parameter prevents bucket confusion attacks
# where an attacker could delete and recreate your S3 bucket under their
# account, causing your Lambda to write sensitive fraud data to their bucket.
