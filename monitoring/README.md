# Monitoring & Observability

Production-grade monitoring for hybrid AI/ML banking platform.

## Layers

- **Streaming Ingestion**: Event latency, delivery success, DLQs
- **Bronze**: Data freshness, schema drift
- **Silver**: Transformation success, feature validity
- **ML**: Model latency, accuracy, drift
- **Warehouse**: ETL/ELT success, table freshness
- **Cost**: Cloud spend per pipeline, per model

## SLIs/SLOs

See `slis_slos.yaml` for detailed service level indicators and objectives.

## Alerts

See `alerts/` for PagerDuty/Teams alert configurations.

## Usage

```bash
python metrics_collector.py --layer all
python alert_manager.py --check-breaches
```
