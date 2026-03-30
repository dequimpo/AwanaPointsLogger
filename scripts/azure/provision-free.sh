#!/usr/bin/env bash
set -euo pipefail

# Free-first provisioning for Awana Points Logger on Azure
# Usage:
#   SUBSCRIPTION_ID=<id> LOCATION=eastus2 ./scripts/azure/provision-free.sh
# Optional env vars:
#   APP_PREFIX=awana
#   RESOURCE_GROUP=rg-awana-free
#   LOCATION=eastus2

APP_PREFIX="${APP_PREFIX:-awana}"
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-awana-free}"
LOCATION="${LOCATION:-eastus2}"
SWA_NAME="${SWA_NAME:-${APP_PREFIX}-web-free}"
ACA_ENV_NAME="${ACA_ENV_NAME:-${APP_PREFIX}-aca-env}"
ACA_APP_NAME="${ACA_APP_NAME:-${APP_PREFIX}-api}"
LOG_ANALYTICS_NAME="${LOG_ANALYTICS_NAME:-${APP_PREFIX}-logs}"

if ! command -v az >/dev/null 2>&1; then
  echo "Azure CLI not found. Install first: brew install azure-cli"
  exit 1
fi

if ! az account show >/dev/null 2>&1; then
  echo "Not logged in to Azure. Run: az login --use-device-code"
  exit 1
fi

if [[ -n "${SUBSCRIPTION_ID:-}" ]]; then
  az account set --subscription "$SUBSCRIPTION_ID"
fi

echo "Creating resource group: $RESOURCE_GROUP"
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none

echo "Creating Static Web App (Free tier): $SWA_NAME"
# Creates the SWA resource without repo binding; CI will deploy artifacts.
az staticwebapp create \
  --name "$SWA_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --sku Free \
  --output none

echo "Creating Log Analytics workspace: $LOG_ANALYTICS_NAME"
az monitor log-analytics workspace create \
  --resource-group "$RESOURCE_GROUP" \
  --workspace-name "$LOG_ANALYTICS_NAME" \
  --location "$LOCATION" \
  --output none

LOG_ANALYTICS_ID=$(az monitor log-analytics workspace show \
  --resource-group "$RESOURCE_GROUP" \
  --workspace-name "$LOG_ANALYTICS_NAME" \
  --query customerId -o tsv)

LOG_ANALYTICS_KEY=$(az monitor log-analytics workspace get-shared-keys \
  --resource-group "$RESOURCE_GROUP" \
  --workspace-name "$LOG_ANALYTICS_NAME" \
  --query primarySharedKey -o tsv)

echo "Creating Container Apps environment: $ACA_ENV_NAME"
az containerapp env create \
  --name "$ACA_ENV_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --logs-workspace-id "$LOG_ANALYTICS_ID" \
  --logs-workspace-key "$LOG_ANALYTICS_KEY" \
  --output none

echo "Creating backend Container App placeholder: $ACA_APP_NAME"
# Placeholder image. CI/CD updates to your FastAPI image in GHCR.
az containerapp create \
  --name "$ACA_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$ACA_ENV_NAME" \
  --image "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest" \
  --target-port 80 \
  --ingress external \
  --cpu 0.25 \
  --memory 0.5Gi \
  --min-replicas 0 \
  --max-replicas 1 \
  --output none

SWA_URL=$(az staticwebapp show --name "$SWA_NAME" --resource-group "$RESOURCE_GROUP" --query defaultHostname -o tsv)
ACA_URL=$(az containerapp show --name "$ACA_APP_NAME" --resource-group "$RESOURCE_GROUP" --query properties.configuration.ingress.fqdn -o tsv)

echo ""
echo "Provisioning complete"
echo "Static Web App URL: https://$SWA_URL"
echo "Container App URL: https://$ACA_URL"
echo ""
echo "Next:"
echo "1) Configure GitHub OIDC + repo secrets/variables"
echo "2) Configure Container App secrets and env vars"
echo "3) Configure Entra redirect URI: https://$SWA_URL/auth"
