"""
Batch Churn Ingestion Pipeline
Production-grade: reads customer logs, validates, writes to Bronze.
"""

import os
import json
import pandas as pd
from jsonschema import validate, ValidationError
from airflow.models import Variable

# Dynamic path resolution
RAW_LOG_PATH = Variable.get(
	'churn_raw_log_path',
	default_var='/data/churn_raw_logs.json'
)
BRONZE_PATH = Variable.get(
	'churn_bronze_path',
	default_var='/lake/bronze/churn_bronze.json'
)
SCHEMA_PATH = Variable.get(
	'churn_bronze_schema_path',
	default_var='/lake/bronze/churn_bronze_schema.json'
)

def load_schema(schema_path):
	with open(schema_path, 'r') as f:
		return json.load(f)

def validate_and_write_bronze():
	schema = load_schema(SCHEMA_PATH)
	df = pd.read_json(RAW_LOG_PATH, lines=True)
	for idx, record in df.iterrows():
		try:
			validate(instance=record.to_dict(), schema=schema)
		except ValidationError as e:
			print(f"Schema validation failed at row {idx}: {e}")
			raise
	df.to_json(BRONZE_PATH, orient='records', lines=True)
	print(f"Bronze data written to {BRONZE_PATH}")
