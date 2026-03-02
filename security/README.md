# Security & Compliance

Production-grade security for hybrid AI/ML banking platform.

## Components

- **Zero Trust**: Network segmentation and auth between layers
- **PII Masking**: Automated PII detection and masking in Silver
- **Key Rotation**: Automated key rotation for all cloud providers
- **Audit Logs**: Centralized audit logging across clouds

## Usage

```bash
# Apply PII masking
python pii_masker.py --input silver/data.parquet --output masked.parquet

# Rotate keys
python key_rotation.py --cloud all

# Check audit logs
python audit_logger.py --query "action=model_deploy"
```

## Compliance

All components follow:
- GDPR data protection requirements
- PCI-DSS for payment data
- SOC 2 Type II controls
- Banking regulatory standards
