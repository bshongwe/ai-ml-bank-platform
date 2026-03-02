
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
from pathlib import Path
from math import radians, cos, sin, asin, sqrt
import json
import logging
import pandas as pd
import numpy as np
from jsonschema import validate, ValidationError
from scipy.stats import entropy
import os

BRONZE_BUCKET = 'lake/bronze/payments_raw'
SILVER_PATH = 'lake/silver/fraud_features/'
SCHEMA_PATH = 'lake/bronze/fraud_bronze_schema.json'

# Constants
EARTH_RADIUS_KM = 6371
SECONDS_PER_DAY = 86400
ROLLING_WINDOW_SIZE = 5

default_args = {
	'owner': 'fraud-ml-platform',
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

def haversine(lat1, lon1, lat2, lon2):
	"""Calculate haversine distance between two points."""
	lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
	dlon = lon2 - lon1
	dlat = lat2 - lat1
	a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
	c = 2 * asin(sqrt(a))
	return c * EARTH_RADIUS_KM

def extract_lat_lon(payload):
	"""Extract latitude and longitude from payload."""
	try:
		return (
			payload.get('latitude', np.nan),
			payload.get('longitude', np.nan)
		)
	except (AttributeError, TypeError):
		return np.nan, np.nan

def rolling_entropy(series):
	"""Calculate entropy of a series."""
	value_counts = series.value_counts(normalize=True)
	return entropy(value_counts, base=2)

def compute_tx_velocity(df):
	"""Compute transaction velocity per customer."""
	df['event_time'] = pd.to_datetime(df['event_time'])
	df['tx_velocity_1m'] = (
		df.groupby('customer_id')['event_time']
		.transform(lambda x: x.rolling('1min', on=x).count())
	)
	return df

def compute_geo_distance(df):
	"""Compute geographic distance between transactions."""
	df[['latitude', 'longitude']] = df['payload'].apply(
		lambda p: pd.Series(extract_lat_lon(p))
	)
	df[['prev_latitude', 'prev_longitude']] = (
		df.groupby('customer_id')[['latitude', 'longitude']].shift(1)
	)
	df['geo_distance_km'] = df.apply(
		lambda row: haversine(
			row['prev_latitude'], row['prev_longitude'],
			row['latitude'], row['longitude']
		) if not pd.isnull(row['prev_latitude']) and
		not pd.isnull(row['latitude']) else 0.0,
		axis=1
	)
	return df

def compute_device_entropy(df):
	"""Compute device entropy in rolling window."""
	df['device_entropy'] = (
		df.groupby('customer_id')['payload']
		.transform(lambda x: x.rolling(
			window=ROLLING_WINDOW_SIZE, min_periods=1
		).apply(
			lambda w: rolling_entropy(
				pd.Series([p.get('device_id', '') for p in w])
			), raw=False
		))
	)
	return df

def feature_engineering_bronze_to_silver(file_path, silver_path):
	"""Transform bronze data to silver features."""
	df = pd.read_json(file_path, lines=True)
	df = df.sort_values(['customer_id', 'event_time'])

	df = compute_tx_velocity(df)
	df = compute_geo_distance(df)
	df = compute_device_entropy(df)

	# Save to Silver
	safe_silver_path = Path(silver_path).resolve()
	if not safe_silver_path.is_dir():
		raise ValueError(f"Invalid silver path: {silver_path}")
	base_name = os.path.basename(file_path).replace('.json', '.parquet')
	out_path = safe_silver_path / base_name
	df.to_parquet(out_path, index=False)
	logging.info("Silver features written to %s", out_path)

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
		timeout=SECONDS_PER_DAY,
		poke_interval=60,
		mode='poke',
	)

	process_file = PythonOperator(
		task_id='process_new_bronze_file',
		python_callable=process_new_bronze_file,
		provide_context=True,
	)

	wait_for_bronze_file >> process_file
