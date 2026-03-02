"""
Drift Detection
Monitor feature distribution and prediction drift.
"""
import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, Tuple

DRIFT_THRESHOLD = 0.05

class DriftDetector:
    def __init__(self, reference_data: pd.DataFrame):
        self.reference_data = reference_data
        self.reference_stats = self._compute_stats(reference_data)

    def _compute_stats(self, data: pd.DataFrame) -> Dict:
        """Compute reference statistics."""
        return {
            col: {
                'mean': data[col].mean(),
                'std': data[col].std(),
                'min': data[col].min(),
                'max': data[col].max()
            }
            for col in data.columns
        }

    def detect_drift(
        self, current_data: pd.DataFrame
    ) -> Tuple[bool, Dict]:
        """Detect drift using KS test."""
        drift_detected = False
        drift_report = {}
        for col in self.reference_data.columns:
            if col in current_data.columns:
                statistic, p_value = stats.ks_2samp(
                    self.reference_data[col].dropna(),
                    current_data[col].dropna()
                )
                has_drift = p_value < DRIFT_THRESHOLD
                drift_report[col] = {
                    'p_value': float(p_value),
                    'statistic': float(statistic),
                    'drift_detected': has_drift
                }
                if has_drift:
                    drift_detected = True
        return drift_detected, drift_report

    def check_prediction_drift(
        self, reference_preds: np.ndarray, current_preds: np.ndarray
    ) -> Tuple[bool, Dict]:
        """Check for prediction distribution drift."""
        statistic, p_value = stats.ks_2samp(reference_preds, current_preds)
        has_drift = p_value < DRIFT_THRESHOLD
        return has_drift, {
            'p_value': float(p_value),
            'statistic': float(statistic),
            'drift_detected': has_drift
        }

if __name__ == '__main__':
    ref_data = pd.DataFrame({
        'feature1': np.random.normal(0, 1, 1000),
        'feature2': np.random.normal(5, 2, 1000)
    })
    detector = DriftDetector(ref_data)
    current_data = pd.DataFrame({
        'feature1': np.random.normal(0.5, 1, 1000),
        'feature2': np.random.normal(5, 2, 1000)
    })
    drift_detected, report = detector.detect_drift(current_data)
    print(f"Drift detected: {drift_detected}")
    for col, metrics in report.items():
        print(f"  {col}: p={metrics['p_value']:.4f}")
