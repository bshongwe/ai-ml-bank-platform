# Cost Controls & Quotas

Automated cost management for hybrid cloud platform.

## Cost Optimization

| Strategy | Implementation | Savings |
|----------|----------------|---------|
| Auto-archiving | Bronze → Glacier after 90d | 70% storage |
| Spot instances | Non-critical ML training | 60% compute |
| Lifecycle policies | Delete scratch files after 7d | 20% storage |
| Resource tagging | Budget tracking by team/project | Visibility |

## Quotas

See `cost_controls.yaml` for resource quotas by environment.

## Usage

```bash
# Check current costs
python cost/cost_reporter.py --period monthly

# Enforce quotas
python cost/quota_enforcer.py --check-all

# Archive old Bronze data
python cost/archive_bronze.py --days-old 90 --dry-run
```

## Cost Alerts

Cost alerts are integrated with monitoring/alert_manager.py:
- Critical: >10% over monthly budget
- Warning: >5% over monthly budget
- Info: Approaching quota limits
