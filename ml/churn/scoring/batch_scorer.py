"""
Churn Batch Scoring
Weekly scoring for retention campaigns.
"""
import os
import joblib
import pandas as pd
from pathlib import Path
from datetime import datetime

MODEL_PATH = os.getenv(
    'CHURN_MODEL_PATH', 'common/model_registry/churn_latest/model.joblib'
)
MODEL_VERSION = os.getenv('CHURN_MODEL_VERSION', 'churn_v1.2')
INPUT_PATH = os.getenv(
    'CHURN_INPUT', 'lake/silver/churn_features.parquet'
)
OUTPUT_PATH = os.getenv(
    'CHURN_OUTPUT', 'warehouse/fact_churn_scores.parquet'
)

def assign_segment(score: float) -> str:
    """Assign customer segment based on churn probability."""
    if score >= 0.7:
        return 'high_risk'
    elif score >= 0.4:
        return 'medium_risk'
    return 'low_risk'

def score_batch():
    """Score all customers in batch."""
    model = joblib.load(MODEL_PATH)
    df = pd.read_parquet(INPUT_PATH)
    feature_cols = [
        'transaction_decay', 'login_inactivity', 'complaint_frequency'
    ]
    X = df[feature_cols]
    df['churn_probability'] = model.predict_proba(X)[:, 1]
    df['segment'] = df['churn_probability'].apply(assign_segment)
    df['model_version'] = MODEL_VERSION
    df['scored_at'] = datetime.utcnow().isoformat()
    output_cols = [
        'customer_id', 'churn_probability', 'segment',
        'model_version', 'scored_at'
    ]
    df[output_cols].to_parquet(OUTPUT_PATH, index=False)
    print(f"Scored {len(df)} customers to {OUTPUT_PATH}")

if __name__ == '__main__':
    score_batch()
