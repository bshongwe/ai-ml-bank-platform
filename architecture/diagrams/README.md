# Architecture Diagrams

Production-grade hybrid AI/ML banking platform architecture.

## System Context

```
┌────────────────────────────────────────────────────────────────┐
│                     Banking Platform                           │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌─────────────┐     ┌──────────────┐     ┌────────────────┐ │
│  │ Transaction │────▶│ Fraud Stream │────▶│ Real-time      │ │
│  │ Processing  │     │ (AWS Kinesis)│     │ Scoring (GCP)  │ │
│  └─────────────┘     └──────────────┘     └────────────────┘ │
│                                                                │
│  ┌─────────────┐     ┌──────────────┐     ┌────────────────┐ │
│  │ Core        │────▶│ Batch ETL    │────▶│ Risk Models    │ │
│  │ Banking     │     │ (Airflow)    │     │ (GCP Vertex)   │ │
│  └─────────────┘     └──────────────┘     └────────────────┘ │
│                                                                │
│  ┌─────────────┐     ┌──────────────┐     ┌────────────────┐ │
│  │ CRM         │────▶│ Churn ETL    │────▶│ Retention      │ │
│  │ System      │     │ (Airflow)    │     │ Campaigns      │ │
│  └─────────────┘     └──────────────┘     └────────────────┘ │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
                    HYBRID CLOUD ARCHITECTURE
                    
┌─────────────────────────────────────────────────────────────┐
│ INGESTION LAYER (AWS)                                       │
├─────────────────────────────────────────────────────────────┤
│  Kinesis Stream → Lambda → S3 Bronze (1-min batches)       │
│  Batch Upload → S3 Bronze (daily/weekly)                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ LAKEHOUSE (Multi-Cloud)                                     │
├─────────────────────────────────────────────────────────────┤
│  Bronze: Immutable raw (PII allowed, encrypted)            │
│  Silver: Features (PII masked, validated schemas)          │
│  Gold: Analytics warehouse (Azure Synapse)                 │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ ML LAYER (GCP)                                              │
├─────────────────────────────────────────────────────────────┤
│  Training: Vertex AI (time-split validation)               │
│  Registry: Version control + approval workflow             │
│  Inference: <100ms latency (fraud), batch (risk/churn)     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ OBSERVABILITY (All Clouds)                                  │
├─────────────────────────────────────────────────────────────┤
│  Metrics: SLI/SLO monitoring (latency, accuracy, cost)     │
│  Alerts: Automated breach notifications (PagerDuty)        │
│  Audit: Centralized JSONL logs (7-year retention)          │
└─────────────────────────────────────────────────────────────┘
```

## ML Lifecycle

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Training   │────▶│  Registry   │────▶│  Inference  │
│             │     │             │     │             │
│ - Time split│     │ - Version   │     │ - <100ms    │
│ - Feature   │     │   control   │     │   latency   │
│   schema    │     │ - Approval  │     │ - Fail-open │
│ - Metrics   │     │   workflow  │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                    │
       ▼                   ▼                    ▼
┌─────────────────────────────────────────────────────┐
│            Drift Detection & Monitoring             │
│  - KS test (p<0.05 threshold)                      │
│  - Feature validation (schema, nulls, ranges)      │
│  - Performance tracking (precision/recall/AUC)     │
└─────────────────────────────────────────────────────┘
```

## Security Boundaries

```
┌────────────────────────────────────────────────────────┐
│ BRONZE LAYER (PII Allowed)                            │
│ - Encrypted at rest (AES-256)                         │
│ - Access: Data Engineering only                       │
│ - Retention: 90 days → Glacier                        │
└────────────────────────────────────────────────────────┘
                       │
                       ▼ PII Masking (SHA-256)
┌────────────────────────────────────────────────────────┐
│ SILVER LAYER (PII Masked)                             │
│ - Hashed identifiers                                  │
│ - Access: ML Engineering + Data Science               │
│ - Retention: 180 days → Glacier IR                    │
└────────────────────────────────────────────────────────┘
                       │
                       ▼ Analytics Transform
┌────────────────────────────────────────────────────────┐
│ GOLD LAYER (Analytics-Safe)                           │
│ - No reversible PII                                   │
│ - Access: Business Analysts + BI Tools                │
│ - Retention: 7 years (regulatory compliance)          │
└────────────────────────────────────────────────────────┘
```

## Cost Optimization

```
Storage Lifecycle:
Bronze → (90 days) → Glacier (70% savings)
Silver → (180 days) → Glacier IR (50% savings)
Models → Keep 10 versions → Archive rest

Compute Optimization:
Production: On-demand instances (99.9% SLA)
Training: Spot instances (60% savings)
Dev/Test: Auto-shutdown after 4 hours idle

Resource Tagging:
All resources tagged with:
- environment (prod/staging/dev)
- team (data-eng/ml-eng/mlops)
- cost_center (fraud/risk/churn)
- project (platform-core)
```

## Recovery Scenarios

```
Failure                Recovery               Target Time
─────────────────────────────────────────────────────────
Stream outage      →   Replay from Bronze   →   <15min
ML model bug       →   Rollback version     →   <5min
ETL failure        →   Auto-backfill Silver →   <30min
Region outage      →   Cross-cloud failover →   <1hr
Data corruption    →   Restore from Bronze  →   <2hr
Security breach    →   Revoke keys + audit  →   <1hr
```
