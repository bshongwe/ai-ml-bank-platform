"""Generate dim_date for 10 years (2020-2030)."""
from datetime import datetime, timedelta
import pyodbc
import os


class DimDateGenerator:
    """Generate date dimension table."""

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

    def generate_dates(self, start_year: int = 2020,
                       end_year: int = 2030) -> None:
        """Generate date records from start_year to end_year."""
        conn = self._get_connection()
        cursor = conn.cursor()

        start_date = datetime(start_year, 1, 1)
        end_date = datetime(end_year, 12, 31)
        current_date = start_date

        batch = []
        while current_date <= end_date:
            date_key = int(current_date.strftime('%Y%m%d'))
            year = current_date.year
            quarter = (current_date.month - 1) // 3 + 1
            month = current_date.month
            week = current_date.isocalendar()[1]
            day_of_month = current_date.day
            day_of_week = current_date.weekday()
            day_name = current_date.strftime('%A')
            is_weekend = 1 if day_of_week >= 5 else 0
            fiscal_year = year if month >= 7 else year - 1
            fiscal_quarter = ((month - 7) % 12) // 3 + 1

            batch.append((
                date_key, current_date.date(), year, quarter, month, week,
                day_of_month, day_of_week, day_name, is_weekend, 0,
                fiscal_year, fiscal_quarter
            ))

            if len(batch) >= 1000:
                cursor.executemany("""
                    INSERT INTO dim_date (
                        date_key, date, year, quarter, month, week,
                        day_of_month, day_of_week, day_name, is_weekend,
                        is_holiday, fiscal_year, fiscal_quarter
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, batch)
                conn.commit()
                batch = []

            current_date += timedelta(days=1)

        if batch:
            cursor.executemany("""
                INSERT INTO dim_date (
                    date_key, date, year, quarter, month, week,
                    day_of_month, day_of_week, day_name, is_weekend,
                    is_holiday, fiscal_year, fiscal_quarter
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)
            conn.commit()

        cursor.close()
        conn.close()


if __name__ == '__main__':
    generator = DimDateGenerator()
    generator.generate_dates(2020, 2030)
    print("Generated dim_date for 2020-2030")
