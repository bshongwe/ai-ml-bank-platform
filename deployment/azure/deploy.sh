#!/bin/bash
set -e

# Azure Deployment Script
# Deploys: Synapse Analytics, API Management, Container Instances

RESOURCE_GROUP="ml-platform-rg"
LOCATION="eastus"
SYNAPSE_WORKSPACE="bank-synapse"
API_MANAGEMENT="bank-api-mgmt"

echo "Deploying to Azure"
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"

# 1. Create resource group
echo "Creating resource group..."
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION

# 2. Create Synapse workspace
echo "Creating Synapse workspace..."
az synapse workspace create \
  --name $SYNAPSE_WORKSPACE \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --storage-account bank-synapse-storage \
  --file-system synapse \
  --sql-admin-login-user sqladmin \
  --sql-admin-login-password 'ComplexP@ssw0rd!' \
  || echo "Synapse workspace already exists"

# 3. Create dedicated SQL pool
echo "Creating SQL pool..."
az synapse sql pool create \
  --name analytics_warehouse \
  --workspace-name $SYNAPSE_WORKSPACE \
  --resource-group $RESOURCE_GROUP \
  --performance-level DW100c \
  || echo "SQL pool already exists"

# 4. Build and push container to ACR
echo "Creating Azure Container Registry..."
az acr create \
  --name bankmlregistry \
  --resource-group $RESOURCE_GROUP \
  --sku Standard \
  --location $LOCATION \
  || echo "ACR already exists"

echo "Building and pushing container..."
az acr build \
  --registry bankmlregistry \
  --image ml-api:latest \
  --file deployment/docker/Dockerfile .

# 5. Deploy to Container Instances
echo "Deploying to Container Instances..."
az container create \
  --name ml-api \
  --resource-group $RESOURCE_GROUP \
  --image bankmlregistry.azurecr.io/ml-api:latest \
  --cpu 2 \
  --memory 4 \
  --registry-login-server bankmlregistry.azurecr.io \
  --registry-username $(az acr credential show --name bankmlregistry --query username -o tsv) \
  --registry-password $(az acr credential show --name bankmlregistry --query passwords[0].value -o tsv) \
  --dns-name-label bank-ml-api \
  --ports 8000 \
  --environment-variables \
    SYNAPSE_SERVER=$SYNAPSE_WORKSPACE.sql.azuresynapse.net \
    SYNAPSE_DB=analytics_warehouse

# 6. Create API Management
echo "Creating API Management..."
az apim create \
  --name $API_MANAGEMENT \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --publisher-email admin@bank.com \
  --publisher-name "Bank ML Platform" \
  --sku-name Developer \
  || echo "API Management already exists"

# 7. Import API to API Management
echo "Importing API..."
az apim api import \
  --resource-group $RESOURCE_GROUP \
  --service-name $API_MANAGEMENT \
  --path /ml \
  --api-id ml-api \
  --specification-format OpenAPI \
  --specification-url http://bank-ml-api.eastus.azurecontainer.io:8000/openapi.json

echo "Azure deployment complete!"
echo "API Endpoint: https://$API_MANAGEMENT.azure-api.net/ml"
echo "Synapse Workspace: https://$SYNAPSE_WORKSPACE.sql.azuresynapse.net"
