"""
API authentication and rate limiting.
"""
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional
from collections import defaultdict
import boto3


class APIKeyValidator:
    """Validate API keys against secrets manager."""

    def __init__(self):
        self.secrets = boto3.client('secretsmanager')
        self.cache = {}
        self.cache_ttl = timedelta(minutes=5)

    def validate(self, api_key: str) -> Optional[str]:
        """Validate API key and return client_id."""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        if key_hash in self.cache:
            cached_time, client_id = self.cache[key_hash]
            if datetime.now(timezone.utc) - cached_time < self.cache_ttl:
                return client_id
        
        try:
            response = self.secrets.get_secret_value(
                SecretId=f'api/keys/{key_hash}'
            )
            client_id = response['SecretString']
            self.cache[key_hash] = (datetime.now(timezone.utc), client_id)
            return client_id
        except self.secrets.exceptions.ResourceNotFoundException:
            return None


class RateLimiter:
    """Token bucket rate limiter per client."""

    def __init__(self, requests_per_minute: int = 100):
        self.rpm = requests_per_minute
        self.buckets = defaultdict(lambda: {
            'tokens': requests_per_minute,
            'last_refill': datetime.now(timezone.utc)
        })

    def allow(self, client_id: str) -> bool:
        """Check if request allowed under rate limit."""
        bucket = self.buckets[client_id]
        now = datetime.now(timezone.utc)
        
        elapsed = (now - bucket['last_refill']).total_seconds()
        refill = int(elapsed * self.rpm / 60)
        
        if refill > 0:
            bucket['tokens'] = min(self.rpm, bucket['tokens'] + refill)
            bucket['last_refill'] = now
        
        if bucket['tokens'] > 0:
            bucket['tokens'] -= 1
            return True
        return False
