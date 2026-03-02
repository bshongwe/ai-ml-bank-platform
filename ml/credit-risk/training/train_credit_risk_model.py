"""
Credit Risk Model Training
Regulator-focused: explainability, stability, audit trail.
"""
import os
import json
import pandas as pd
import numpy as np
import joblib
import hashlib
from pathlib import Path
from typing import NamedTuple
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, classification_report
from datetime import datetime

# Constants
N_ESTIMATORS = 50
MAX_DEPTH = 10
MAX_FEATURES = 'sqrt'
RANDOM_STATE = 42
TRAIN_CUTOFF_DATE = '2026-01-01'

FEATURES_PATH = os.getenv(
    'CREDIT_RISK_FEATURES_PATH',
    'lake/silver/credit_risk_features.parquet'
)
LABELS_PATH = os.getenv(
    'CREDIT_RISK_LABELS_PATH',
    'data/credit_risk_labels.csv'
)
MODEL_REGISTRY = os.getenv('MODEL_REGISTRY', 'common/model_registry/')
MODEL_VERSION = f"risk_v{datetime.now().strftime('%Y%m%d%H%M%S')}"

class FeatureSet(NamedTuple):
    X_train: pd.DataFrame
    y_train: pd.Series
    X_test: pd.DataFrame
    y_test: pd.Series

def load_and_merge_data():
    features = pd.read_parquet(FEATURES_PATH)
    labels = pd.read_csv(LABELS_PATH)
    return features.merge(
        labels, on='account_id', how='inner', validate='one_to_one'
    )

def split_train_test(data):
    train = data[data['snapshot_date'] < TRAIN_CUTOFF_DATE]
    test = data[data['snapshot_date'] >= TRAIN_CUTOFF_DATE]
    return train, test

def prepare_features(train, test):
    feature_cols = [
        'repayment_history', 'balance_volatility', 'delinquency_trends'
    ]
    return FeatureSet(
        X_train=train[feature_cols],
        y_train=train['is_default'],
        X_test=test[feature_cols],
        y_test=test['is_default']
    )

def train_model(X_train, y_train):
    model = RandomForestClassifier(
        n_estimators=N_ESTIMATORS,
        max_depth=MAX_DEPTH,
        max_features=MAX_FEATURES,
        random_state=RANDOM_STATE,
        min_samples_leaf=50
    )
    model.fit(X_train, y_train)
    return model

def evaluate_model(model, X_test, y_test):
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_pred_proba)
    return auc

def save_model_artifacts(model, metrics, feature_schema, train):
    model_path = Path(MODEL_REGISTRY) / MODEL_VERSION
    model_path.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path / 'model.joblib')
    with open(model_path / 'metrics.json', 'w', encoding='utf-8') as f:
        json.dump(metrics, f)
    with open(
        model_path / 'feature_schema.txt', 'w', encoding='utf-8'
    ) as f:
        f.write(feature_schema)

if __name__ == '__main__':
    data = load_and_merge_data()
    train, test = split_train_test(data)
    features = prepare_features(train, test)
    feature_schema = str(list(features.X_train.columns))
    model = train_model(features.X_train, features.y_train)
    auc = evaluate_model(model, features.X_test, features.y_test)
    metrics = {
        'auc': auc,
        'train_size': len(train),
        'test_size': len(test)
    }
    save_model_artifacts(model, metrics, feature_schema, train)
    print(f"Model {MODEL_VERSION} trained. AUC: {auc:.3f}")
