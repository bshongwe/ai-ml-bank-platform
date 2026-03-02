"""Warehouse maintenance tasks for Synapse Analytics."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pyodbc
from azure.identity import DefaultAzureCredential
import os


class WarehouseMaintenance:
    """Optimize and vacuum Synapse warehouse tables."""

    def __init__(self, synapse_server: str, database: str):
        self.synapse_server = synapse_server
        self.database = database

    def _get_connection(self) -> pyodbc.Connection:
        """Get Synapse connection."""
        conn_str = (
            f"Driver={{ODBC Driver 18 for SQL Server}};"
            f"Server={self.synapse_server};"
            f"Database={self.database};"
            f"Authentication=ActiveDirectoryInteractive;"
        )
        return pyodbc.connect(conn_str)

    def update_statistics(self, table_name: str) -> None:
        """Update table statistics for query optimization."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(f"UPDATE STATISTICS {table_name}")
        conn.commit()
        print(f"Updated statistics for {table_name}")
        cursor.close()
        conn.close()

    def rebuild_indexes(self, table_name: str) -> None:
        """Rebuild table indexes for performance."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(f"ALTER INDEX ALL ON {table_name} REBUILD")
        conn.commit()
        print(f"Rebuilt indexes for {table_name}")
        cursor.close()
        conn.close()

    def archive_old_partitions(self, table_name: str, days: int = 90) -> None:
        """Archive old partitions to reduce query scan size."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).date()
        archive_sql = f"""
        ALTER TABLE {table_name}
        SWITCH PARTITION $PARTITION.pf_{table_name}('{cutoff}')
        TO {table_name}_archive
        """
        try:
            cursor.execute(archive_sql)
            conn.commit()
            print(f"Archived {table_name} partitions older than {cutoff}")
        except pyodbc.Error as e:
            if 'does not exist' in str(e):
                print(f"No partitions to archive for {table_name}")
            else:
                raise
        cursor.close()
        conn.close()

    def vacuum_all_tables(self) -> None:
        """Run maintenance on all Gold layer tables."""
        tables = ['agg_fraud_metrics', 'agg_risk_distribution',
                  'agg_churn_cohorts']
        for table in tables:
            self.update_statistics(table)
            self.rebuild_indexes(table)
            self.archive_old_partitions(table)


if __name__ == '__main__':
    maint = WarehouseMaintenance(
        synapse_server=os.getenv('SYNAPSE_SERVER'),
        database=os.getenv('SYNAPSE_DB')
    )
    maint.vacuum_all_tables()
