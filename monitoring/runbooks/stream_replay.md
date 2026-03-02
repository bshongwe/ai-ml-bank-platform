# Operational Runbook: Stream Replay

## Scenario
Fraud stream processing failed for 2 hours due to Lambda timeout.

## Detection
- Alert: streaming_ingestion_success_rate < 99%
- Symptom: Bronze files missing for time range

## Response Steps

### 1. Identify Gap (3 min)
```bash
# Check Bronze files
ls -l lake/bronze/fraud/$(date +%Y/%m/%d)/

# Find missing hours
python monitoring/recovery_scripts/replay_bronze.py \
  --start-time "2026-03-01T10:00:00" \
  --end-time "2026-03-01T12:00:00" \
  --dry-run
```

### 2. Verify Source Availability (2 min)
```bash
# Check Kinesis has retained events (24hr retention)
aws kinesis describe-stream --stream-name fraud-events
```

### 3. Execute Replay (10 min)
```bash
# Replay from Bronze (if events were written)
python monitoring/recovery_scripts/replay_bronze.py \
  --start-time "2026-03-01T10:00:00" \
  --end-time "2026-03-01T12:00:00"

# OR reprocess from Kinesis (if Bronze missing)
# Trigger Airflow backfill for that period
```

### 4. Validate Replay (5 min)
```bash
# Check Bronze completeness
python monitoring/metrics_collector.py

# Verify Silver layer updated
ls -l lake/silver/fraud/2026-03-01.parquet
```

### 5. Monitor Downstream (10 min)
- Check fraud model received backfilled features
- Verify no duplicate transactions scored
- Confirm SLO recovery: streaming_ingestion_success_rate > 99%

## Escalation
- **If Kinesis expired**: Contact data engineering (gap = data loss)
- **If replay fails**: Check Lambda permissions/timeouts
- **If duplicates detected**: Review transaction_id deduplication logic

## Prevention
- Increase Kinesis retention to 7 days
- Add Lambda retry configuration
- Implement idempotent Bronze writes
