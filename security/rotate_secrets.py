#!/usr/bin/env python3
"""
Automated secrets rotation for AWS Secrets Manager
Rotates API encryption keys and database credentials every 90 days
"""
import boto3
import json
import secrets
from datetime import datetime, timedelta, timezone
from base64 import b64encode

secrets_client = boto3.client('secretsmanager')
kms_client = boto3.client('kms')

ROTATION_DAYS = 90
SECRET_PREFIXES = [
    'banking/api/client/',
    'banking/database/',
    'banking/encryption/'
]

def generate_encryption_key():
    """Generate 256-bit encryption key"""
    return b64encode(secrets.token_bytes(32)).decode('utf-8')

def rotate_secret(secret_name: str):
    """Rotate a secret if it's older than ROTATION_DAYS"""
    try:
        response = secrets_client.describe_secret(SecretId=secret_name)
        last_changed = response.get('LastChangedDate')
        
        if not last_changed:
            print(f"⚠️  {secret_name}: No rotation date found")
            return
        
        days_old = (datetime.now(timezone.utc) - last_changed).days
        
        if days_old >= ROTATION_DAYS:
            print(f"🔄 Rotating {secret_name} (age: {days_old} days)")
            
            # Generate new key
            new_key = generate_encryption_key()
            
            # Update secret
            secrets_client.update_secret(
                SecretId=secret_name,
                SecretString=new_key
            )
            
            # Tag with rotation timestamp
            secrets_client.tag_resource(
                SecretId=secret_name,
                Tags=[{
                    'Key': 'LastRotated',
                    'Value': datetime.now(timezone.utc).isoformat()
                }]
            )
            
            print(f"✅ Rotated {secret_name}")
        else:
            print(f"✓ {secret_name}: OK (age: {days_old} days)")
    
    except secrets_client.exceptions.ResourceNotFoundException:
        print(f"❌ {secret_name}: Not found")
    except Exception as e:
        print(f"❌ {secret_name}: Error - {e}")

def list_secrets_by_prefix(prefix: str):
    """List all secrets matching prefix"""
    paginator = secrets_client.get_paginator('list_secrets')
    secrets = []
    
    for page in paginator.paginate():
        for secret in page['SecretList']:
            if secret['Name'].startswith(prefix):
                secrets.append(secret['Name'])
    
    return secrets

def main():
    print("=" * 60)
    print("Banking ML Platform - Secrets Rotation")
    print(f"Rotation threshold: {ROTATION_DAYS} days")
    print("=" * 60)
    print()
    
    all_secrets = []
    for prefix in SECRET_PREFIXES:
        all_secrets.extend(list_secrets_by_prefix(prefix))
    
    if not all_secrets:
        print("No secrets found to rotate")
        return
    
    print(f"Found {len(all_secrets)} secrets to check")
    print()
    
    for secret_name in all_secrets:
        rotate_secret(secret_name)
    
    print()
    print("=" * 60)
    print("Rotation complete")
    print("=" * 60)

if __name__ == '__main__':
    main()
