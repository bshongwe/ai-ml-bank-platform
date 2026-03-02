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

```bash
# 1. Setup Python environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure paths (update with your values)
export BRONZE_PATH=/data/lake/bronze
export SILVER_PATH=/data/lake/silver
export MODEL_REGISTRY=/data/models
export SYNAPSE_SERVER=bank-synapse.sql.azure.com
export SYNAPSE_DB=analytics_warehouse

# 3. Run data pipelines
airflow dags trigger fraud_streaming_dag      # Bronze → Silver
airflow dags trigger warehouse_refresh_dag    # Silver → Gold → Synapse

# 4. Train ML models
python ml/fraud/training/train_fraud_model.py
python ml/credit-risk/training/train_credit_risk_model.py
python ml/churn/training/train_churn_model.py

# 5. Check monitoring & data quality
python monitoring/metrics_collector.py
python monitoring/alert_manager.py

# 6. Run warehouse maintenance (weekly)
python warehouse/maintenance.py
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

- **Total Files**: 126 production-ready modules
- **Phases Complete**: 4/4 (Foundation, Pipelines, ML, Hardening)
- **ML Models**: 3 (Fraud, Credit Risk, Churn)
- **Cloud Providers**: 3 (AWS, GCP, Azure)
- **Lakehouse Layers**: 3 (Bronze → Silver → Gold)
- **DAGs**: 4 (Fraud streaming, Credit risk, Churn, Warehouse refresh)
- **Recovery Scripts**: 2 (Bronze replay, Model rollback)
- **Security Controls**: 3 (PII masking, Key rotation, Audit logs)

## License

Proprietary - Bank Internal Use Only
