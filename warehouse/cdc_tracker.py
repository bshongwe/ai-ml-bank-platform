"""Change Data Capture for incremental Gold layer loads."""
from datetime import datetime, timezone
import pandas as pd
import pyodbc
import os


class CDCTracker:
    """Track processed records using database control table."""

    def __init__(self, synapse_server: str = None, database: str = None):
        self.synapse_server = synapse_server or os.getenv('SYNAPSE_SERVER')
        self.database = database or os.getenv('SYNAPSE_DB')

    def _get_connection(self) -> pyodbc.Connection:
        """Get Synapse connection."""
        conn_str = (
            f"Driver={{ODBC Driver 18 for SQL Server}};"
            f"Server={self.synapse_server};"
            f"Database={self.database};"
            f"Authentication=ActiveDirectoryInteractive;"
        )
        return pyodbc.connect(conn_str)

    def get_last_processed(self, table: str) -> str:
        """Get last processed timestamp from control table."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT last_processed_timestamp FROM cdc_control "
            "WHERE table_name = ?",
            (table,)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            return row[0].isoformat()
        return '1970-01-01T00:00:00Z'

    def update_processed(self, table: str, timestamp: str,
                        rows_processed: int) -> None:
        """Update last processed timestamp atomically."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            MERGE cdc_control AS target
            USING (SELECT ? AS table_name, ? AS ts, ? AS rows) AS source
            ON target.table_name = source.table_name
            WHEN MATCHED THEN
                UPDATE SET
                    last_processed_timestamp = source.ts,
                    rows_processed = target.rows_processed + source.rows,
                    updated_at = GETUTCDATE()
            WHEN NOT MATCHED THEN
                INSERT (table_name, last_processed_timestamp, rows_processed)
                VALUES (source.table_name, source.ts, source.rows);
        """, (table, timestamp, rows_processed))
        conn.commit()
        cursor.close()
        conn.close()

    def filter_new_records(self, df: pd.DataFrame, table: str,
                          time_col: str) -> pd.DataFrame:
        """Filter to only new records since last load."""
        last_ts = pd.to_datetime(self.get_last_processed(table), utc=True)
        df[time_col] = pd.to_datetime(df[time_col], utc=True)
        df_sorted = df.sort_values(time_col)
        new_df = df_sorted[df_sorted[time_col] > last_ts].copy()
        if len(new_df) > 0:
            max_ts = new_df[time_col].max().isoformat()
            self.update_processed(table, max_ts, len(new_df))
        return new_df
