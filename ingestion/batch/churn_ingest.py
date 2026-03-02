"""
Batch Churn Ingestion Pipeline
Production-grade: reads customer logs, validates, writes to Bronze.
"""

import os
import json
import logging
import pandas as pd
from jsonschema import validate, ValidationError
from airflow.models import Variable
from pathlib import Path

# Dynamic path resolution
RAW_LOG_PATH = Variable.get(
	'churn_raw_log_path',
	default_var='data/churn_raw_logs.json'
)
BRONZE_PATH = Variable.get(
	'churn_bronze_path',
	default_var='lake/bronze/churn_bronze.json'
)
SCHEMA_PATH = Variable.get(
	'churn_bronze_schema_path',
	default_var='lake/bronze/churn_bronze_schema.json'
)

def load_schema(schema_path):
	safe_path = Path(schema_path).resolve()
	if not safe_path.is_file():
		raise ValueError(f"Invalid schema path: {schema_path}")
	with open(safe_path, 'r', encoding='utf-8') as f:
		return json.load(f)

def validate_and_write_bronze():
	schema = load_schema(SCHEMA_PATH)
	safe_raw_path = Path(RAW_LOG_PATH).resolve()
	if not safe_raw_path.is_file():
		raise ValueError(f"Invalid raw log path: {RAW_LOG_PATH}")
	df = pd.read_json(safe_raw_path, lines=True)
	for idx, record in df.iterrows():
		try:
			validate(instance=record.to_dict(), schema=schema)
		except ValidationError as e:
			logging.error(
				"Schema validation failed at row %s: %s", idx, e
			)
			raise
	df.to_json(BRONZE_PATH, orient='records', lines=True)
	logging.info("Bronze data written to %s", BRONZE_PATH)
