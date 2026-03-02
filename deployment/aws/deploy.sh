#!/bin/bash
set -e

# AWS Deployment Script for ML Platform
# Deploys: Kinesis, Lambda, ECS Fargate, MWAA

REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
CLUSTER_NAME="ml-platform"
SERVICE_NAME="ml-api"

echo "Deploying to AWS Account: $ACCOUNT_ID"
echo "Region: $REGION"

# 1. Create ECR repository
echo "Creating ECR repository..."
aws ecr create-repository \
  --repository-name ml-api \
  --region $REGION \
  --image-scanning-configuration scanOnPush=true \
  || echo "ECR repository already exists"

# 2. Build and push Docker image
echo "Building Docker image..."
docker build -t ml-api:latest -f deployment/docker/Dockerfile .

echo "Pushing to ECR..."
aws ecr get-login-password --region $REGION | \
  docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

docker tag ml-api:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/ml-api:latest
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/ml-api:latest

# 3. Create ECS cluster
echo "Creating ECS cluster..."
aws ecs create-cluster \
  --cluster-name $CLUSTER_NAME \
  --region $REGION \
  || echo "Cluster already exists"

# 4. Register task definition
echo "Registering ECS task definition..."
sed "s/ACCOUNT_ID/$ACCOUNT_ID/g" deployment/aws/ecs-task-definition.json > /tmp/task-def.json
aws ecs register-task-definition \
  --cli-input-json file:///tmp/task-def.json \
  --region $REGION

# 5. Create ECS service
echo "Creating ECS service..."
aws ecs create-service \
  --cluster $CLUSTER_NAME \
  --service-name $SERVICE_NAME \
  --task-definition ml-api \
  --desired-count 3 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:$REGION:$ACCOUNT_ID:targetgroup/ml-api/xxx,containerName=ml-api,containerPort=8000" \
  --region $REGION \
  || echo "Service already exists"

# 6. Deploy streaming infrastructure
echo "Deploying Kinesis and Lambda..."
python ingestion/streaming/deploy_infrastructure.py

# 7. Create MWAA environment
echo "Creating MWAA environment..."
aws mwaa create-environment \
  --name ml-platform-airflow \
  --airflow-version 2.7.2 \
  --source-bucket-arn arn:aws:s3:::bank-mwaa-dags \
  --dag-s3-path dags/ \
  --execution-role-arn arn:aws:iam::$ACCOUNT_ID:role/mwaa-execution-role \
  --network-configuration "SubnetIds=subnet-xxx,subnet-yyy,SecurityGroupIds=sg-xxx" \
  --logging-configuration "DagProcessingLogs={Enabled=true,LogLevel=INFO},TaskLogs={Enabled=true,LogLevel=INFO}" \
  --region $REGION \
  || echo "MWAA environment already exists"

# 8. Upload Airflow DAGs
echo "Uploading Airflow DAGs..."
aws s3 sync orchestration/ s3://bank-mwaa-dags/dags/ \
  --exclude "*.pyc" \
  --exclude "__pycache__/*"

# 9. Setup DynamoDB tables
echo "Creating DynamoDB tables..."
python security/setup_dynamodb_encryption.py

echo "AWS deployment complete!"
echo "API Endpoint: http://ml-api-lb-xxx.us-east-1.elb.amazonaws.com"
echo "Airflow UI: https://xxx.airflow.us-east-1.amazonaws.com"
