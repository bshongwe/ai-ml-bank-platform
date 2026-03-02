
"""
Airflow DAG: Batch Credit Risk Pipeline
Production-grade, scheduled, auditable, idempotent.
Reads Bronze account/repayment data, validates schema, computes risk features, writes Silver.
"""


from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from airflow.models import Variable
import json
import logging
import pandas as pd
from jsonschema import validate, ValidationError
import os
import numpy as np
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from security.encryption_migration import EncryptionMigration

# Constants
REPAYMENT_HISTORY_WINDOW = 12
BALANCE_VOLATILITY_DAYS = 90
DELINQUENCY_WINDOW = 12

# Encryption support
encryption_migration = EncryptionMigration()

# Dynamic path resolution using Airflow Variables
BRONZE_PATH = Variable.get(
	'credit_risk_bronze_path',
	default_var='lake/bronze/credit_risk_bronze.json'
)
SILVER_PATH = Variable.get(
	'credit_risk_silver_path',
	default_var='lake/silver/credit_risk_features.parquet'
)
SCHEMA_PATH = Variable.get(
	'credit_risk_bronze_schema_path',
	default_var='lake/bronze/credit_risk_bronze_schema.json'
)

default_args = {
	'owner': 'credit-risk-ml-platform',
	'depends_on_past': False,
	'retries': 2,
}

def load_schema(schema_path):
	safe_path = Path(schema_path).resolve()
	if not safe_path.is_file():
		raise ValueError(f"Invalid schema path: {schema_path}")
	with open(safe_path, 'r', encoding='utf-8') as f:
		return json.load(f)

def validate_bronze_file(file_path, schema):
	safe_path = Path(file_path).resolve()
	if not safe_path.is_file():
		raise ValueError(f"Invalid file path: {file_path}")
	df = pd.read_json(safe_path, lines=True)
	for idx, record in df.iterrows():
		try:
			validate(instance=record.to_dict(), schema=schema)
		except ValidationError as e:
			logging.error(
				"Schema validation failed at row %s: %s", idx, e
			)
			raise
	logging.info(
		"All records in %s passed schema validation.", file_path
	)

def compute_credit_risk_features(file_path, out_path):
	"""
	Compute risk features with encryption support:
	- repayment_history: last 12 repayment statuses
	- balance_volatility: stddev of balance over last 90 days
	- delinquency_trends: rolling mean of missed payments
	"""
	df = pd.read_json(file_path, lines=True)
	
	# Decrypt PII fields if encrypted (auto-detects)
	df = encryption_migration.decrypt_dataframe(df, 'bronze', 'credit_risk')
	
	df['snapshot_date'] = pd.to_datetime(df['snapshot_date'])
	df = df.sort_values(['account_id', 'snapshot_date'])

	# Repayment history (last 12)
	df['repayment_history'] = df.groupby('account_id')[
		'repayment_status'
	].transform(
		lambda x: x.rolling(
			window=REPAYMENT_HISTORY_WINDOW, min_periods=1
		).apply(lambda w: list(w), raw=False)
	)

	# Balance volatility (stddev over last 90 days)
	df['balance_volatility'] = df.groupby('account_id')[
		'balance'
	].transform(
		lambda x: x.rolling(
			f'{BALANCE_VOLATILITY_DAYS}D', on=df['snapshot_date']
		).std()
	)

	# Delinquency trends (rolling mean of missed payments)
	df['delinquency_trends'] = df.groupby('account_id')[
		'repayment_status'
	].transform(
		lambda x: x.rolling(
			window=DELINQUENCY_WINDOW, min_periods=1
		).apply(
			lambda w: np.mean(
				[1 if v == 'missed' else 0 for v in w]
			),
			raw=False
		)
	)
	
	# Encrypt PII fields for Silver layer (if enabled in config)
	df = encryption_migration.encrypt_dataframe(df, 'silver', 'credit_risk')

	df.to_parquet(out_path, index=False)
	logging.info("Credit risk features written to %s", out_path)

def batch_credit_risk_etl():
	schema = load_schema(SCHEMA_PATH)
	validate_bronze_file(BRONZE_PATH, schema)
	compute_credit_risk_features(BRONZE_PATH, SILVER_PATH)

with DAG(
	dag_id='credit_risk_batch_pipeline',
	default_args=default_args,
	description='Batch credit risk pipeline: Bronze → Silver → ML',
	schedule_interval='@daily',
	start_date=days_ago(1),
	catchup=False,
) as dag:
	etl_task = PythonOperator(
		task_id='batch_credit_risk_etl',
		python_callable=batch_credit_risk_etl,
	)
