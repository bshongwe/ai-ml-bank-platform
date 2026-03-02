
"""
Airflow DAG: Streaming Fraud Pipeline
Production-grade, event-driven, idempotent, auditable.
Watches S3 Bronze path for new events, validates schema, triggers Silver feature engineering.
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.sensors.s3_key import S3KeySensor
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.utils.dates import days_ago
import json
import logging
import pandas as pd
from jsonschema import validate, ValidationError
import os

BRONZE_BUCKET = 'lake/bronze/payments_raw'
SILVER_PATH = '/Users/ernie-dev/Documents/ai-ml-bank-platform/lake/silver/fraud_features/'
SCHEMA_PATH = '/Users/ernie-dev/Documents/ai-ml-bank-platform/lake/bronze/fraud_bronze_schema.json'

default_args = {
	'owner': 'fraud-ml-platform',
	'depends_on_past': False,
	'retries': 2,
}

def load_schema(schema_path):
	with open(schema_path, 'r') as f:
		return json.load(f)

def validate_bronze_file(file_path, schema):
	df = pd.read_json(file_path, lines=True)
	for idx, record in df.iterrows():
		try:
			validate(instance=record.to_dict(), schema=schema)
		except ValidationError as e:
			logging.error(f"Schema validation failed at row {idx}: {e}")
			raise
	logging.info(f"All records in {file_path} passed schema validation.")

def feature_engineering_bronze_to_silver(file_path, silver_path):
	df = pd.read_json(file_path, lines=True)
	# Example feature engineering (replace with real logic)
	df['tx_velocity_1m'] = 1.0  # TODO: implement real calculation
	df['geo_distance_km'] = 0.0 # TODO: implement real calculation
	df['device_entropy'] = 0.0  # TODO: implement real calculation
	# Save to Silver
	out_path = os.path.join(silver_path, os.path.basename(file_path))
	df.to_parquet(out_path, index=False)
	logging.info(f"Silver features written to {out_path}")

def process_new_bronze_file(**context):
	s3_key = context['task_instance'].xcom_pull(task_ids='wait_for_bronze_file')
	local_path = f"/tmp/{os.path.basename(s3_key)}"
	s3 = S3Hook(aws_conn_id='aws_default')
	s3.get_key(s3_key, bucket_name=BRONZE_BUCKET).download_file(local_path)
	schema = load_schema(SCHEMA_PATH)
	validate_bronze_file(local_path, schema)
	feature_engineering_bronze_to_silver(local_path, SILVER_PATH)

with DAG(
	dag_id='fraud_streaming_pipeline',
	default_args=default_args,
	description='Streaming fraud pipeline: Bronze → Silver → ML',
	schedule_interval=None,  # event-driven
	start_date=days_ago(1),
	catchup=False,
) as dag:
	wait_for_bronze_file = S3KeySensor(
		task_id='wait_for_bronze_file',
		bucket_key='payments_raw/*.json',
		bucket_name=BRONZE_BUCKET,
		aws_conn_id='aws_default',
		wildcard_match=True,
		timeout=60*60*24,
		poke_interval=60,
		mode='poke',
	)

	process_file = PythonOperator(
		task_id='process_new_bronze_file',
		python_callable=process_new_bronze_file,
		provide_context=True,
	)

	wait_for_bronze_file >> process_file
