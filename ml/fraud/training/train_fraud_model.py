"""
Fraud Model Training Script
Production-grade: time-split validation, feature schema hash, metrics, lineage.
"""
import os
import json
import pandas as pd
import numpy as np
import joblib
import hashlib
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, precision_score
from datetime import datetime

from typing import NamedTuple

# Constants
N_ESTIMATORS = 100
RANDOM_STATE = 42
MIN_SAMPLES_LEAF = 1
MAX_FEATURES = 'sqrt'
TRAIN_CUTOFF_DATE = '2026-01-01'
THRESHOLD = 0.5

FEATURES_PATH = os.getenv(
    'FRAUD_FEATURES_PATH',
    'lake/silver/fraud_features.parquet'
)
LABELS_PATH = os.getenv('FRAUD_LABELS_PATH', 'data/fraud_labels.csv')
MODEL_REGISTRY = os.getenv(
    'MODEL_REGISTRY',
    'common/model_registry/'
)
MODEL_VERSION = f"fraud_v{datetime.now().strftime('%Y%m%d%H%M%S')}"

def load_and_merge_data():
    """Load features and labels, merge on transaction_id."""
    features = pd.read_parquet(FEATURES_PATH)
    labels = pd.read_csv(LABELS_PATH)
    return features.merge(
        labels,
        on='transaction_id',
        how='inner',
        validate='one_to_one'
    )

def split_train_test(data):
    """Split data by time to prevent leakage."""
    train = data[data['event_time'] < TRAIN_CUTOFF_DATE]
    test = data[data['event_time'] >= TRAIN_CUTOFF_DATE]
    return train, test

class FeatureSet(NamedTuple):
    """Container for train/test features and labels."""
    X_train: pd.DataFrame
    y_train: pd.Series
    X_test: pd.DataFrame
    y_test: pd.Series

def prepare_features(train, test):
    """Extract feature columns and labels."""
    feature_cols = ['tx_velocity_1m', 'geo_distance_km', 'device_entropy']
    return FeatureSet(
        X_train=train[feature_cols],
        y_train=train['is_fraud'],
        X_test=test[feature_cols],
        y_test=test['is_fraud']
    )

def compute_feature_schema_hash(X_train):
    """Compute hash of feature schema."""
    feature_schema = str(list(X_train.columns))
    return hashlib.sha256(feature_schema.encode()).hexdigest()

def train_model(X_train, y_train):
    """Train RandomForest classifier."""
    model = RandomForestClassifier(
        n_estimators=N_ESTIMATORS,
        random_state=RANDOM_STATE,
        min_samples_leaf=MIN_SAMPLES_LEAF,
        max_features=MAX_FEATURES
    )
    model.fit(X_train, y_train)
    return model

def evaluate_model(model, X_test, y_test):
    """Evaluate model and return metrics."""
    y_pred = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred > THRESHOLD)
    return auc, precision

def save_model_artifacts(model, metrics, feature_schema, train):
    """Save model, metrics, and metadata."""
    model_path = Path(MODEL_REGISTRY) / MODEL_VERSION
    model_path.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, model_path / 'model.joblib')

    with open(model_path / 'metrics.json', 'w', encoding='utf-8') as f:
        json.dump(metrics, f)

    with open(
        model_path / 'feature_schema.txt', 'w', encoding='utf-8'
    ) as f:
        f.write(feature_schema)

    fingerprint = hashlib.sha256(
        train.to_csv(index=False).encode()
    ).hexdigest()
    with open(
        model_path / 'training_dataset_fingerprint.txt',
        'w',
        encoding='utf-8'
    ) as f:
        f.write(fingerprint)

if __name__ == '__main__':
    data = load_and_merge_data()
    train, test = split_train_test(data)
    features = prepare_features(train, test)

    feature_schema = str(list(features.X_train.columns))
    feature_schema_hash = compute_feature_schema_hash(features.X_train)

    model = train_model(features.X_train, features.y_train)
    auc, precision = evaluate_model(
        model, features.X_test, features.y_test
    )

    metrics = {
        'auc': auc,
        'precision@0.5': precision,
        'feature_schema_hash': feature_schema_hash,
        'train_size': len(train),
        'test_size': len(test)
    }

    save_model_artifacts(model, metrics, feature_schema, train)
    print(f"Model {MODEL_VERSION} trained and registered.")
