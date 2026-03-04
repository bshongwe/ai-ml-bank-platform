# Deployment Guide

Complete guide for deploying the Banking ML Platform to production.

## Prerequisites

### Required Tools
- AWS CLI v2
- Terraform >= 1.0
- Docker
- kubectl
- gcloud CLI
- Azure CLI

### Required Credentials
- AWS credentials with admin access
- GCP service account with GKE/GCR permissions
- Azure service principal with Synapse access
- GitHub repository secrets configured

## Quick Deploy

```bash
# One-command deployment
./deploy.sh production us-east-1
```

## Manual Deployment Steps

### 1. Infrastructure (Terraform)

```bash
cd terraform

# Initialize
terraform init

# Plan
terraform plan -var="environment=production"

# Apply
terraform apply -var="environment=production"

# Outputs
terraform output
```

**Resources Created**:
- S3 buckets (bronze, silver, models, DLQ)
- Kinesis stream (fraud-transactions)
- Lambda function (fraud-stream-processor)
- ECS cluster + service
- ALB with HTTPS listener
- CloudWatch alarms
- SNS alerts topic

### 2. Container Images

```bash
# Build
docker build --target api -t banking-ml-api:latest .
docker build --target worker -t banking-ml-worker:latest .

# Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

docker tag banking-ml-api:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/banking-ml-platform:api-latest
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/banking-ml-platform:api-latest

# Push to GCR (for GKE)
gcloud auth configure-docker
docker tag banking-ml-worker:latest gcr.io/banking-ml-prod/banking-worker:latest
docker push gcr.io/banking-ml-prod/banking-worker:latest
```

### 3. Kubernetes (GKE)

```bash
# Connect to cluster
gcloud container clusters get-credentials ml-cluster --region us-central1

# Create namespace and secrets
kubectl apply -f k8s/namespace-secrets.yaml

# Update secrets with actual values
kubectl create secret generic banking-api-secrets \
  --from-literal=AWS_ACCESS_KEY_ID=<KEY> \
  --from-literal=AWS_SECRET_ACCESS_KEY=<SECRET> \
  -n banking-ml --dry-run=client -o yaml | kubectl apply -f -

# Deploy services
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/worker-deployment.yaml

# Verify
kubectl get pods -n banking-ml
kubectl rollout status deployment/banking-api -n banking-ml
```

### 4. Azure Synapse

```bash
# Set environment variables
export SYNAPSE_SERVER=bank-synapse.sql.azure.com
export SYNAPSE_DB=analytics_warehouse

# Deploy schema
bash warehouse/ddl/deploy_schema.sh

# Verify
sqlcmd -S $SYNAPSE_SERVER -d $SYNAPSE_DB -G -Q "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES"
```

### 5. Lambda Function

```bash
# Package
cd ingestion/streaming
zip -r ../../lambda_deployment.zip lambda_handler.py
cd ../..

# Deploy
aws lambda update-function-code \
  --function-name fraud-stream-processor-production \
  --zip-file fileb://lambda_deployment.zip
```

### 6. Secrets Management

```bash
# Generate API client keys
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Store in Secrets Manager
aws secretsmanager create-secret \
  --name banking/api/client/CLIENT_ID/encryption-key \
  --secret-string $(openssl rand -base64 32)

# Set up rotation
python security/rotate_secrets.py
```

## Deployment Verification

### Health Checks

```bash
# API health
curl https://api.banking-ml.example.com/health

# ECS service status
aws ecs describe-services \
  --cluster banking-ml-cluster-production \
  --services api-service

# Kubernetes pods
kubectl get pods -n banking-ml

# Lambda function
aws lambda get-function \
  --function-name fraud-stream-processor-production
```

### Smoke Tests

```bash
# Test fraud scoring endpoint
python api/client_example.py

# Test Kinesis ingestion
python ingestion/streaming/fraud_streaming_ingest.py

# Test pipeline
docker-compose run worker python main.py pipeline fraud
```

## Monitoring Setup

### CloudWatch Dashboards

Alarms automatically created by Terraform:
- API CPU/Memory utilization
- ALB 5xx errors
- Lambda errors/throttles
- Kinesis iterator age

### Grafana Dashboard

```bash
# Import dashboard
curl -X POST http://grafana:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @monitoring/dashboards/production-dashboard.json
```

### Log Aggregation

