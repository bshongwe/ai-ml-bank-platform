"""
Encryption migration utilities.
Supports gradual rollout and rollback of field-level encryption.
"""
from pathlib import Path
import pandas as pd
import yaml
from typing import List, Dict
from security.field_encryption import FieldEncryptor


class EncryptionMigration:
    """Migrate data to encrypted format with rollback support."""
    
    def __init__(self, config_path: str = 'security/encryption_config.yaml'):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.encryptors = {
            'bronze': FieldEncryptor(self.config['kms_keys']['bronze']),
            'silver': FieldEncryptor(self.config['kms_keys']['silver']),
            'gold': FieldEncryptor(self.config['kms_keys']['gold'])
        }
    
    def get_pii_fields(self, layer: str, dataset: str) -> List[str]:
        """Get list of PII fields for layer/dataset."""
        field_key = f'{layer}_pii_fields'
        return self.config.get(field_key, {}).get(dataset, [])
    
    def encrypt_dataframe(self, df: pd.DataFrame, layer: str, 
                         dataset: str) -> pd.DataFrame:
        """Encrypt PII fields in dataframe."""
        if not self.config['encryption_enabled'].get(layer, False):
            return df
        
        pii_fields = self.get_pii_fields(layer, dataset)
        encryptor = self.encryptors[layer]
        
        df_encrypted = df.copy()
        for field in pii_fields:
            if field in df_encrypted.columns:
                df_encrypted[field] = df_encrypted[field].apply(
                    encryptor.encrypt_field
                )
        
        return df_encrypted
    
    def decrypt_dataframe(self, df: pd.DataFrame, layer: str,
                         dataset: str) -> pd.DataFrame:
        """Decrypt PII fields in dataframe (auto-detects encrypted fields)."""
        pii_fields = self.get_pii_fields(layer, dataset)
        encryptor = self.encryptors[layer]
        
        df_decrypted = df.copy()
        for field in pii_fields:
            if field in df_decrypted.columns:
                df_decrypted[field] = df_decrypted[field].apply(
                    encryptor.decrypt_field
                )
        
        return df_decrypted
    
    def migrate_file(self, input_path: Path, output_path: Path,
                    layer: str, dataset: str) -> Dict:
        """Migrate single parquet file to encrypted format."""
        df = pd.read_parquet(input_path)
        
        original_count = len(df)
        encrypted_df = self.encrypt_dataframe(df, layer, dataset)
        
        encrypted_df.to_parquet(output_path, index=False)
        
        return {
            'input': str(input_path),
            'output': str(output_path),
            'records': original_count,
            'encrypted_fields': self.get_pii_fields(layer, dataset)
        }
    
    def rollback_file(self, encrypted_path: Path, output_path: Path,
                     layer: str, dataset: str) -> Dict:
        """Rollback encrypted file to plaintext."""
        df = pd.read_parquet(encrypted_path)
        
        decrypted_df = self.decrypt_dataframe(df, layer, dataset)
        
        decrypted_df.to_parquet(output_path, index=False)
        
        return {
            'input': str(encrypted_path),
            'output': str(output_path),
            'records': len(df),
            'decrypted_fields': self.get_pii_fields(layer, dataset)
        }
    
    def get_encryption_coverage(self, df: pd.DataFrame, layer: str,
                                dataset: str) -> Dict:
        """Calculate encryption coverage percentage."""
        pii_fields = self.get_pii_fields(layer, dataset)
        encryptor = self.encryptors[layer]
        
        coverage = {}
        for field in pii_fields:
            if field in df.columns:
                encrypted_count = df[field].apply(
                    encryptor.is_encrypted
                ).sum()
                total_count = len(df)
                coverage[field] = {
                    'encrypted': int(encrypted_count),
                    'total': total_count,
                    'percentage': round(encrypted_count / total_count * 100, 2)
                }
        
        return coverage


if __name__ == '__main__':
    migration = EncryptionMigration()
    
    # Example: Migrate Bronze fraud data
    result = migration.migrate_file(
        input_path=Path('lake/bronze/fraud_raw.parquet'),
        output_path=Path('lake/bronze/fraud_raw_encrypted.parquet'),
        layer='bronze',
        dataset='fraud'
    )
    print(f"Migration complete: {result}")
