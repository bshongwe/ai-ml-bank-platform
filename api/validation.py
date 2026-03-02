"""
Request validation for replay attack prevention and input sanitization.
"""
from datetime import datetime, timezone
from typing import Dict, Any, Set
import boto3
from pydantic import BaseModel, Field, validator


class FraudScoreRequest(BaseModel):
    """Fraud scoring request schema."""
    transaction_id: str = Field(..., min_length=1, max_length=100)
    tx_velocity_1m: float = Field(..., ge=0, le=1000)
    geo_distance_km: float = Field(..., ge=0, le=20000)
    device_entropy: float = Field(..., ge=0, le=10)
    
    @validator('transaction_id')
    def validate_transaction_id(cls, v):
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Invalid transaction_id format')
        return v


class ReplayProtection:
    """Prevent replay attacks using nonce tracking and timestamp validation."""
    
    WINDOW_SECONDS = 300  # 5 minutes
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.nonce_table = self.dynamodb.Table('api_nonces')
    
    def validate_request(self, client_id: str, nonce: str, 
                        timestamp: int) -> bool:
        """Validate request is not replayed."""
        now = int(datetime.now(timezone.utc).timestamp())
        
        # Check timestamp within window
        if abs(now - timestamp) > self.WINDOW_SECONDS:
            return False
        
        # Check nonce not used
        try:
            self.nonce_table.put_item(
                Item={
                    'client_id': client_id,
                    'nonce': nonce,
                    'timestamp': timestamp,
                    'ttl': now + self.WINDOW_SECONDS
                },
                ConditionExpression='attribute_not_exists(nonce)'
            )
            return True
        except self.dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            return False


class DistributedRateLimiter:
    """Distributed rate limiter using DynamoDB."""
    
    def __init__(self, requests_per_minute: int = 100):
        self.rpm = requests_per_minute
        self.dynamodb = boto3.resource('dynamodb')
        self.rate_table = self.dynamodb.Table('api_rate_limits')
    
    def allow(self, client_id: str) -> bool:
        """Check if request allowed under distributed rate limit."""
        now = int(datetime.now(timezone.utc).timestamp())
        minute_bucket = now // 60
        
        try:
            response = self.rate_table.update_item(
                Key={'client_id': client_id, 'minute': minute_bucket},
                UpdateExpression='ADD request_count :inc SET #ttl = :ttl',
                ExpressionAttributeNames={'#ttl': 'ttl'},
                ExpressionAttributeValues={
                    ':inc': 1,
                    ':ttl': now + 120,
                    ':limit': self.rpm
                },
                ConditionExpression='attribute_not_exists(request_count) OR request_count < :limit',
                ReturnValues='UPDATED_NEW'
            )
            return True
        except self.dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            return False
