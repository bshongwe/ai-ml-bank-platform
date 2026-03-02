# Production Deployment Guide

## Overview

Deploy the hybrid AI/ML banking platform across AWS, GCP, and Azure.

## Prerequisites

### Tools Required
```bash
# AWS CLI
aws --version  # >= 2.0

# GCP CLI
gcloud --version  # >= 400.0

# Azure CLI
az --version  # >= 2.50

# Docker
docker --version  # >= 20.10

# Python
python --version  # >= 3.11
```

### Credentials Setup
```bash
# AWS
aws configure
export AWS_PROFILE=bank-prod

# GCP
gcloud auth login
gcloud config set project bank-ml-platform

# Azure
az login
az account set --subscription "Bank Production"
```

## Deployment Order

**Critical**: Deploy in this order to maintain dependencies:

1. **AWS** (Streaming + Orchestration)
2. **GCP** (ML Training)
3. **Azure** (Data Warehouse)

## Step-by-Step Deployment

### 1. AWS Deployment (30 minutes)

```bash
# Make script executable
chmod +x deployment/aws/deploy.sh

# Deploy infrastructure
./deployment/aws/deploy.sh

# Verify deployment
aws ecs list-services --cluster ml-platform
aws mwaa get-environment --name ml-platform-airflow
```

**What Gets Deployed**:
- ✅ Kinesis stream (fraud-transactions)
- ✅ Lambda function (stream processor)
- ✅ ECS Fargate (ML API, 3 tasks)
- ✅ MWAA (Managed Airflow)
- ✅ DynamoDB tables (API nonces, rate limits)

### 2. GCP Deployment (20 minutes)

```bash
# Make script executable
chmod +x deployment/gcp/deploy.sh

# Deploy infrastructure
./deployment/gcp/deploy.sh

# Verify deployment
gcloud run services list
gcloud ai models list --region=us-central1
```

**What Gets Deployed**:
- ✅ Cloud Run (ML API)
- ✅ Vertex AI (training pipeline)
- ✅ GCS buckets (models, training data)

### 3. Azure Deployment (40 minutes)

```bash
# Make script executable
chmod +x deployment/azure/deploy.sh

# Deploy infrastructure
./deployment/azure/deploy.sh

# Verify deployment
az synapse workspace show --name bank-synapse
az apim show --name bank-api-mgmt
```

**What Gets Deployed**:
- ✅ Synapse Analytics (DW100c)
- ✅ Container Instances (ML API)
- ✅ API Management (gateway)

## Post-Deployment Configuration

### 1. Configure Cross-Cloud Networking

```bash
# AWS VPC Peering to GCP
aws ec2 create-vpc-peering-connection \
  --vpc-id vpc-aws \
  --peer-vpc-id vpc-gcp \
  --peer-region us-central1

# Azure VNet Peering to AWS
az network vnet peering create \
  --name azure-to-aws \
  --resource-group ml-platform-rg \
  --vnet-name ml-vnet \
  --remote-vnet /subscriptions/xxx/resourceGroups/xxx/providers/Microsoft.Network/virtualNetworks/aws-vnet
```

### 2. Setup Secrets

```bash
# AWS Secrets Manager
aws secretsmanager create-secret \
  --name api/client/payment-processor/encryption-key \
  --secret-string $(openssl rand -base64 32)

# GCP Secret Manager
echo -n $(openssl rand -base64 32) | \
  gcloud secrets create api-encryption-key --data-file=-

# Azure Key Vault
az keyvault secret set \
  --vault-name bank-vault \
  --name api-encryption-key \
  --value $(openssl rand -base64 32)
```

### 3. Upload ML Models

```bash
# Upload to S3
aws s3 cp ml/fraud/models/ s3://bank-ml-models/fraud/ --recursive

# Upload to GCS
gsutil -m cp -r ml/fraud/models/ gs://bank-ml-models/fraud/

# Register in Vertex AI
gcloud ai models upload \
  --region=us-central1 \
  --display-name=fraud-model \
  --artifact-uri=gs://bank-ml-models/fraud/
```

### 4. Initialize Synapse Tables

```bash
# Run warehouse setup
python warehouse/synapse_loader.py --init

# Create partitions
python warehouse/maintenance.py --create-partitions
```

## Verification Checklist

