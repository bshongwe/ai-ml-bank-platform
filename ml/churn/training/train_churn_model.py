"""
Churn Prediction Model Training
Focus: High recall to catch at-risk customers early.
"""
import os
import json
import pandas as pd
import joblib
import hashlib
from pathlib import Path
from typing import NamedTuple
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, recall_score
from datetime import datetime

# Constants
N_ESTIMATORS = 100
RANDOM_STATE = 42
TRAIN_CUTOFF_DATE = '2026-01-01'
THRESHOLD = 0.3

FEATURES_PATH = os.getenv(
    'CHURN_FEATURES_PATH', 'lake/silver/churn_features.parquet'
)
LABELS_PATH = os.getenv('CHURN_LABELS_PATH', 'data/churn_labels.csv')
MODEL_REGISTRY = os.getenv('MODEL_REGISTRY', 'common/model_registry/')
MODEL_VERSION = f"churn_v{datetime.now().strftime('%Y%m%d%H%M%S')}"

class FeatureSet(NamedTuple):
    X_train: pd.DataFrame
    y_train: pd.Series
    X_test: pd.DataFrame
    y_test: pd.Series

def load_and_merge_data():
    features = pd.read_parquet(FEATURES_PATH)
    labels = pd.read_csv(LABELS_PATH)
    return features.merge(
        labels, on='customer_id', how='inner', validate='one_to_one'
    )

def split_train_test(data):
    train = data[data['event_time'] < TRAIN_CUTOFF_DATE]
    test = data[data['event_time'] >= TRAIN_CUTOFF_DATE]
    return train, test

def prepare_features(train, test):
    feature_cols = [
        'transaction_decay', 'login_inactivity', 'complaint_frequency'
    ]
    return FeatureSet(
        X_train=train[feature_cols],
        y_train=train['churned'],
        X_test=test[feature_cols],
        y_test=test['churned']
    )

def train_model(X_train, y_train):
    model = RandomForestClassifier(
        n_estimators=N_ESTIMATORS,
        random_state=RANDOM_STATE,
        class_weight='balanced'
    )
    model.fit(X_train, y_train)
    return model

def evaluate_model(model, X_test, y_test):
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_pred_proba)
    recall = recall_score(y_test, y_pred_proba > THRESHOLD)
    return auc, recall

def save_model_artifacts(model, metrics, feature_schema):
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
    auc, recall = evaluate_model(model, features.X_test, features.y_test)
    metrics = {
        'auc': auc,
        'recall@0.3': recall,
        'train_size': len(train),
        'test_size': len(test)
    }
    save_model_artifacts(model, metrics, feature_schema)
    print(f"Model {MODEL_VERSION} trained. AUC: {auc:.3f}")
