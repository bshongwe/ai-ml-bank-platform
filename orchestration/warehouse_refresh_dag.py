"""Airflow DAG for Gold layer warehouse refresh."""
from datetime import datetime, timedelta
from pathlib import Path
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
import sys

sys.path.append(str(Path(__file__).parent.parent))

from warehouse.transforms.fraud_gold_transform import transform_fraud_to_gold
from warehouse.transforms.credit_risk_gold_transform import (
    transform_credit_risk_to_gold)
from warehouse.transforms.churn_gold_transform import transform_churn_to_gold
from warehouse.synapse_loader import SynapseLoader
from warehouse.maintenance import WarehouseMaintenance
import os

default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'warehouse_refresh',
    default_args=default_args,
    description='Silver → Gold → Synapse warehouse refresh',
    schedule_interval='0 */6 * * *',
    start_date=days_ago(1),
    catchup=False,
    tags=['gold', 'warehouse', 'analytics'],
)


def transform_fraud_gold(**context):
    """Transform fraud to Gold layer."""
    silver = Path('lake/silver/fraud_scores.parquet')
    gold = Path('warehouse/agg_fraud_metrics.parquet')
    transform_fraud_to_gold(silver, gold)


def transform_credit_risk_gold(**context):
    """Transform credit risk to Gold layer."""
    silver = Path('warehouse/fact_credit_risk.parquet')
    gold = Path('warehouse/agg_risk_distribution.parquet')
    transform_credit_risk_to_gold(silver, gold)


def transform_churn_gold(**context):
    """Transform churn to Gold layer."""
    silver = Path('warehouse/fact_churn_scores.parquet')
    gold = Path('warehouse/agg_churn_cohorts.parquet')
    transform_churn_to_gold(silver, gold)


def load_to_synapse(**context):
    """Load Gold parquet to Synapse warehouse."""
    loader = SynapseLoader(
        synapse_server=os.getenv('SYNAPSE_SERVER'),
        database=os.getenv('SYNAPSE_DB'),
        storage_account=os.getenv('AZURE_STORAGE_ACCOUNT')
    )

    loader.create_partitions('agg_fraud_metrics', 'hour_bucket', 'DAILY')
    loader.create_partitions('agg_risk_distribution', 'date', 'DAILY')
    loader.create_partitions('agg_churn_cohorts', 'week', 'WEEKLY')

    loader.load_table(
        Path('warehouse/agg_fraud_metrics.parquet'),
        'agg_fraud_metrics',
        'gold-layer',
        load_type='incremental'
    )
    loader.load_table(
        Path('warehouse/agg_risk_distribution.parquet'),
        'agg_risk_distribution',
        'gold-layer',
        load_type='full'
    )
    loader.load_table(
        Path('warehouse/agg_churn_cohorts.parquet'),
        'agg_churn_cohorts',
        'gold-layer',
        load_type='incremental'
    )


def vacuum_warehouse(**context):
    """Run warehouse maintenance tasks."""
    maint = WarehouseMaintenance(
        synapse_server=os.getenv('SYNAPSE_SERVER'),
        database=os.getenv('SYNAPSE_DB')
    )
    maint.vacuum_all_tables()


fraud_transform = PythonOperator(
    task_id='transform_fraud_gold',
    python_callable=transform_fraud_gold,
    dag=dag,
)

credit_transform = PythonOperator(
    task_id='transform_credit_risk_gold',
    python_callable=transform_credit_risk_gold,
    dag=dag,
)

churn_transform = PythonOperator(
    task_id='transform_churn_gold',
    python_callable=transform_churn_gold,
    dag=dag,
)

synapse_load = PythonOperator(
    task_id='load_to_synapse',
    python_callable=load_to_synapse,
    dag=dag,
)

vacuum_task = PythonOperator(
    task_id='vacuum_warehouse',
    python_callable=vacuum_warehouse,
    dag=dag,
)

[fraud_transform, credit_transform, churn_transform] >> synapse_load >> vacuum_task