- [ ] AWS ECS service running (3 tasks healthy)
- [ ] GCP Cloud Run responding (200 OK on /health)
- [ ] Azure Synapse accessible (SQL pool online)
- [ ] Airflow DAGs visible in MWAA UI
- [ ] API endpoints responding (test with curl)
- [ ] DynamoDB tables created
- [ ] Secrets stored in all clouds
- [ ] ML models uploaded

## Testing

### Test ML API
```bash
# AWS endpoint
curl https://ml-api-lb-xxx.us-east-1.elb.amazonaws.com/health

# GCP endpoint
curl https://ml-api-xxx.run.app/health

# Azure endpoint
curl https://bank-api-mgmt.azure-api.net/ml/health
```

### Test Airflow DAGs
```bash
# Trigger fraud streaming DAG
aws mwaa create-cli-token --name ml-platform-airflow
# Use token to access Airflow UI and trigger DAG
```

### Test End-to-End
```bash
# Send test transaction to Kinesis
python ingestion/streaming/test_producer.py

# Check Bronze layer
aws s3 ls s3://bank-datalake-bronze/payments_raw/

# Check Silver layer (after DAG runs)
aws s3 ls s3://bank-datalake-silver/fraud_features/

# Check Gold layer (after warehouse refresh)
python warehouse/synapse_loader.py --query "SELECT COUNT(*) FROM agg_fraud_metrics"
```

## Monitoring

### CloudWatch Dashboards
```bash
# Create monitoring dashboard
aws cloudwatch put-dashboard \
  --dashboard-name ml-platform \
  --dashboard-body file://deployment/aws/cloudwatch-dashboard.json
```

### Alerts
```bash
# Setup SNS topic for alerts
aws sns create-topic --name ml-platform-alerts

# Subscribe email
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:xxx:ml-platform-alerts \
  --protocol email \
  --notification-endpoint ops@bank.com
```

## Rollback Procedures

### Rollback AWS
```bash
# Revert to previous task definition
aws ecs update-service \
  --cluster ml-platform \
  --service ml-api \
  --task-definition ml-api:PREVIOUS_VERSION
```

### Rollback GCP
```bash
# Revert to previous Cloud Run revision
gcloud run services update-traffic ml-api \
  --to-revisions=ml-api-PREVIOUS_REVISION=100
```

### Rollback Azure
```bash
# Redeploy previous container
az container create \
  --name ml-api \
  --image bankmlregistry.azurecr.io/ml-api:PREVIOUS_TAG
```

## Cost Monitoring

```bash
# AWS Cost Explorer
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost

# GCP Billing
gcloud billing accounts list
gcloud billing projects describe bank-ml-platform

# Azure Cost Management
az consumption usage list \
  --start-date 2024-01-01 \
  --end-date 2024-01-31
```

## Troubleshooting

### Issue: ECS tasks failing
```bash
# Check logs
aws logs tail /ecs/ml-api --follow

# Check task status
aws ecs describe-tasks \
  --cluster ml-platform \
  --tasks $(aws ecs list-tasks --cluster ml-platform --query 'taskArns[0]' --output text)
```

### Issue: Airflow DAGs not appearing
```bash
# Check S3 sync
aws s3 ls s3://bank-mwaa-dags/dags/

# Check MWAA logs
aws logs tail /aws/mwaa/ml-platform-airflow/dag-processing --follow
```

### Issue: Synapse connection timeout
```bash
# Check firewall rules
az synapse workspace firewall-rule list \
  --workspace-name bank-synapse \
  --resource-group ml-platform-rg

# Add your IP
az synapse workspace firewall-rule create \
  --name AllowMyIP \
  --workspace-name bank-synapse \
  --resource-group ml-platform-rg \
  --start-ip-address YOUR_IP \
  --end-ip-address YOUR_IP
```

## Support

- **AWS Issues**: AWS Support Console
- **GCP Issues**: GCP Support Portal
- **Azure Issues**: Azure Support Portal
- **Platform Issues**: Internal #ml-platform-ops channel

## Next Steps

After successful deployment:
1. Review [security/ENCRYPTION_GUIDE.md](../security/ENCRYPTION_GUIDE.md)
2. Start Phase 3 migration (encrypt existing data)
3. Onboard first API client
4. Setup monitoring dashboards
5. Schedule weekly cost reviews
