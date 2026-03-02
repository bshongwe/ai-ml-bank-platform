
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
	import numpy as np
	from scipy.stats import entropy
	from math import radians, cos, sin, asin, sqrt

	df = pd.read_json(file_path, lines=True)
	df = df.sort_values(['customer_id', 'event_time'])

	# --- tx_velocity_1m: count of transactions per customer in the last 1 minute ---
	df['event_time'] = pd.to_datetime(df['event_time'])
	df['tx_velocity_1m'] = (
		df.groupby('customer_id')['event_time']
		.transform(lambda x: x.rolling('1min', on=x).count())
	)

	# --- geo_distance_km: haversine distance between consecutive transactions ---
	def haversine(lat1, lon1, lat2, lon2):
		# convert decimal degrees to radians
		lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
		dlon = lon2 - lon1
		dlat = lat2 - lat1
		a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
		c = 2 * asin(sqrt(a))
		r = 6371  # Radius of earth in kilometers
		return c * r

	# Assume columns 'latitude' and 'longitude' exist in payload
	def extract_lat_lon(payload):
		try:
			return payload.get('latitude', np.nan), payload.get('longitude', np.nan)
		except Exception:
			return np.nan, np.nan
	df[['latitude', 'longitude']] = df['payload'].apply(lambda p: pd.Series(extract_lat_lon(p)))
	df[['prev_latitude', 'prev_longitude']] = (
		df.groupby('customer_id')[['latitude', 'longitude']].shift(1)
	)
	df['geo_distance_km'] = df.apply(
		lambda row: haversine(row['prev_latitude'], row['prev_longitude'], row['latitude'], row['longitude'])
		if not pd.isnull(row['prev_latitude']) and not pd.isnull(row['latitude']) else 0.0,
		axis=1
	)

	# --- device_entropy: entropy of device IDs in a rolling 5-min window ---
	def rolling_entropy(series):
		value_counts = series.value_counts(normalize=True)
		return entropy(value_counts, base=2)
	df['device_entropy'] = (
		df.groupby('customer_id')['payload']
		.transform(lambda x: x.rolling(window=5, min_periods=1).apply(
			lambda w: rolling_entropy(pd.Series([p.get('device_id', '') for p in w])), raw=False))
	)

	# Save to Silver
	out_path = os.path.join(silver_path, os.path.basename(file_path).replace('.json', '.parquet'))
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
