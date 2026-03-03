"""Automated partition management for Synapse tables."""
from datetime import datetime, timedelta, timezone
import pyodbc
import os


class PartitionManager:
    """Manage sliding window partitions automatically."""

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

    def create_future_partitions(self, table_name: str,
                                 months_ahead: int = 3) -> None:
        """Create partitions for next N months."""
        conn = self._get_connection()
        cursor = conn.cursor()

        for i in range(1, months_ahead + 1):
            future_date = datetime.now(timezone.utc) + timedelta(days=30 * i)
            partition_value = future_date.replace(day=1).strftime('%Y-%m-01')

            try:
                cursor.execute(f"""
                    ALTER PARTITION FUNCTION pf_{table_name}()
                    SPLIT RANGE ('{partition_value}')
                """)
                conn.commit()
                print(f"Created partition for {partition_value}")
            except pyodbc.Error as e:
                if 'already exists' in str(e):
                    continue
                raise

        cursor.close()
        conn.close()

    def archive_old_partitions(self, table_name: str,
                               months_old: int = 3) -> None:
        """Archive partitions older than N months."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cutoff = (datetime.now(timezone.utc) -
                  timedelta(days=30 * months_old)).replace(day=1)

        try:
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name}_archive
                LIKE {table_name}
            """)

            cursor.execute(f"""
                ALTER TABLE {table_name}
                SWITCH PARTITION $PARTITION.pf_{table_name}('{cutoff}')
                TO {table_name}_archive
            """)
            conn.commit()
            print(f"Archived {table_name} partition {cutoff}")
        except pyodbc.Error as e:
            if 'does not exist' in str(e):
                print(f"No partition to archive for {cutoff}")
            else:
                raise

        cursor.close()
        conn.close()

    def maintain_all_tables(self) -> None:
        """Run partition maintenance on all tables."""
        tables = ['fact_fraud_scores', 'fact_credit_risk', 'fact_churn',
                  'agg_fraud_metrics', 'agg_risk_distribution',
                  'agg_churn_cohorts']
        
        for table in tables:
            print(f"Maintaining partitions for {table}")
            self.create_future_partitions(table, months_ahead=3)
            self.archive_old_partitions(table, months_old=3)


if __name__ == '__main__':
    manager = PartitionManager()
    manager.maintain_all_tables()
