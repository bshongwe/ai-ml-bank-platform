# Hybrid AI/ML Banking Platform

Production-grade platform for fraud detection, credit risk modeling, and
churn prediction across AWS, GCP, and Azure.

## 1. Business Problem

### Use Cases
- **Fraud Detection**: Real-time transaction scoring (<100ms latency)
- **Credit Risk**: Monthly risk band assignment for regulatory capital
- **Churn Prediction**: Weekly retention campaign targeting

### Business Impact
- Fraud loss reduction: 40% (precision >85%, recall >90%)
- Risk model accuracy: AUC >0.80 (Basel III compliant)
- Churn intervention: 25% reduction (high-recall targeting)

## 2. Why Hybrid Cloud

| Cloud | Role | Rationale |
|-------|------|-----------|
| AWS | Streaming ingestion | Kinesis <1s latency, Lambda scale |
| GCP | ML training/inference | Vertex AI, Compute Engine GPUs |
| Azure | Analytics warehouse | Synapse integration with BI tools |

**Trade-off**: Complexity vs. best-of-breed capabilities per layer.

See [ADR-001](architecture/decision-records/ADR-001-hybrid-cloud.md).

## 3. System Architecture

```
┌─────────┐     ┌─────────┐     ┌──────────┐     ┌──────────┐
│ Stream  │────▶│ Bronze  │────▶│  Silver  │────▶│   Gold   │
│  (AWS)  │     │  (Raw)  │     │(Features)│     │(Analytics)│
└─────────┘     └─────────┘     └──────────┘     └──────────┘
                                       │
                                       ▼
                                ┌──────────┐
                                │ML Models │
                                │  (GCP)   │
                                └──────────┘
```

Lakehouse: Bronze (immutable) → Silver (validated) → Gold (warehouse).

Diagrams: [architecture/diagrams/](architecture/diagrams/)

## 4. Data Flow

### Fraud (Streaming)
1. Kinesis → Lambda → S3 Bronze (1-min batches)
2. Airflow DAG → Feature engineering → Parquet Silver
3. GCP Vertex AI → Fraud score → Analytics warehouse
4. CDC incremental load → Gold aggregation → Synapse

### Credit Risk (Batch)
1. Daily upload → S3 Bronze
2. Airflow DAG → Repayment history features → Silver
3. Monthly training → Risk band assignment → Warehouse
4. Daily Gold aggregation → Risk distribution → Synapse

### Churn (Batch)
1. Weekly CRM export → Azure Blob → Bronze
2. Feature engineering → Transaction decay, login inactivity
3. Weekly scoring → Retention campaign targets
4. Weekly Gold cohorts → Churn segments → Synapse

### Gold Layer (Analytics Warehouse)
- **Incremental CDC**: Only process changed records (90% faster)
- **Data quality gates**: Validation metrics tracked per load
- **Aggregation**: Hourly fraud, daily risk, weekly churn cohorts
- **Warehouse optimization**: Auto-maintenance (stats, indexes, partitions)

## 5. ML Lifecycle & Governance

### Training
- Time-split validation (no data leakage)
- Feature schema hashing (lineage tracking)
- Hyperparameter logging (reproducibility)

### Registry
- Version control with approval workflow
- Metadata: training dataset fingerprint, metrics, approval timestamp
- Rollback capability (<5min recovery)

### Monitoring
- Drift detection: Kolmogorov-Smirnov test (p<0.05 threshold)
- Feature validation: Schema, nulls, ranges, types
- Performance: Precision/recall/AUC tracked per version

See [ADR-003](architecture/decision-records/ADR-003-ml-governance.md).

## 6. Security & Compliance

### Zero-Trust Boundaries
- Bronze: PII allowed (encrypted at rest)
- Silver: PII masked (SHA-256 hashing)
- Gold: Analytics-safe (no reversible identifiers, aggregated metrics)

### Data Quality & CDC
- **Incremental processing**: CDC tracks last processed timestamp per table
- **Quality gates**: Schema validation, null checks, range validation
- **Idempotent pipelines**: Safe to re-run without duplicates
- **DQ metrics tracking**: Validation results logged per load

### Key Rotation
- 90-day automated rotation (AWS/GCP/Azure)
- Audit logging: JSONL files with timestamp/action/resource/user

### Compliance
- Basel III: Credit risk model documentation
- GDPR: PII masking before analytics layer
- SOC 2: Audit logs retained 7 years

