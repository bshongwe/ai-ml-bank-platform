"""Populate dim_customer with SCD Type 2 tracking."""
from datetime import datetime, timezone
import pandas as pd
import pyodbc
import os


class DimCustomerETL:
    """Load and maintain customer dimension with SCD Type 2."""

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
        """Load customer data from source system."""
        df = pd.read_parquet(source_path)
        required = ['customer_id', 'customer_name', 'customer_segment',
                    'risk_profile']
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
                SELECT customer_key, customer_segment, risk_profile
                FROM dim_customer
                WHERE customer_id = ? AND is_current = 1
            """, (row['customer_id'],))
            
            existing = cursor.fetchone()

            if existing is None:
                cursor.execute("""
                    INSERT INTO dim_customer (
                        customer_id, customer_name, customer_segment,
                        risk_profile, valid_from, is_current, data_source
                    ) VALUES (?, ?, ?, ?, ?, 1, 'crm_system')
                """, (row['customer_id'], row['customer_name'],
                      row['customer_segment'], row['risk_profile'], now))
            else:
                if (existing[1] != row['customer_segment'] or
                    existing[2] != row['risk_profile']):
                    cursor.execute("""
                        UPDATE dim_customer
                        SET is_current = 0, valid_to = ?, updated_at = ?
                        WHERE customer_key = ?
                    """, (now, now, existing[0]))

                    cursor.execute("""
                        INSERT INTO dim_customer (
                            customer_id, customer_name, customer_segment,
                            risk_profile, valid_from, is_current, data_source
                        ) VALUES (?, ?, ?, ?, ?, 1, 'crm_system')
                    """, (row['customer_id'], row['customer_name'],
                          row['customer_segment'], row['risk_profile'], now))

        conn.commit()
        cursor.close()
        conn.close()


if __name__ == '__main__':
    etl = DimCustomerETL()
    source_df = etl.load_source_data('data/source/customers.parquet')
    etl.apply_scd_type2(source_df)
    print(f"Loaded {len(source_df)} customers with SCD Type 2")
