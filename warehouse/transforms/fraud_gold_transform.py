"""Silver → Gold transformation for fraud metrics."""
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import pyarrow.parquet as pq

FRAUD_THRESHOLD = 0.7
HIGH_RISK_THRESHOLD = 0.85


def validate_silver_data(df: pd.DataFrame) -> None:
    """Validate Silver layer data quality."""
    required = ['transaction_id', 'fraud_score', 'event_time']
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    if df['fraud_score'].isnull().any():
        raise ValueError("Null fraud scores detected")
    if not (0 <= df['fraud_score']).all() or not (df['fraud_score'] <= 1).all():
        raise ValueError("Fraud scores out of range [0,1]")


def aggregate_fraud_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate to hourly fraud metrics (analytics-safe)."""
    df['hour_bucket'] = pd.to_datetime(df['event_time']).dt.floor('H')
    df['is_flagged'] = df['fraud_score'] >= FRAUD_THRESHOLD
    df['is_high_risk'] = df['fraud_score'] >= HIGH_RISK_THRESHOLD

    agg = df.groupby('hour_bucket').agg(
        total_transactions=('transaction_id', 'count'),
        flagged_transactions=('is_flagged', 'sum'),
        high_risk_count=('is_high_risk', 'sum'),
        avg_fraud_score=('fraud_score', 'mean')
    ).reset_index()

    agg['fraud_rate'] = agg['flagged_transactions'] / agg['total_transactions']
    return agg


def transform_fraud_to_gold(silver_path: Path, gold_path: Path) -> None:
    """Transform Silver fraud scores to Gold aggregated metrics."""
    df = pd.read_parquet(silver_path)
    validate_silver_data(df)
    gold_df = aggregate_fraud_metrics(df)
    gold_df.to_parquet(gold_path, index=False)
    print(f"Gold fraud metrics: {len(gold_df)} hourly records")


if __name__ == '__main__':
    silver = Path('lake/silver/fraud_scores.parquet')
    gold = Path('warehouse/agg_fraud_metrics.parquet')
    transform_fraud_to_gold(silver, gold)
