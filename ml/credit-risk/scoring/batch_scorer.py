"""
Credit Risk Batch Scoring
Monthly scoring with risk band assignment.
"""
import os
import joblib
import pandas as pd
from pathlib import Path
from datetime import datetime

MODEL_PATH = os.getenv(
    'RISK_MODEL_PATH', 'common/model_registry/risk_latest/model.joblib'
)
MODEL_VERSION = os.getenv('RISK_MODEL_VERSION', 'risk_v2.1')
INPUT_PATH = os.getenv(
    'RISK_INPUT', 'lake/silver/credit_risk_features.parquet'
)
OUTPUT_PATH = os.getenv(
    'RISK_OUTPUT', 'warehouse/fact_credit_risk.parquet'
)

def assign_risk_band(score: float) -> str:
    """Assign risk band based on PD score."""
    if score >= 0.5:
        return 'high'
    elif score >= 0.2:
        return 'medium'
    return 'low'

def score_batch():
    """Score all accounts in batch."""
    model = joblib.load(MODEL_PATH)
    df = pd.read_parquet(INPUT_PATH)
    feature_cols = [
        'repayment_history', 'balance_volatility', 'delinquency_trends'
    ]
    X = df[feature_cols]
    df['pd_score'] = model.predict_proba(X)[:, 1]
    df['risk_band'] = df['pd_score'].apply(assign_risk_band)
    df['model_version'] = MODEL_VERSION
    df['scored_at'] = datetime.utcnow().isoformat()
    output_cols = [
        'account_id', 'pd_score', 'risk_band',
        'model_version', 'scored_at'
    ]
    df[output_cols].to_parquet(OUTPUT_PATH, index=False)
    print(f"Scored {len(df)} accounts to {OUTPUT_PATH}")

if __name__ == '__main__':
    score_batch()
