"""Silver → Gold transformation for fraud metrics."""
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import pyarrow.parquet as pq
import sys

sys.path.append(str(Path(__file__).parent.parent))
from warehouse.cdc_tracker import CDCTracker

FRAUD_THRESHOLD = 0.7
HIGH_RISK_THRESHOLD = 0.85


def validate_silver_data(df: pd.DataFrame) -> dict:
    """Validate Silver layer data quality and return DQ metrics."""
    required = ['transaction_id', 'fraud_score', 'event_time']
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    
    dq_metrics = {
        'total_records': len(df),
        'null_scores': int(df['fraud_score'].isnull().sum()),
        'out_of_range': int(((df['fraud_score'] < 0) | 
                            (df['fraud_score'] > 1)).sum()),
        'null_pct': round(df['fraud_score'].isnull().mean() * 100, 2)
    }
    
    if dq_metrics['null_scores'] > 0:
        raise ValueError(f"Null fraud scores: {dq_metrics['null_scores']}")
    if dq_metrics['out_of_range'] > 0:
        raise ValueError(f"Out of range scores: {dq_metrics['out_of_range']}")
    
    return dq_metrics


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
    agg['created_at'] = datetime.now(timezone.utc)
    agg['updated_at'] = datetime.now(timezone.utc)
    return agg


def transform_fraud_to_gold(silver_path: Path, gold_path: Path,
                           incremental: bool = True) -> None:
    """Transform Silver fraud scores to Gold aggregated metrics."""
    df = pd.read_parquet(silver_path)
    
    if incremental:
        cdc = CDCTracker()
        df = cdc.filter_new_records(df, 'fraud_scores', 'event_time')
        if len(df) == 0:
            print("No new records to process")
            return
    
    dq_metrics = validate_silver_data(df)
    gold_df = aggregate_fraud_metrics(df)
    
    if incremental and gold_path.exists():
        existing = pd.read_parquet(gold_path)
        gold_df = pd.concat([existing, gold_df])
        gold_df = gold_df.sort_values('updated_at', ascending=False)
        gold_df = gold_df.drop_duplicates(subset=['hour_bucket'], keep='first')
    
    gold_df.to_parquet(gold_path, index=False)
    print(f"Gold fraud: {len(gold_df)} records, DQ: {dq_metrics}")


if __name__ == '__main__':
    silver = Path('lake/silver/fraud_scores.parquet')
    gold = Path('warehouse/agg_fraud_metrics.parquet')
    transform_fraud_to_gold(silver, gold)
