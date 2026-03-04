"""
Hybrid AI/ML Banking Platform - Main Entry Point
Orchestrates fraud detection, credit risk, and churn prediction across AWS/GCP/Azure.

NOTE: This entry point is for development, testing, and CI/CD.
Production deployments should use:
- API: Kubernetes/ECS with load balancer
- Pipelines: Airflow scheduler
- Training: Orchestrated batch jobs
- Monitoring: Automated cron/CloudWatch Events
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))


AIRFLOW_NOTE = "NOTE: Airflow DAGs should be triggered via Airflow scheduler."
DIRECT_EXEC_NOTE = "Executing pipeline tasks directly..."


def start_api_server(host: str = "127.0.0.1", port: int = 8000):
    """Start FastAPI ML inference server (dev/test only)."""
    import uvicorn
    from api.main import app
    
    env = os.getenv('ENVIRONMENT', 'dev')
    if env == 'production':
        print("WARNING: Direct uvicorn not recommended for production.")
        print("Use Kubernetes/ECS with gunicorn/uvicorn workers instead.")
        response = input("Continue anyway? (yes/no): ")
        if response.lower() != 'yes':
            sys.exit(1)
    
    print(f"Starting ML API server on {host}:{port} [env={env}]")
    uvicorn.run(app, host=host, port=port)


def start_dashboard():
    """Start Streamlit dashboard (dev only)."""
    import subprocess
    
    env = os.getenv('ENVIRONMENT', 'dev')
    if env == 'production':
        print("ERROR: Streamlit dashboard is for development only.")
        print("Use proper monitoring tools in production (Grafana, CloudWatch, etc.)")
        sys.exit(1)
    
    print("Starting Streamlit dashboard...")
    result = subprocess.run(["streamlit", "run", "streamlit_app.py"])
    sys.exit(result.returncode)


def run_fraud_pipeline():
    """Execute fraud detection streaming pipeline."""
    print("Running fraud detection pipeline...")
    print(AIRFLOW_NOTE)
    print(DIRECT_EXEC_NOTE)
    from orchestration.fraud_streaming_dag import process_new_bronze_file
    process_new_bronze_file()


def run_credit_risk_pipeline():
    """Execute credit risk batch pipeline."""
    print("Running credit risk pipeline...")
    print(AIRFLOW_NOTE)
    print(DIRECT_EXEC_NOTE)
    from orchestration.credit_risk_batch_dag import process_credit_risk_batch
    process_credit_risk_batch()


def run_churn_pipeline():
    """Execute churn prediction batch pipeline."""
    print("Running churn prediction pipeline...")
    print(AIRFLOW_NOTE)
    print(DIRECT_EXEC_NOTE)
    from orchestration.churn_batch_dag import process_churn_batch
    process_churn_batch()


def run_warehouse_refresh():
    """Execute warehouse refresh (Silver → Gold → Synapse)."""
    print("Running warehouse refresh...")
    print(AIRFLOW_NOTE)
    print(DIRECT_EXEC_NOTE)
    from orchestration.warehouse_refresh_dag import refresh_warehouse
    refresh_warehouse()


def train_fraud_model():
    """Train fraud detection model."""
    from ml.fraud.training.train_fraud_model import train_fraud_model as train
    print("Training fraud detection model...")
    train()


def train_credit_risk_model():
    """Train credit risk model."""
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent / 'ml' / 'credit-risk'))
    from training.train_credit_risk_model import train_credit_risk_model as train
    print("Training credit risk model...")
    train()


def train_churn_model():
    """Train churn prediction model."""
    from ml.churn.training.train_churn_model import train_churn_model as train
    print("Training churn prediction model...")
    train()


def collect_metrics():
    """Collect platform metrics."""
    from monitoring.metrics_collector import MetricsCollector
    print("Collecting platform metrics...")
    collector = MetricsCollector()
    collector.collect_all()


def check_alerts():
    """Check and process alerts."""
    from monitoring.alert_manager import AlertManager
    from monitoring.metrics_collector import MetricsCollector
    print("Checking alerts...")
    collector = MetricsCollector()
    metrics = collector.collect_all()
    manager = AlertManager()
    manager.process_alerts(metrics)


def run_warehouse_maintenance():
    """Run warehouse maintenance (stats, indexes, archival)."""
    from warehouse.maintenance import WarehouseMaintenance
    print("Running warehouse maintenance...")
    synapse_server = os.getenv('SYNAPSE_SERVER')
    database = os.getenv('SYNAPSE_DB')
    if not synapse_server or not database:
        raise ValueError("SYNAPSE_SERVER and SYNAPSE_DB environment variables required")
    maintenance = WarehouseMaintenance(synapse_server, database)
    maintenance.vacuum_all_tables()


def generate_cost_report():
    """Generate cost analysis report."""
    from cost.cost_reporter import CostReporter
    print("Generating cost report...")
    reporter = CostReporter()
    reporter.generate_report()


def main():
    parser = argparse.ArgumentParser(
        description="Hybrid AI/ML Banking Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py dashboard              # Start Streamlit dashboard (dev UI)
  python main.py api                    # Start ML API server
  python main.py pipeline fraud         # Run fraud detection pipeline
  python main.py pipeline credit-risk   # Run credit risk pipeline
  python main.py pipeline churn         # Run churn prediction pipeline
  python main.py pipeline warehouse     # Refresh analytics warehouse
  python main.py train fraud            # Train fraud model
  python main.py train credit-risk      # Train credit risk model
  python main.py train churn            # Train churn model
  python main.py monitor metrics        # Collect metrics
  python main.py monitor alerts         # Check alerts
  python main.py ops maintenance        # Run warehouse maintenance
  python main.py ops cost-report        # Generate cost report
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Dashboard
    subparsers.add_parser("dashboard", help="Start Streamlit dashboard (dev only)")
    
    # API server
    api_parser = subparsers.add_parser("api", help="Start ML API server")
    api_parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    api_parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    
    # Pipelines
    pipeline_parser = subparsers.add_parser("pipeline", help="Run data pipeline")
    pipeline_parser.add_argument(
        "pipeline_type",
        choices=["fraud", "credit-risk", "churn", "warehouse"],
        help="Pipeline to execute"
    )
    
    # Model training
    train_parser = subparsers.add_parser("train", help="Train ML model")
    train_parser.add_argument(
        "model_type",
        choices=["fraud", "credit-risk", "churn"],
        help="Model to train"
    )
    
    # Monitoring
    monitor_parser = subparsers.add_parser("monitor", help="Monitoring operations")
    monitor_parser.add_argument(
        "monitor_type",
        choices=["metrics", "alerts"],
        help="Monitoring operation"
    )
    
    # Operations
    ops_parser = subparsers.add_parser("ops", help="Operational tasks")
    ops_parser.add_argument(
        "ops_type",
        choices=["maintenance", "cost-report"],
        help="Operational task"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    env = os.getenv('ENVIRONMENT', 'dev')
    print(f"Environment: {env}")
    
    # Command dispatch table
    dispatch = {
        "dashboard": lambda: start_dashboard(),
        "api": lambda: start_api_server(args.host, args.port),
        "pipeline": lambda: {
            "fraud": run_fraud_pipeline,
            "credit-risk": run_credit_risk_pipeline,
            "churn": run_churn_pipeline,
            "warehouse": run_warehouse_refresh,
        }[args.pipeline_type](),
        "train": lambda: {
            "fraud": train_fraud_model,
            "credit-risk": train_credit_risk_model,
            "churn": train_churn_model,
        }[args.model_type](),
        "monitor": lambda: {
            "metrics": collect_metrics,
            "alerts": check_alerts,
        }[args.monitor_type](),
        "ops": lambda: {
            "maintenance": run_warehouse_maintenance,
            "cost-report": generate_cost_report,
        }[args.ops_type](),
    }
    
    try:
        dispatch[args.command]()
        print("✓ Command completed successfully")
    
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
