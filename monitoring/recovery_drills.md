# Failure & Recovery Drills

Production-ready recovery procedures for all failure scenarios.

## Failure Scenarios

| Scenario | Recovery | Target Time |
|----------|----------|-------------|
| Stream outage | Replay from Bronze | <15min |
| ML model bug | Rollback to stable version | <5min |
| ETL failure | Auto-backfill Silver | <30min |
| Cloud region outage | Cross-cloud failover | <1hr |

## Usage

```bash
# Test replay from Bronze
python recovery_scripts/replay_bronze.py --start-time "2026-03-01T00:00:00"

# Rollback ML model
python recovery_scripts/model_rollback.py --model fraud --version previous

# Backfill Silver layer
python recovery_scripts/backfill_silver.py --date 2026-03-01

# Test failover
python recovery_scripts/test_failover.py --layer ml --target-cloud gcp
```

## Runbooks

See individual files in `runbooks/` for detailed procedures.