See [ADR-004](architecture/decision-records/ADR-004-security.md).

## 7. Failure Scenarios & Recovery

| Scenario | Recovery | Target Time |
|----------|----------|-------------|
| Stream outage | Replay from Bronze | <15min |
| ML model bug | Rollback to stable version | <5min |
| ETL failure | Auto-backfill Silver | <30min |
| Cloud region outage | Cross-cloud failover | <1hr |

Runbooks: [monitoring/runbooks/](monitoring/runbooks/)

## 8. Cost Controls

### Optimization
- Auto-archiving: Bronze → Glacier after 90 days (70% savings)
- Spot instances: Non-critical ML training (60% savings)
- Resource tagging: Budget tracking by team/project
- **Incremental CDC**: 90% faster warehouse refreshes (only process new data)
- **Partition archival**: Move old Synapse partitions to cold storage

### Quotas
Environment-specific limits enforced by `cost/quota_enforcer.py`.

### Warehouse Maintenance
- **Statistics updates**: Maintain optimal query plans
- **Index rebuilds**: Prevent performance degradation
- **Automated archival**: 90+ day partitions to archive tables

See [cost/cost_controls.yaml](cost/cost_controls.yaml).

## 9. Trade-offs & Alternatives

### Hybrid vs. Single-Cloud
- **Chosen**: Hybrid (AWS streaming, GCP ML, Azure warehouse)
- **Alternative**: GCP-only (simpler, less vendor lock-in risk)
- **Trade-off**: Complexity vs. best-of-breed per layer

### Lakehouse vs. Data Warehouse
- **Chosen**: Lakehouse (Bronze → Silver → Gold)
- **Alternative**: Direct warehouse loading
- **Trade-off**: Flexibility vs. operational overhead

### RandomForest vs. Deep Learning
- **Chosen**: RandomForest (interpretability for regulators)
- **Alternative**: Neural networks (higher accuracy potential)
- **Trade-off**: Explainability vs. performance

## 10. How a Bank Would Operate This

### Team Structure
- **Data Engineering**: Airflow DAGs, Bronze/Silver pipelines
- **ML Engineering**: Model training, registry, drift monitoring
- **MLOps**: Deployment, rollback, performance tracking
- **Security**: PII masking, key rotation, audit compliance
- **FinOps**: Cost reporting, quota enforcement, archival policies

### Daily Operations
1. Monitor SLI/SLO dashboard (monitoring/slis_slos.yaml)
2. Review drift detection alerts (KS test p-values)
3. Execute runbooks for incidents (monitoring/runbooks/)
4. Weekly cost review (cost/cost_reporter.py)

### Model Governance
- **Training**: Principal Scientist approval required
- **Deployment**: Staff Engineer review + regression tests
- **Monitoring**: Automated precision/recall tracking
- **Rollback**: <5min recovery if degradation detected

### Audit Trail
- All model training: Dataset fingerprint + hyperparameters logged
- All deployments: Approval timestamp + reviewer recorded
- All access: Centralized audit logs (security/audit_logger.py)

---

## Quick Start

### Docker (Recommended)

```bash
# 1. Build images
docker-compose build

# 2. Start development dashboard
docker-compose up dashboard
# Access at http://localhost:8501

# 3. Or start API server
docker-compose up api
# Access at http://localhost:8000

# 4. Run specific commands
docker-compose run worker python main.py train fraud
docker-compose run worker python main.py pipeline warehouse
```

### Development Environment

```bash
# 1. Setup Python environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment variables
export BRONZE_PATH=/data/lake/bronze
export SILVER_PATH=/data/lake/silver
export MODEL_REGISTRY=/data/models
export SYNAPSE_SERVER=bank-synapse.sql.azure.com
export SYNAPSE_DB=analytics_warehouse
export ENVIRONMENT=dev

# 3. Start interactive dashboard (recommended for dev)
python main.py dashboard

# OR use CLI commands:

# Run data pipelines
python main.py pipeline fraud
python main.py pipeline credit-risk
python main.py pipeline churn
python main.py pipeline warehouse

# Train ML models
python main.py train fraud
python main.py train credit-risk
python main.py train churn

# Start API server
python main.py api

# Monitoring & operations
python main.py monitor metrics
python main.py monitor alerts
python main.py ops maintenance
python main.py ops cost-report
```

### Production Environment

