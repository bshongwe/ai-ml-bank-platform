"""
Streamlit Dashboard - Development Environment
Interactive UI for platform operations, monitoring, and testing.

Usage: streamlit run streamlit_app.py
"""
import streamlit as st
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.append(str(Path(__file__).parent))

st.set_page_config(
    page_title="Banking ML Platform",
    page_icon="🏦",
    layout="wide"
)

st.title("🏦 Hybrid AI/ML Banking Platform")
st.caption("Development Dashboard - Not for production use")

# Environment check
env = os.getenv('ENVIRONMENT', 'dev')
if env == 'production':
    st.error("⚠️ This Streamlit dashboard is for development only. Use proper orchestration in production.")
    st.stop()

st.success(f"Environment: {env}")

# Sidebar navigation
page = st.sidebar.selectbox(
    "Navigation",
    ["🏠 Overview", "🚀 Pipelines", "🤖 ML Training", "📊 Monitoring", "⚙️ Operations", "🧪 API Testing"]
)

# Overview Page
if page == "🏠 Overview":
    st.header("Platform Overview")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("ML Models", "3", help="Fraud, Credit Risk, Churn")
        st.metric("Cloud Providers", "3", help="AWS, GCP, Azure")
    
    with col2:
        st.metric("Lakehouse Layers", "3", help="Bronze → Silver → Gold")
        st.metric("Active DAGs", "4", help="Fraud, Credit, Churn, Warehouse")
    
    with col3:
        st.metric("Total Files", "126+", help="Production-ready modules")
        st.metric("Security Controls", "3", help="PII, Keys, Audit")
    
    st.subheader("Quick Actions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Refresh Warehouse", use_container_width=True):
            with st.spinner("Running warehouse refresh..."):
                try:
                    from orchestration.warehouse_refresh_dag import refresh_warehouse
                    refresh_warehouse()
                    st.success("✓ Warehouse refresh completed")
                except Exception as e:
                    st.error(f"✗ Error: {e}")
    
    with col2:
        if st.button("📈 Collect Metrics", use_container_width=True):
            with st.spinner("Collecting metrics..."):
                try:
                    from monitoring.metrics_collector import MetricsCollector
                    collector = MetricsCollector()
                    collector.collect_all()
                    st.success("✓ Metrics collected")
                except Exception as e:
                    st.error(f"✗ Error: {e}")
    
    with col3:
        if st.button("🔔 Check Alerts", use_container_width=True):
            with st.spinner("Checking alerts..."):
                try:
                    from monitoring.alert_manager import AlertManager
                    from monitoring.metrics_collector import MetricsCollector
                    collector = MetricsCollector()
                    metrics = collector.collect_all()
                    manager = AlertManager()
                    manager.process_alerts(metrics)
                    st.success("✓ Alerts checked")
                except Exception as e:
                    st.error(f"✗ Error: {e}")

# Pipelines Page
elif page == "🚀 Pipelines":
    st.header("Data Pipelines")
    
    pipeline = st.selectbox(
        "Select Pipeline",
        ["Fraud Detection (Streaming)", "Credit Risk (Batch)", "Churn Prediction (Batch)", "Warehouse Refresh"]
    )
    
    if st.button("▶️ Run Pipeline", type="primary"):
        with st.spinner(f"Running {pipeline}..."):
            try:
                if "Fraud" in pipeline:
                    from orchestration.fraud_streaming_dag import process_new_bronze_file
                    process_new_bronze_file()
                elif "Credit" in pipeline:
                    from orchestration.credit_risk_batch_dag import process_credit_risk_batch
                    process_credit_risk_batch()
                elif "Churn" in pipeline:
                    from orchestration.churn_batch_dag import process_churn_batch
                    process_churn_batch()
                elif "Warehouse" in pipeline:
                    from orchestration.warehouse_refresh_dag import refresh_warehouse
                    refresh_warehouse()
                
                st.success(f"✓ {pipeline} completed successfully")
                st.balloons()
            except Exception as e:
                st.error(f"✗ Pipeline failed: {e}")
                st.exception(e)

