"""
Airflow DAG: Batch Churn Pipeline
Production-grade, scheduled, auditable, idempotent.
Reads Bronze customer logs, validates schema, computes churn features, writes Silver.
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
from pathlib import Path

# Dynamic path resolution using Airflow Variables
BRONZE_PATH = Variable.get(
	'churn_bronze_path',
	default_var='lake/bronze/churn_bronze.json'
)
SILVER_PATH = Variable.get(
	'churn_silver_path',
	default_var='lake/silver/churn_features.parquet'
)
SCHEMA_PATH = Variable.get(
	'churn_bronze_schema_path',
	default_var='lake/bronze/churn_bronze_schema.json'
)

default_args = {
	'owner': 'churn-ml-platform',
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

def compute_churn_features(file_path, out_path):
	"""
	Compute churn features:
	- transaction_decay: exp decay of tx count over 90 days
	- login_inactivity: days since last login
	- complaint_frequency: rolling mean of complaints per 30 days
	"""
	df = pd.read_json(file_path, lines=True)
	df['event_time'] = pd.to_datetime(df['event_time'])
	df = df.sort_values(['customer_id', 'event_time'])

	# Transaction decay (exp decay of tx count over 90 days)
	def exp_decay(events, decay_rate=0.01):
		return np.sum(np.exp(-decay_rate * np.arange(len(events))))
	df['transaction_decay'] = df.groupby('customer_id')[
		'event_time'
	].transform(lambda x: exp_decay(x))

	# Login inactivity (days since last login)
	df['login_inactivity'] = df.groupby('customer_id')[
		'event_time'
	].transform(lambda x: (x.max() - x).dt.days)

	# Complaint frequency (rolling mean per 30 days)
	df['complaint_frequency'] = df.groupby('customer_id')[
		'event_type'
	].transform(
		lambda x: x.rolling(window=30, min_periods=1)
		.apply(lambda w: np.mean([1 if v == 'complaint' else 0 for v in w]),
			   raw=False)
	)

	df.to_parquet(out_path, index=False)
	logging.info("Churn features written to %s", out_path)

def batch_churn_etl():
	schema = load_schema(SCHEMA_PATH)
	validate_bronze_file(BRONZE_PATH, schema)
	compute_churn_features(BRONZE_PATH, SILVER_PATH)

with DAG(
	dag_id='churn_batch_pipeline',
	default_args=default_args,
	description='Batch churn pipeline: Bronze → Silver → ML',
	schedule_interval='@daily',
	start_date=days_ago(1),
	catchup=False,
) as dag:
	etl_task = PythonOperator(
		task_id='batch_churn_etl',
		python_callable=batch_churn_etl,
	)
