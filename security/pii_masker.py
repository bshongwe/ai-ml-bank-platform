"""
PII Masker
Automated PII detection and masking for Silver layer.
"""
import os
import re
import hashlib
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any

PII_PATTERNS = {
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
    'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
    'credit_card': r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b'
}

PII_COLUMNS = [
    'customer_id', 'account_id', 'email', 'phone',
    'address', 'name', 'ssn'
]

class PIIMasker:
    def __init__(self, hash_salt: str = None):
        self.hash_salt = hash_salt or os.getenv('PII_HASH_SALT', 'default')

    def hash_value(self, value: str) -> str:
        """Hash PII value with salt."""
        if pd.isna(value):
            return value
        combined = f"{value}{self.hash_salt}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    def mask_pattern(self, text: str, pattern: str) -> str:
        """Mask text matching pattern."""
        if pd.isna(text):
            return text
        return re.sub(pattern, '***MASKED***', str(text))

    def mask_column(
        self, df: pd.DataFrame, column: str, method: str = 'hash'
    ) -> pd.DataFrame:
        """Mask a specific column."""
        if column not in df.columns:
            return df
        
        if method == 'hash':
            df[column] = df[column].apply(self.hash_value)
        elif method == 'redact':
            df[column] = '***REDACTED***'
        
        return df

    def detect_and_mask_pii(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect and mask PII in dataframe."""
        masked_df = df.copy()
        
        # Mask known PII columns
        for col in PII_COLUMNS:
            if col in masked_df.columns:
                masked_df = self.mask_column(masked_df, col, method='hash')
        
        # Detect and mask PII patterns in text columns
        text_cols = masked_df.select_dtypes(
            include=['object', 'string']
        ).columns
        
        for col in text_cols:
            for pii_type, pattern in PII_PATTERNS.items():
                masked_df[col] = masked_df[col].apply(
                    lambda x: self.mask_pattern(x, pattern)
                )
        
        return masked_df

    def mask_file(self, input_path: str, output_path: str) -> None:
        """Mask PII in parquet file."""
        df = pd.read_parquet(input_path)
        masked_df = self.detect_and_mask_pii(df)
        masked_df.to_parquet(output_path, index=False)
        print(f"Masked PII: {input_path} -> {output_path}")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Mask PII in data files')
    parser.add_argument('--input', required=True, help='Input file')
    parser.add_argument('--output', required=True, help='Output file')
    args = parser.parse_args()
    
    masker = PIIMasker()
    masker.mask_file(args.input, args.output)
