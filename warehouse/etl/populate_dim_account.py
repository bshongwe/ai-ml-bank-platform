"""Populate dim_account with SCD Type 2 tracking."""
from datetime import datetime, timezone
import pandas as pd
import pyodbc
import os


class DimAccountETL:
    """Load and maintain account dimension with SCD Type 2."""

    def __init__(self, synapse_server: str = None, database: str = None):
        self.synapse_server = synapse_server or os.getenv('SYNAPSE_SERVER')
        self.database = database or os.getenv('SYNAPSE_DB')

    def _get_connection(self) -> pyodbc.Connection:
        conn_str = (
            f"Driver={{ODBC Driver 18 for SQL Server}};"
            f"Server={self.synapse_server};"
            f"Database={self.database};"
            f"Authentication=ActiveDirectoryInteractive;"
        )
        return pyodbc.connect(conn_str)

    def load_source_data(self, source_path: str) -> pd.DataFrame:
        """Load account data from core banking system."""
        df = pd.read_parquet(source_path)
        required = ['account_id', 'customer_id', 'account_type',
                    'account_status', 'balance']
        if not all(col in df.columns for col in required):
            raise ValueError(f"Missing required columns: {required}")
        return df

    def apply_scd_type2(self, new_df: pd.DataFrame) -> None:
        """Apply SCD Type 2 logic to track changes."""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now(timezone.utc)

        for _, row in new_df.iterrows():
            cursor.execute("""
                SELECT account_key, account_status, balance
                FROM dim_account
                WHERE account_id = ? AND is_current = 1
            """, (row['account_id'],))
            
            existing = cursor.fetchone()

            if existing is None:
                cursor.execute("""
                    INSERT INTO dim_account (
                        account_id, customer_id, account_type,
                        account_status, balance, valid_from, is_current,
                        data_source
                    ) VALUES (?, ?, ?, ?, ?, ?, 1, 'core_banking')
                """, (row['account_id'], row['customer_id'],
                      row['account_type'], row['account_status'],
                      row['balance'], now))
            else:
                if (existing[1] != row['account_status'] or
                    abs(existing[2] - row['balance']) > 0.01):
                    cursor.execute("""
                        UPDATE dim_account
                        SET is_current = 0, valid_to = ?, updated_at = ?
                        WHERE account_key = ?
                    """, (now, now, existing[0]))

                    cursor.execute("""
                        INSERT INTO dim_account (
                            account_id, customer_id, account_type,
                            account_status, balance, valid_from, is_current,
                            data_source
                        ) VALUES (?, ?, ?, ?, ?, ?, 1, 'core_banking')
                    """, (row['account_id'], row['customer_id'],
                          row['account_type'], row['account_status'],
                          row['balance'], now))

        conn.commit()
        cursor.close()
        conn.close()


if __name__ == '__main__':
    etl = DimAccountETL()
    source_df = etl.load_source_data('data/source/accounts.parquet')
    etl.apply_scd_type2(source_df)
    print(f"Loaded {len(source_df)} accounts with SCD Type 2")
