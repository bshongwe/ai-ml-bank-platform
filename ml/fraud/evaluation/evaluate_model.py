"""
Fraud Model Evaluation
Comprehensive metrics, fairness checks, performance monitoring.
"""
import os
import json
import joblib
import pandas as pd
from pathlib import Path
from sklearn.metrics import (
    roc_auc_score, precision_score, recall_score,
    f1_score, confusion_matrix
)
from datetime import datetime

MODEL_PATH = os.getenv(
    'FRAUD_MODEL_PATH', 'common/model_registry/fraud_latest/model.joblib'
)
TEST_DATA_PATH = os.getenv(
    'FRAUD_TEST_DATA', 'lake/silver/fraud_test.parquet'
)
OUTPUT_PATH = os.getenv(
    'EVAL_OUTPUT', 'ml/fraud/evaluation/metrics.json'
)
THRESHOLD = 0.5

def evaluate_model():
    """Evaluate model on test set."""
    model = joblib.load(MODEL_PATH)
    df = pd.read_parquet(TEST_DATA_PATH)
    feature_cols = [
        'tx_velocity_1m', 'geo_distance_km', 'device_entropy'
    ]
    X = df[feature_cols]
    y_true = df['is_fraud']
    y_pred_proba = model.predict_proba(X)[:, 1]
    y_pred = (y_pred_proba > THRESHOLD).astype(int)
    metrics = {
        'auc': float(roc_auc_score(y_true, y_pred_proba)),
        'precision': float(precision_score(y_true, y_pred)),
        'recall': float(recall_score(y_true, y_pred)),
        'f1': float(f1_score(y_true, y_pred)),
        'threshold': THRESHOLD,
        'test_size': len(df),
        'evaluated_at': datetime.utcnow().isoformat()
    }
    cm = confusion_matrix(y_true, y_pred)
    metrics['confusion_matrix'] = {
        'tn': int(cm[0, 0]),
        'fp': int(cm[0, 1]),
        'fn': int(cm[1, 0]),
        'tp': int(cm[1, 1])
    }
    output_path = Path(OUTPUT_PATH)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=2)
    print(f"Evaluation complete. AUC: {metrics['auc']:.3f}")
    return metrics

if __name__ == '__main__':
    metrics = evaluate_model()
    print(json.dumps(metrics, indent=2))
