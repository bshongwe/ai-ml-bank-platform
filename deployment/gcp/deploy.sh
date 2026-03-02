#!/bin/bash
set -e

# GCP Deployment Script for ML Training
# Deploys: Vertex AI, Cloud Run, Cloud Storage

PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"

echo "Deploying to GCP Project: $PROJECT_ID"
echo "Region: $REGION"

# 1. Enable required APIs
echo "Enabling GCP APIs..."
gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  storage.googleapis.com \
  secretmanager.googleapis.com \
  --project=$PROJECT_ID

# 2. Create GCS buckets
echo "Creating GCS buckets..."
gsutil mb -p $PROJECT_ID -l $REGION gs://$PROJECT_ID-ml-models/ || true
gsutil mb -p $PROJECT_ID -l $REGION gs://$PROJECT_ID-ml-training/ || true

# 3. Build and deploy ML API to Cloud Run
echo "Building container for Cloud Run..."
gcloud builds submit \
  --tag gcr.io/$PROJECT_ID/ml-api:latest \
  --project=$PROJECT_ID \
  -f deployment/docker/Dockerfile .

echo "Deploying to Cloud Run..."
gcloud run deploy ml-api \
  --image gcr.io/$PROJECT_ID/ml-api:latest \
  --platform managed \
  --region $REGION \
  --min-instances 2 \
  --max-instances 100 \
  --memory 2Gi \
  --cpu 2 \
  --timeout 60s \
  --concurrency 80 \
  --allow-unauthenticated \
  --set-env-vars MODEL_REGISTRY=gs://$PROJECT_ID-ml-models/ \
  --project=$PROJECT_ID

# 4. Create Vertex AI training pipeline
echo "Creating Vertex AI training pipeline..."
gcloud ai custom-jobs create \
  --region=$REGION \
  --display-name=fraud-model-training \
  --worker-pool-spec=machine-type=n1-highmem-8,replica-count=1,container-image-uri=gcr.io/$PROJECT_ID/ml-training:latest \
  --project=$PROJECT_ID

# 5. Deploy model to Vertex AI endpoint
echo "Deploying model to Vertex AI..."
gcloud ai models upload \
  --region=$REGION \
  --display-name=fraud-model \
  --container-image-uri=gcr.io/$PROJECT_ID/ml-api:latest \
  --container-health-route=/health \
  --container-predict-route=/v1/fraud/score \
  --project=$PROJECT_ID

echo "GCP deployment complete!"
echo "Cloud Run URL: $(gcloud run services describe ml-api --region=$REGION --format='value(status.url)')"
