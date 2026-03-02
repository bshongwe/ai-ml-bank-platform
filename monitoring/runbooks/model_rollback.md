# Operational Runbook: Model Rollback

## Scenario
Production fraud model shows degraded precision (<85%).

## Detection
- Alert from monitoring/alert_manager.py (SLO breach)
- Metric: `ml_model_precision` below threshold

## Response Steps

### 1. Assess Impact (2 min)
```bash
python ml/fraud/evaluation/evaluate_model.py \
  --model-path common/model_registry/fraud_latest/model.pkl \
  --data-path lake/silver/fraud/2026-03-01.parquet
```

### 2. Check Recent Versions (1 min)
```bash
python monitoring/recovery_scripts/model_rollback.py \
  --model fraud
```

### 3. Execute Rollback (2 min)
```bash
python monitoring/recovery_scripts/model_rollback.py \
  --model fraud \
  --version previous
```

### 4. Verify Rollback (5 min)
```bash
# Test inference
python ml/fraud/inference/fraud_scorer.py \
  --transaction-id test_123
  
# Check model version
cat common/model_registry/fraud_latest/metadata.json
```

### 5. Monitor Recovery (10 min)
- Watch ml_model_precision metric
- Check fraud_score_latency_ms < 100ms
- Verify no prediction errors

## Escalation
- **If rollback fails**: Contact ML platform team
- **If metric still degraded**: Investigate training data drift
- **If inference errors**: Check feature schema compatibility

## Post-Incident
- Root cause analysis: Why did model degrade?
- Update training validation: Add regression tests
- Document lessons: Update ml/fraud/training/README.md
