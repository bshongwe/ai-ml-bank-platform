"""Azure Synapse warehouse loader."""
from pathlib import Path
from datetime import datetime, timezone
import os
import pyodbc
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient


class SynapseLoader:
    """Load Gold layer data into Azure Synapse Analytics."""

    def __init__(self, synapse_server: str, database: str, storage_account: str):
        self.synapse_server = synapse_server
        self.database = database
        self.storage_account = storage_account
        self.credential = DefaultAzureCredential()
        self.blob_client = BlobServiceClient(
            account_url=f"https://{storage_account}.blob.core.windows.net",
            credential=self.credential
        )

    def _get_connection(self) -> pyodbc.Connection:
        """Get Synapse connection using Azure AD auth."""
        conn_str = (
            f"Driver={{ODBC Driver 18 for SQL Server}};"
            f"Server={self.synapse_server};"
            f"Database={self.database};"
            f"Authentication=ActiveDirectoryInteractive;"
        )
        return pyodbc.connect(conn_str)

    def _upload_to_blob(self, local_path: Path, container: str) -> str:
        """Upload parquet to Azure Blob Storage."""
        blob_name = f"gold/{local_path.name}"
        blob_client = self.blob_client.get_blob_client(
            container=container, blob=blob_name)
        with open(local_path, 'rb') as data:
            blob_client.upload_blob(data, overwrite=True)
        return f"https://{self.storage_account}.blob.core.windows.net/" \
               f"{container}/{blob_name}"

    def load_table(self, parquet_path: Path, table_name: str,
                   container: str, load_type: str = 'incremental') -> None:
        """Load parquet into Synapse table."""
        blob_url = self._upload_to_blob(parquet_path, container)

        conn = self._get_connection()
        cursor = conn.cursor()

        if load_type == 'full':
            cursor.execute(f"TRUNCATE TABLE {table_name}")

        copy_sql = f"""
        COPY INTO {table_name}
        FROM '{blob_url}'
        WITH (
            FILE_TYPE = 'PARQUET',
            CREDENTIAL = (IDENTITY = 'Managed Identity')
        )
        """
        cursor.execute(copy_sql)
        conn.commit()

        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"Loaded {table_name}: {count} rows")

        cursor.close()
        conn.close()

    def create_partitions(self, table_name: str, partition_col: str) -> None:
        """Create table partitions for performance."""
        conn = self._get_connection()
        cursor = conn.cursor()

        partition_sql = f"""
        ALTER TABLE {table_name}
        SWITCH PARTITION $PARTITION.{partition_col}(GETDATE())
        TO {table_name}_staging PARTITION $PARTITION.{partition_col}(GETDATE())
        """
        cursor.execute(partition_sql)
        conn.commit()

        cursor.close()
        conn.close()


if __name__ == '__main__':
    loader = SynapseLoader(
        synapse_server=os.getenv('SYNAPSE_SERVER', 'bank-synapse.sql.azure.com'),
        database=os.getenv('SYNAPSE_DB', 'analytics_warehouse'),
        storage_account=os.getenv('AZURE_STORAGE_ACCOUNT', 'bankdatalake')
    )

    loader.load_table(
        Path('warehouse/agg_fraud_metrics.parquet'),
        'agg_fraud_metrics',
        'gold-layer',
        load_type='incremental'
    )
    loader.load_table(
        Path('warehouse/agg_risk_distribution.parquet'),
        'agg_risk_distribution',
        'gold-layer',
        load_type='full'
    )
    loader.load_table(
        Path('warehouse/agg_churn_cohorts.parquet'),
        'agg_churn_cohorts',
        'gold-layer',
        load_type='incremental'
    )
