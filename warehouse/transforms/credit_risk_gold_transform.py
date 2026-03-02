"""Silver → Gold transformation for credit risk distribution."""
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import pyarrow.parquet as pq


def validate_silver_data(df: pd.DataFrame) -> None:
    """Validate Silver layer data quality."""
    required = ['account_id', 'risk_band', 'score', 'event_time']
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    valid_bands = {'high', 'medium', 'low'}
    if not df['risk_band'].isin(valid_bands).all():
        raise ValueError(f"Invalid risk bands, expected {valid_bands}")


def aggregate_risk_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate to daily risk band distribution (analytics-safe)."""
    df['date'] = pd.to_datetime(df['event_time']).dt.date

    agg = df.groupby(['date', 'risk_band']).agg(
        account_count=('account_id', 'nunique'),
        avg_score=('score', 'mean'),
        total_exposure=('score', 'sum')
    ).reset_index()

    return agg


def transform_credit_risk_to_gold(silver_path: Path, gold_path: Path) -> None:
    """Transform Silver credit risk to Gold distribution metrics."""
    df = pd.read_parquet(silver_path)
    validate_silver_data(df)
    gold_df = aggregate_risk_distribution(df)
    gold_df.to_parquet(gold_path, index=False)
    print(f"Gold risk distribution: {len(gold_df)} daily band records")


if __name__ == '__main__':
    silver = Path('warehouse/fact_credit_risk.parquet')
    gold = Path('warehouse/agg_risk_distribution.parquet')
    transform_credit_risk_to_gold(silver, gold)
