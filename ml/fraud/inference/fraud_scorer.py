"""
Fraud Inference Service
Online scoring with <100ms latency, fail-open on error.
"""
import os
import json
import joblib
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

MODEL_PATH = os.getenv(
    'FRAUD_MODEL_PATH', 'common/model_registry/fraud_latest/model.joblib'
)
MODEL_VERSION = os.getenv('FRAUD_MODEL_VERSION', 'fraud_v1.0.0')
DECISION_THRESHOLD = 0.85

class FraudScorer:
    def __init__(self):
        self.model = joblib.load(MODEL_PATH)
        self.model_version = MODEL_VERSION

    def score(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Score transaction for fraud risk."""
        try:
            df = pd.DataFrame([features])
            feature_cols = [
                'tx_velocity_1m', 'geo_distance_km', 'device_entropy'
            ]
            X = df[feature_cols]
            fraud_score = float(self.model.predict_proba(X)[0, 1])
            decision = self._make_decision(fraud_score)
            return {
                'transaction_id': features.get('transaction_id'),
                'fraud_score': round(fraud_score, 4),
                'decision': decision,
                'model_version': self.model_version,
                'scored_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                'transaction_id': features.get('transaction_id'),
                'fraud_score': None,
                'decision': 'allow',
                'error': str(e),
                'model_version': self.model_version,
                'scored_at': datetime.utcnow().isoformat()
            }

    def _make_decision(self, score: float) -> str:
        if score >= DECISION_THRESHOLD:
            return 'block'
        elif score >= 0.5:
            return 'challenge'
        return 'allow'

def score_transaction(transaction: Dict[str, Any]) -> Dict[str, Any]:
    """Stateless scoring function."""
    scorer = FraudScorer()
    return scorer.score(transaction)

if __name__ == '__main__':
    sample = {
        'transaction_id': 'test-123',
        'tx_velocity_1m': 5,
        'geo_distance_km': 150.0,
        'device_entropy': 1.2
    }
    result = score_transaction(sample)
    print(json.dumps(result, indent=2))
