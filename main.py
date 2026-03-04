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
    subprocess.run(["streamlit", "run", "streamlit_app.py"])


def run_fraud_pipeline():
    """Execute fraud detection streaming pipeline."""
    from orchestration.fraud_streaming_dag import fraud_streaming_dag
    print("Running fraud detection pipeline...")
    fraud_streaming_dag()


def run_credit_risk_pipeline():
    """Execute credit risk batch pipeline."""
    from orchestration.credit_risk_batch_dag import credit_risk_batch_dag
    print("Running credit risk pipeline...")
    credit_risk_batch_dag()


def run_churn_pipeline():
    """Execute churn prediction batch pipeline."""
    from orchestration.churn_batch_dag import churn_batch_dag
    print("Running churn prediction pipeline...")
    churn_batch_dag()


def run_warehouse_refresh():
    """Execute warehouse refresh (Silver → Gold → Synapse)."""
    from orchestration.warehouse_refresh_dag import warehouse_refresh_dag
    print("Running warehouse refresh...")
    warehouse_refresh_dag()


def train_fraud_model():
    """Train fraud detection model."""
    from ml.fraud.training.train_fraud_model import train_fraud_model as train
    print("Training fraud detection model...")
    train()


def train_credit_risk_model():
    """Train credit risk model."""
    from ml.credit_risk.training.train_credit_risk_model import train_credit_risk_model as train
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
    print("Checking alerts...")
    manager = AlertManager()
    manager.check_all()


def run_warehouse_maintenance():
    """Run warehouse maintenance (stats, indexes, archival)."""
    from warehouse.maintenance import WarehouseMaintenance
    print("Running warehouse maintenance...")
    maintenance = WarehouseMaintenance()
    maintenance.run_all()


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
    
    try:
        if args.command == "dashboard":
            start_dashboard()
        
        elif args.command == "api":
            start_api_server(args.host, args.port)
        
        elif args.command == "pipeline":
            if args.pipeline_type == "fraud":
                run_fraud_pipeline()
            elif args.pipeline_type == "credit-risk":
                run_credit_risk_pipeline()
            elif args.pipeline_type == "churn":
                run_churn_pipeline()
            elif args.pipeline_type == "warehouse":
                run_warehouse_refresh()
        
        elif args.command == "train":
            if args.model_type == "fraud":
                train_fraud_model()
            elif args.model_type == "credit-risk":
                train_credit_risk_model()
            elif args.model_type == "churn":
                train_churn_model()
        
        elif args.command == "monitor":
            if args.monitor_type == "metrics":
                collect_metrics()
            elif args.monitor_type == "alerts":
                check_alerts()
        
        elif args.command == "ops":
            if args.ops_type == "maintenance":
                run_warehouse_maintenance()
            elif args.ops_type == "cost-report":
                generate_cost_report()
        
        print("✓ Command completed successfully")
    
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
