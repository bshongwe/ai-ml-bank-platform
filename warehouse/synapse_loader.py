"""Azure Synapse warehouse loader."""
from pathlib import Path
from datetime import datetime, timezone
import os
import json
import pyodbc
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient


class SynapseLoader:
    """Load Gold layer data into Azure Synapse Analytics."""

    def __init__(self, synapse_server: str, database: str, storage_account: str,
                 log_path: Path = Path('warehouse/load_stats.jsonl')):
        self.synapse_server = synapse_server
        self.database = database
        self.storage_account = storage_account
        self.log_path = log_path
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

    def _log_load_stats(self, table_name: str, rows_loaded: int,
                        load_type: str, duration_sec: float) -> None:
        """Log load statistics for audit and monitoring."""
        stats = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'table': table_name,
            'rows_loaded': rows_loaded,
            'load_type': load_type,
            'duration_sec': round(duration_sec, 2),
            'database': self.database
        }
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(stats) + '\n')

    def load_table(self, parquet_path: Path, table_name: str,
                   container: str, load_type: str = 'incremental') -> None:
        """Load parquet into Synapse table."""
        start_time = datetime.now(timezone.utc)
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

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        self._log_load_stats(table_name, count, load_type, duration)
        print(f"Loaded {table_name}: {count} rows in {duration:.2f}s")

        cursor.close()
        conn.close()

    def create_partitions(self, table_name: str, partition_col: str,
                          partition_scheme: str = 'DAILY') -> None:
        """Create table partitions for query performance."""
        conn = self._get_connection()
        cursor = conn.cursor()

        if partition_scheme == 'DAILY':
            partition_sql = f"""
            CREATE PARTITION FUNCTION pf_{table_name} (DATE)
            AS RANGE RIGHT FOR VALUES (
                DATEADD(DAY, -30, CAST(GETDATE() AS DATE)),
                DATEADD(DAY, -7, CAST(GETDATE() AS DATE)),
                CAST(GETDATE() AS DATE)
            )
            """
        elif partition_scheme == 'WEEKLY':
            partition_sql = f"""
            CREATE PARTITION FUNCTION pf_{table_name} (DATE)
            AS RANGE RIGHT FOR VALUES (
                DATEADD(WEEK, -12, CAST(GETDATE() AS DATE)),
                DATEADD(WEEK, -4, CAST(GETDATE() AS DATE)),
                CAST(GETDATE() AS DATE)
            )
            """
        else:
            raise ValueError(f"Unsupported partition scheme: {partition_scheme}")

        try:
            cursor.execute(partition_sql)
            cursor.execute(f"""
                CREATE PARTITION SCHEME ps_{table_name}
                AS PARTITION pf_{table_name}
                ALL TO ([PRIMARY])
            """)
            conn.commit()
            print(f"Created {partition_scheme} partitions for {table_name}")
        except pyodbc.Error as e:
            if 'already exists' in str(e):
                print(f"Partitions already exist for {table_name}")
            else:
                raise

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
