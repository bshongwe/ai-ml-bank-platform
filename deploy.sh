#!/bin/bash
# Automated deployment script for Banking ML Platform

set -e

ENVIRONMENT=${1:-production}
AWS_REGION=${2:-us-east-1}

echo "=========================================="
echo "Banking ML Platform Deployment"
echo "Environment: $ENVIRONMENT"
echo "AWS Region: $AWS_REGION"
echo "=========================================="

# Step 1: Package Lambda function first
echo ""
echo "[1/6] Packaging Lambda function..."
cd ingestion/streaming
zip -r ../../lambda_deployment.zip lambda_handler.py
cd ../..

# Step 2: Deploy AWS Infrastructure with Terraform
echo ""
echo "[2/6] Deploying AWS infrastructure..."
cd terraform
terraform init
terraform plan -var="environment=$ENVIRONMENT" -var="aws_region=$AWS_REGION"
read -p "Apply Terraform changes? (yes/no): " confirm
if [ "$confirm" == "yes" ]; then
    terraform apply -var="environment=$ENVIRONMENT" -var="aws_region=$AWS_REGION" -auto-approve
else
    echo "Terraform deployment cancelled"
    exit 1
fi
cd ..

# Step 3: Build and Push Docker Images
echo ""
echo "[3/6] Building Docker images..."
IMAGE_TAG=$(git rev-parse --short HEAD)
echo "Using image tag: $IMAGE_TAG"

docker build --target api -t banking-ml-api:$IMAGE_TAG .
docker build --target worker -t banking-ml-worker:$IMAGE_TAG .

echo "Pushing to ECR and GCR..."
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Push API to ECR
docker tag banking-ml-api:$IMAGE_TAG $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/banking-ml-platform:api-$IMAGE_TAG
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/banking-ml-platform:api-$IMAGE_TAG

# Push worker to GCR
gcloud auth configure-docker
docker tag banking-ml-worker:$IMAGE_TAG gcr.io/banking-ml-prod/banking-worker:sha-$IMAGE_TAG
docker push gcr.io/banking-ml-prod/banking-worker:sha-$IMAGE_TAG

# Step 4: Deploy to GKE (if using Kubernetes)
echo ""
echo "[4/6] Deploying to Kubernetes..."
read -p "Deploy to GKE? (yes/no): " deploy_k8s
if [ "$deploy_k8s" == "yes" ]; then
    gcloud container clusters get-credentials ml-cluster --region us-central1
    
    # Substitute IMAGE_TAG in manifests
    export IMAGE_TAG
    envsubst < k8s/namespace-secrets.yaml | kubectl apply -f -
    envsubst < k8s/api-deployment.yaml | kubectl apply -f -
    envsubst < k8s/worker-deployment.yaml | kubectl apply -f -
    
    echo "Waiting for rollout..."
    kubectl rollout status deployment/banking-api -n banking-ml
fi

# Step 5: Deploy Azure Synapse Schema
echo ""
echo "[5/6] Deploying Azure Synapse schema..."
read -p "Deploy Synapse schema? (yes/no): " deploy_synapse
if [ "$deploy_synapse" == "yes" ]; then
    bash warehouse/ddl/deploy_schema.sh
fi

# Step 6: Verify Deployment
echo ""
echo "[6/6] Verifying deployment..."

# Check ECS service
echo "Checking ECS service..."
aws ecs describe-services \
    --cluster banking-ml-cluster-$ENVIRONMENT \
    --services api-service \
    --region $AWS_REGION \
    --query 'services[0].status' \
    --output text

# Check ALB health
echo "Checking ALB target health..."
TARGET_GROUP_ARN=$(aws elbv2 describe-target-groups \
    --names banking-api-tg-$ENVIRONMENT \
    --region $AWS_REGION \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text)

aws elbv2 describe-target-health \
    --target-group-arn $TARGET_GROUP_ARN \
    --region $AWS_REGION

# Check Lambda
echo "Checking Lambda function..."
aws lambda get-function \
    --function-name fraud-stream-processor-$ENVIRONMENT \
    --region $AWS_REGION \
    --query 'Configuration.State' \
    --output text

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Configure DNS for ALB endpoint"
echo "2. Set up SSL certificate in ACM"
echo "3. Configure monitoring alerts"
echo "4. Run smoke tests"
echo ""
echo "Useful commands:"
echo "  - View API logs: aws logs tail /ecs/banking-api --follow"
echo "  - Check ECS tasks: aws ecs list-tasks --cluster banking-ml-cluster-$ENVIRONMENT"
echo "  - Monitor Kinesis: aws kinesis describe-stream --stream-name fraud-transactions-$ENVIRONMENT"
