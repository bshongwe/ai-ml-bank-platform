"""
Example API client with end-to-end encryption.
"""
import requests
import base64
import os
import secrets
from datetime import datetime, timezone
from api.crypto import SecurePayloadHandler


class BankingAPIClient:
    """Client for secure ML API communication."""

    def __init__(self, api_url: str, api_key: str, encryption_key: bytes):
        self.api_url = api_url
        self.api_key = api_key
        self.handler = SecurePayloadHandler(encryption_key)

    def score_fraud(self, transaction: dict) -> dict:
        """Score transaction for fraud."""
        nonce = secrets.token_urlsafe(32)
        timestamp = int(datetime.now(timezone.utc).timestamp())
        
        encrypted = self.handler.encrypt(transaction, nonce, timestamp)
        
        response = requests.post(
            f"{self.api_url}/v1/fraud/score",
            json={"encrypted_payload": encrypted},
            headers={"X-API-Key": self.api_key},
            timeout=5
        )
        response.raise_for_status()
        
        encrypted_result = response.json()["encrypted_payload"]
        result, _, _ = self.handler.decrypt(encrypted_result)
        return result


if __name__ == "__main__":
    client = BankingAPIClient(
        api_url="https://api.bank.com",
        api_key=os.getenv("API_KEY"),
        encryption_key=base64.b64decode(os.getenv("ENCRYPTION_KEY"))
    )
    
    transaction = {
        "transaction_id": "tx-123",
        "tx_velocity_1m": 5,
        "geo_distance_km": 150.0,
        "device_entropy": 1.2
    }
    result = client.score_fraud(transaction)
    print(f"Fraud: {result['decision']}, score: {result['fraud_score']}")
