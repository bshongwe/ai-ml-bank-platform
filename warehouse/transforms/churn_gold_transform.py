"""Silver → Gold transformation for churn cohorts."""
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import pyarrow.parquet as pq
import sys

sys.path.append(str(Path(__file__).parent.parent))
from warehouse.cdc_tracker import CDCTracker

HIGH_RISK_THRESHOLD = 0.7
MEDIUM_RISK_THRESHOLD = 0.4
HIGH_CONFIDENCE_THRESHOLD = 0.8


def validate_silver_data(df: pd.DataFrame) -> dict:
    """Validate Silver layer data quality and return DQ metrics."""
    required = ['customer_id', 'churn_probability', 'confidence', 'event_time']
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    
    dq_metrics = {
        'total_records': len(df),
        'out_of_range': int(((df['churn_probability'] < 0) | 
                            (df['churn_probability'] > 1)).sum()),
        'null_confidence': int(df['confidence'].isnull().sum())
    }
    
    if dq_metrics['out_of_range'] > 0:
        raise ValueError(f"Out of range probabilities: {dq_metrics['out_of_range']}")
    
    return dq_metrics


def assign_risk_segment(prob: float) -> str:
    """Assign risk segment based on churn probability."""
    if prob >= HIGH_RISK_THRESHOLD:
        return 'high_risk'
    elif prob >= MEDIUM_RISK_THRESHOLD:
        return 'medium_risk'
    return 'low_risk'


def aggregate_churn_cohorts(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate to weekly churn cohorts (analytics-safe)."""
    df['week'] = pd.to_datetime(df['event_time']).dt.to_period('W').dt.start_time
    df['risk_segment'] = df['churn_probability'].apply(assign_risk_segment)
    df['is_high_confidence'] = df['confidence'] >= HIGH_CONFIDENCE_THRESHOLD

    agg = df.groupby(['week', 'risk_segment']).agg(
        customer_count=('customer_id', 'nunique'),
        avg_churn_probability=('churn_probability', 'mean'),
        high_confidence_count=('is_high_confidence', 'sum')
    ).reset_index()

    return agg


def transform_churn_to_gold(silver_path: Path, gold_path: Path,
                           incremental: bool = True) -> None:
    """Transform Silver churn scores to Gold cohort metrics."""
    df = pd.read_parquet(silver_path)
    
    if incremental:
        cdc = CDCTracker()
        df = cdc.filter_new_records(df, 'churn_scores', 'event_time')
        if len(df) == 0:
            print("No new records to process")
            return
    
    dq_metrics = validate_silver_data(df)
    gold_df = aggregate_churn_cohorts(df)
    
    if incremental and gold_path.exists():
        existing = pd.read_parquet(gold_path)
        gold_df = pd.concat([existing, gold_df]).drop_duplicates(
            subset=['week', 'risk_segment'], keep='last')
    
    gold_df.to_parquet(gold_path, index=False)
    print(f"Gold churn: {len(gold_df)} records, DQ: {dq_metrics}")


if __name__ == '__main__':
    silver = Path('warehouse/fact_churn_scores.parquet')
    gold = Path('warehouse/agg_churn_cohorts.parquet')
    transform_churn_to_gold(silver, gold)