```bash
# Tail API logs
aws logs tail /ecs/banking-api --follow

# Tail Lambda logs
aws logs tail /aws/lambda/fraud-stream-processor-production --follow

# Kubernetes logs
kubectl logs -f deployment/banking-api -n banking-ml
```

## Rollback Procedures

### ECS Rollback

```bash
# List task definitions
aws ecs list-task-definitions --family-prefix banking-api

# Rollback to previous version
aws ecs update-service \
  --cluster banking-ml-cluster-production \
  --service api-service \
  --task-definition banking-api:PREVIOUS_VERSION
```

### Kubernetes Rollback

```bash
# Rollback deployment
kubectl rollout undo deployment/banking-api -n banking-ml

# Rollback to specific revision
kubectl rollout undo deployment/banking-api --to-revision=2 -n banking-ml
```

### Model Rollback

```bash
# Use recovery script
python monitoring/recovery_scripts/model_rollback.py --model fraud --version v1.2.3
```

## Blue/Green Deployment

### ECS Blue/Green

```bash
# Create new task definition with :green tag
aws ecs register-task-definition --cli-input-json file://task-def-green.json

# Update service with new task definition
aws ecs update-service \
  --cluster banking-ml-cluster-production \
  --service api-service \
  --task-definition banking-api:green

# Monitor deployment
aws ecs wait services-stable \
  --cluster banking-ml-cluster-production \
  --services api-service
```

### Kubernetes Canary

```bash
# Deploy canary version
kubectl apply -f k8s/api-deployment-canary.yaml

# Monitor metrics
kubectl top pods -n banking-ml

# Promote canary
kubectl patch deployment banking-api -n banking-ml \
  --patch '{"spec":{"template":{"spec":{"containers":[{"name":"api","image":"gcr.io/banking-ml-prod/banking-api:canary"}]}}}}'
```

## Disaster Recovery

### Bronze Replay

```bash
# Replay from specific timestamp
python monitoring/recovery_scripts/replay_bronze.py \
  --start-time "2024-01-01T00:00:00Z" \
  --end-time "2024-01-01T23:59:59Z"
```

### Cross-Region Failover

```bash
# Switch to DR region
export AWS_REGION=us-west-2

# Update DNS to point to DR ALB
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch file://dns-failover.json
```

## Cost Optimization

### Enable Auto-Scaling

Already configured in Terraform:
- ECS: 3-20 tasks based on CPU (70%)
- Kubernetes HPA: 3-20 pods based on CPU/memory

### Spot Instances

```bash
# Update ECS service to use Fargate Spot
aws ecs update-service \
  --cluster banking-ml-cluster-production \
  --service api-service \
  --capacity-provider-strategy \
    capacityProvider=FARGATE_SPOT,weight=1,base=0
```

### Archive Old Data

```bash
# Run archival script
python cost/archive_bronze.py --days 90
```

## Security Hardening

### Enable WAF

```bash
# Create WAF ACL
aws wafv2 create-web-acl \
  --name banking-api-waf \
  --scope REGIONAL \
  --default-action Allow={} \
  --rules file://waf-rules.json

# Associate with ALB
aws wafv2 associate-web-acl \
  --web-acl-arn <WAF_ACL_ARN> \
  --resource-arn <ALB_ARN>
```

### Rotate Secrets

```bash
# Manual rotation
python security/rotate_secrets.py

# Automated (cron)
0 0 * * 0 /usr/bin/python3 /app/security/rotate_secrets.py
```

## Troubleshooting

### Common Issues

**ECS tasks failing to start**
```bash
# Check task logs
aws ecs describe-tasks \
  --cluster banking-ml-cluster-production \
  --tasks <TASK_ID>
```

**Lambda timeout**
```bash
# Increase timeout
aws lambda update-function-configuration \
  --function-name fraud-stream-processor-production \
  --timeout 120
```

**Kubernetes pods pending**
```bash
# Check events
kubectl describe pod <POD_NAME> -n banking-ml

# Check node resources
kubectl top nodes
```

## Maintenance Windows

### Planned Maintenance

```bash
# Scale down to minimum
kubectl scale deployment banking-api --replicas=1 -n banking-ml

# Perform maintenance
bash warehouse/ddl/deploy_schema.sh

# Scale back up
kubectl scale deployment banking-api --replicas=3 -n banking-ml
```

## Support Contacts

- **Infrastructure**: devops@bank.example.com
- **ML Engineering**: ml-team@bank.example.com
- **Security**: security@bank.example.com
- **On-Call**: PagerDuty rotation
