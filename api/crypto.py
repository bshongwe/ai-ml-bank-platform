"""
AES-256-GCM encryption for secure API communication.
Per-client encryption keys stored in cloud secrets manager.
"""
import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import json
import boto3
from datetime import datetime, timezone


class SecurePayloadHandler:
    """Handle encrypted API payloads with AES-256-GCM (authenticated encryption)."""

    def __init__(self, encryption_key: bytes):
        if len(encryption_key) != 32:
            raise ValueError("Encryption key must be 32 bytes (AES-256)")
        self.aesgcm = AESGCM(encryption_key)

    def encrypt(self, payload: dict, nonce: str, timestamp: int) -> str:
        """Encrypt JSON payload with nonce and timestamp."""
        envelope = {
            'data': payload,
            'nonce': nonce,
            'timestamp': timestamp
        }
        plaintext = json.dumps(envelope).encode('utf-8')
        
        iv = os.urandom(12)  # GCM uses 96-bit nonce
        ciphertext = self.aesgcm.encrypt(iv, plaintext, None)
        
        return base64.b64encode(iv + ciphertext).decode('utf-8')

    def decrypt(self, encrypted_payload: str) -> tuple:
        """Decrypt and return (payload, nonce, timestamp)."""
        data = base64.b64decode(encrypted_payload)
        
        iv = data[:12]
        ciphertext = data[12:]
        
        plaintext = self.aesgcm.decrypt(iv, ciphertext, None)
        envelope = json.loads(plaintext.decode('utf-8'))
        
        return (
            envelope['data'],
            envelope['nonce'],
            envelope['timestamp']
        )


def get_client_key(client_id: str) -> bytes:
    """Retrieve client encryption key from secrets manager."""
    secrets = boto3.client('secretsmanager')
    response = secrets.get_secret_value(
        SecretId=f'api/client/{client_id}/encryption-key'
    )
    return base64.b64decode(response['SecretString'])