```bash
# Production uses orchestration, not direct execution:

# 1. Pipelines: Airflow scheduler triggers DAGs automatically
airflow dags trigger fraud_streaming_dag
airflow dags trigger warehouse_refresh_dag

# 2. API: Kubernetes/ECS deployment
kubectl apply -f k8s/api-deployment.yaml

# 3. Training: Scheduled batch jobs
# Triggered by Airflow or Kubernetes CronJob

# 4. Monitoring: CloudWatch/Grafana dashboards
# Automated metric collection via cron/CloudWatch Events
```

## Documentation

- **ADRs**: [architecture/decision-records/](architecture/decision-records/)
- **Data Contracts**: 
  - Bronze: [lake/bronze/](lake/bronze/)
  - Silver: [lake/silver/](lake/silver/)
  - Gold: [warehouse/schemas/](warehouse/schemas/)
- **Runbooks**: [monitoring/runbooks/](monitoring/runbooks/)
- **Cost Controls**: [cost/README.md](cost/README.md)
- **Architecture Diagrams**: [architecture/diagrams/](architecture/diagrams/)

## Key Components

| Component | Purpose | Location |
|-----------|---------|----------|
| **Main Entry Point** | Unified CLI & dashboard launcher | `main.py` |
| **Streamlit Dashboard** | Interactive dev UI | `streamlit_app.py` |
| **Bronze Layer** | Immutable raw data | `lake/bronze/` |
| **Silver Layer** | Validated features, PII masked | `lake/silver/` |
| **Gold Layer** | Analytics-safe aggregates | `warehouse/` |
| **CDC Tracker** | Incremental load optimization | `warehouse/cdc_tracker.py` |
| **Synapse Loader** | Azure warehouse integration | `warehouse/synapse_loader.py` |
| **Warehouse Maintenance** | Query optimization | `warehouse/maintenance.py` |
| **ML Registry** | Model version control | `ml/common/model_registry/` |
| **Drift Detection** | Distribution monitoring | `ml/common/drift_detection/` |
| **PII Masker** | Privacy compliance | `security/pii_masker.py` |
| **Audit Logger** | Regulatory compliance | `security/audit_logger.py` |

## Platform Statistics

- **Total Files**: 128 production-ready modules
- **Phases Complete**: 4/4 (Foundation, Pipelines, ML, Hardening)
- **ML Models**: 3 (Fraud, Credit Risk, Churn)
- **Cloud Providers**: 3 (AWS, GCP, Azure)
- **Lakehouse Layers**: 3 (Bronze → Silver → Gold)
- **DAGs**: 4 (Fraud streaming, Credit risk, Churn, Warehouse refresh)
- **Entry Points**: 2 (CLI main.py, Dashboard streamlit_app.py)
- **Recovery Scripts**: 2 (Bronze replay, Model rollback)
- **Security Controls**: 3 (PII masking, Key rotation, Audit logs)
- **CI/CD Pipelines**: 3 (CI, CD, ML Training)

## CI/CD

### GitHub Actions Workflows

1. **CI Pipeline** (`.github/workflows/ci.yml`)
   - Runs on: Push to main/develop, Pull requests
   - Tests: Linting, import validation, Docker builds
   - Duration: ~5 minutes

2. **CD Pipeline** (`.github/workflows/cd.yml`)
   - Runs on: Push to main, Version tags
   - Deploys:
     - API → AWS ECS (ECR registry)
     - Worker → GCP GKE (GCR registry)
   - Security: Trivy vulnerability scanning
   - Duration: ~10 minutes

3. **ML Training** (`.github/workflows/ml-training.yml`)
   - Runs on: Weekly schedule (Sunday 2 AM UTC), Manual trigger
   - Trains: Fraud, Credit Risk, Churn models
   - Storage: S3 model registry
   - Duration: ~30-60 minutes per model

### Required Secrets

Configure in GitHub Settings → Secrets:

```bash
AWS_ACCESS_KEY_ID          # AWS deployment credentials
AWS_SECRET_ACCESS_KEY      # AWS deployment credentials
GCP_SA_KEY                 # GCP service account JSON
AZURE_CREDENTIALS          # Azure service principal
```

### Deployment Flow

```
Developer Push → CI Tests → Merge to main → CD Deploy → Production
                    ↓                           ↓
                 Linting                    ECS/GKE
                 Docker Build               Security Scan
                 Import Check               Rollout
```

## License

Proprietary - Bank Internal Use Only
