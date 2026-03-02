"""
Field-level encryption using AWS KMS envelope encryption.
Encrypts PII fields in Bronze/Silver/Gold layers.
"""
import base64
import boto3
from typing import Any, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import json


class FieldEncryptor:
    """Encrypt individual fields using KMS envelope encryption."""
    
    ENCRYPTED_PREFIX = "ENC:"
    
    def __init__(self, kms_key_id: str):
        self.kms_key_id = kms_key_id
        self.kms = boto3.client('kms')
        self._data_key_cache = {}
    
    def _get_data_key(self) -> tuple:
        """Get data encryption key from KMS."""
        if 'key' in self._data_key_cache:
            return self._data_key_cache['key']
        
        response = self.kms.generate_data_key(
            KeyId=self.kms_key_id,
            KeySpec='AES_256'
        )
        
        plaintext_key = response['Plaintext']
        encrypted_key = response['CiphertextBlob']
        
        self._data_key_cache['key'] = (plaintext_key, encrypted_key)
        return plaintext_key, encrypted_key
    
    def encrypt_field(self, value: Any) -> str:
        """Encrypt a single field value."""
        if value is None:
            return None
        
        if isinstance(value, str) and value.startswith(self.ENCRYPTED_PREFIX):
            return value
        
        plaintext_key, encrypted_key = self._get_data_key()
        
        aesgcm = AESGCM(plaintext_key)
        nonce = b'\x00' * 12
        
        plaintext = json.dumps(value).encode('utf-8')
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        
        envelope = {
            'encrypted_key': base64.b64encode(encrypted_key).decode('utf-8'),
            'ciphertext': base64.b64encode(ciphertext).decode('utf-8')
        }
        
        return self.ENCRYPTED_PREFIX + base64.b64encode(
            json.dumps(envelope).encode('utf-8')
        ).decode('utf-8')
    
    def decrypt_field(self, encrypted_value: str) -> Any:
        """Decrypt a single field value."""
        if encrypted_value is None:
            return None
        
        if not isinstance(encrypted_value, str):
            return encrypted_value
        
        if not encrypted_value.startswith(self.ENCRYPTED_PREFIX):
            return encrypted_value
        
        envelope_b64 = encrypted_value[len(self.ENCRYPTED_PREFIX):]
        envelope = json.loads(base64.b64decode(envelope_b64))
        
        encrypted_key = base64.b64decode(envelope['encrypted_key'])
        ciphertext = base64.b64decode(envelope['ciphertext'])
        
        response = self.kms.decrypt(CiphertextBlob=encrypted_key)
        plaintext_key = response['Plaintext']
        
        aesgcm = AESGCM(plaintext_key)
        nonce = b'\x00' * 12
        
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return json.loads(plaintext.decode('utf-8'))
    
    def is_encrypted(self, value: Any) -> bool:
        """Check if field is already encrypted."""
        return (
            isinstance(value, str) and 
            value.startswith(self.ENCRYPTED_PREFIX)
        )