# ML Training Page
elif page == "🤖 ML Training":
    st.header("ML Model Training")
    
    model = st.selectbox(
        "Select Model",
        ["Fraud Detection", "Credit Risk", "Churn Prediction"]
    )
    
    if st.button("🎯 Train Model", type="primary"):
        with st.spinner(f"Training {model} model..."):
            try:
                if "Fraud" in model:
                    from ml.fraud.training.train_fraud_model import train_fraud_model
                    train_fraud_model()
                elif "Credit" in model:
                    import sys
                    from pathlib import Path
                    sys.path.append(str(Path.cwd() / 'ml' / 'credit-risk'))
                    from training.train_credit_risk_model import train_credit_risk_model
                    train_credit_risk_model()
                elif "Churn" in model:
                    from ml.churn.training.train_churn_model import train_churn_model
                    train_churn_model()
                
                st.success(f"✓ {model} model trained successfully")
                st.balloons()
            except Exception as e:
                st.error(f"✗ Training failed: {e}")
                st.exception(e)

# Monitoring Page
elif page == "📊 Monitoring":
    st.header("Platform Monitoring")
    
    tab1, tab2 = st.tabs(["Metrics", "Alerts"])
    
    with tab1:
        st.subheader("Metrics Collection")
        if st.button("Collect All Metrics"):
            with st.spinner("Collecting metrics..."):
                try:
                    from monitoring.metrics_collector import MetricsCollector
                    collector = MetricsCollector()
                    collector.collect_all()
                    st.success("✓ Metrics collected")
                except Exception as e:
                    st.error(f"✗ Error: {e}")
    
    with tab2:
        st.subheader("Alert Management")
        if st.button("Check All Alerts"):
            with st.spinner("Checking alerts..."):
                try:
                    from monitoring.alert_manager import AlertManager
                    from monitoring.metrics_collector import MetricsCollector
                    collector = MetricsCollector()
                    metrics = collector.collect_all()
                    manager = AlertManager()
                    manager.process_alerts(metrics)
                    st.success("✓ Alerts checked")
                except Exception as e:
                    st.error(f"✗ Error: {e}")

# Operations Page
elif page == "⚙️ Operations":
    st.header("Operational Tasks")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Warehouse Maintenance")
        if st.button("Run Maintenance", use_container_width=True):
            with st.spinner("Running warehouse maintenance..."):
                try:
                    from warehouse.maintenance import WarehouseMaintenance
                    synapse_server = os.getenv('SYNAPSE_SERVER')
                    database = os.getenv('SYNAPSE_DB')
                    if not synapse_server or not database:
                        st.error("SYNAPSE_SERVER and SYNAPSE_DB environment variables required")
                    else:
                        maintenance = WarehouseMaintenance(synapse_server, database)
                        maintenance.vacuum_all_tables()
                        st.success("✓ Maintenance completed")
                except Exception as e:
                    st.error(f"✗ Error: {e}")
    
    with col2:
        st.subheader("Cost Analysis")
        if st.button("Generate Report", use_container_width=True):
            with st.spinner("Generating cost report..."):
                try:
                    from cost.cost_reporter import CostReporter
                    reporter = CostReporter()
                    reporter.generate_report()
                    st.success("✓ Cost report generated")
                except Exception as e:
                    st.error(f"✗ Error: {e}")

# API Testing Page
elif page == "🧪 API Testing":
    st.header("API Testing")
    
    st.subheader("Fraud Scoring Test")
    
    col1, col2 = st.columns(2)
    
    with col1:
        amount = st.number_input("Transaction Amount", min_value=0.0, value=1000.0)
        merchant = st.text_input("Merchant", value="ACME Store")
        location = st.text_input("Location", value="New York, NY")
    
    with col2:
        card_present = st.checkbox("Card Present", value=True)
        international = st.checkbox("International", value=False)
        time_since_last = st.number_input("Hours Since Last Transaction", min_value=0, value=24)
    
    if st.button("🔍 Score Transaction", type="primary"):
        st.info("API testing requires running API server. Use: python main.py api")
        
        payload = {
            "amount": amount,
            "merchant": merchant,
            "location": location,
            "card_present": card_present,
            "international": international,
            "time_since_last_transaction": time_since_last
        }
        
        st.json(payload)
        st.caption("Send this payload to POST /v1/fraud/score with encryption")

# Footer
st.sidebar.markdown("---")
st.sidebar.caption(f"Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
st.sidebar.caption("🔒 Development Environment Only")
