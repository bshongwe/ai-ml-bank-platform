"""Silver → Gold transformation for credit risk distribution."""
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import pyarrow.parquet as pq
import sys

sys.path.append(str(Path(__file__).parent.parent))
from warehouse.cdc_tracker import CDCTracker


def validate_silver_data(df: pd.DataFrame) -> dict:
    """Validate Silver layer data quality and return DQ metrics."""
    required = ['account_id', 'risk_band', 'score', 'event_time']
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    valid_bands = {'high', 'medium', 'low'}
    
    dq_metrics = {
        'total_records': len(df),
        'invalid_bands': int(~df['risk_band'].isin(valid_bands).sum()),
        'null_scores': int(df['score'].isnull().sum())
    }
    
    if dq_metrics['invalid_bands'] > 0:
        raise ValueError(f"Invalid risk bands: {dq_metrics['invalid_bands']}")
    
    return dq_metrics


def aggregate_risk_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate to daily risk band distribution (analytics-safe)."""
    df['date'] = pd.to_datetime(df['event_time']).dt.date

    agg = df.groupby(['date', 'risk_band']).agg(
        account_count=('account_id', 'nunique'),
        avg_score=('score', 'mean'),
        total_exposure=('score', 'sum')
    ).reset_index()

    return agg


def transform_credit_risk_to_gold(silver_path: Path, gold_path: Path,
                                 incremental: bool = True) -> None:
    """Transform Silver credit risk to Gold distribution metrics."""
    df = pd.read_parquet(silver_path)
    
    if incremental:
        cdc = CDCTracker()
        df = cdc.filter_new_records(df, 'credit_risk', 'event_time')
        if len(df) == 0:
            print("No new records to process")
            return
    
    dq_metrics = validate_silver_data(df)
    gold_df = aggregate_risk_distribution(df)
    
    if incremental and gold_path.exists():
        existing = pd.read_parquet(gold_path)
        gold_df = pd.concat([existing, gold_df]).drop_duplicates(
            subset=['date', 'risk_band'], keep='last')
    
    gold_df.to_parquet(gold_path, index=False)
    print(f"Gold risk: {len(gold_df)} records, DQ: {dq_metrics}")


if __name__ == '__main__':
    silver = Path('warehouse/fact_credit_risk.parquet')
    gold = Path('warehouse/agg_risk_distribution.parquet')
    transform_credit_risk_to_gold(silver, gold)
