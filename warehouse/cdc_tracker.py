"""Change Data Capture for incremental Gold layer loads."""
from pathlib import Path
from datetime import datetime, timezone
import json
import pandas as pd


class CDCTracker:
    """Track processed records for incremental loads."""

    def __init__(self, state_path: Path = Path('warehouse/cdc_state.json')):
        self.state_path = state_path
        self.state = self._load_state()

    def _load_state(self) -> dict:
        """Load CDC state from disk."""
        if self.state_path.exists():
            with open(self.state_path, 'r') as f:
                return json.load(f)
        return {}

    def _save_state(self) -> None:
        """Persist CDC state to disk."""
        with open(self.state_path, 'w') as f:
            json.dump(self.state, f, indent=2)

    def get_last_processed(self, table: str) -> str:
        """Get last processed timestamp for table."""
        return self.state.get(table, '1970-01-01T00:00:00Z')

    def update_processed(self, table: str, timestamp: str) -> None:
        """Update last processed timestamp."""
        self.state[table] = timestamp
        self._save_state()

    def filter_new_records(self, df: pd.DataFrame, table: str,
                          time_col: str) -> pd.DataFrame:
        """Filter to only new records since last load."""
        last_ts = self.get_last_processed(table)
        df[time_col] = pd.to_datetime(df[time_col])
        new_df = df[df[time_col] > last_ts].copy()
        if len(new_df) > 0:
            max_ts = new_df[time_col].max().isoformat()
            self.update_processed(table, max_ts)
        return new_df
