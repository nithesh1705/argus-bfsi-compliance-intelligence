#!/usr/bin/env bash
# ==============================================================================
# ARGUS — Cloud Run Deployment Script (infra/deploy.sh)
#
# Builds and deploys backend and frontend services to Google Cloud Run.
# ==============================================================================

set -euo pipefail

PROJECT_ID="${ARGUS_PROJECT_ID:-YOUR_GCP_PROJECT_ID}"
REGION="${ARGUS_REGION:-asia-south1}"
REPO="${REGION}-docker.pkg.dev/${PROJECT_ID}/argus-repo"

BACKEND_IMAGE="${REPO}/argus-backend:latest"
FRONTEND_IMAGE="${REPO}/argus-frontend:latest"

BACKEND_SA="argus-backend-sa@${PROJECT_ID}.iam.gserviceaccount.com"
DB_INSTANCE_NAME="${ARGUS_DB_INSTANCE:-argus-mysql-primary}"

echo "=== Deploying ARGUS to Google Cloud Run ==="
echo "Building container images..."

# Build & Push Backend
docker build -t "${BACKEND_IMAGE}" -f backend/Dockerfile .
docker push "${BACKEND_IMAGE}"

# Build & Push Frontend
docker build -t "${FRONTEND_IMAGE}" -f frontend/Dockerfile ./frontend
docker push "${FRONTEND_IMAGE}"

# Deploy Backend Cloud Run Service
echo "Deploying argus-backend service..."
gcloud run deploy argus-backend \
    --image="${BACKEND_IMAGE}" \
    --region="${REGION}" \
    --service-account="${BACKEND_SA}" \
    --add-cloudsql-instances="${PROJECT_ID}:${REGION}:${DB_INSTANCE_NAME}" \
    --set-env-vars="ARGUS_PROVIDER_MODE=live,ARGUS_PROJECT_ID=${PROJECT_ID},ARGUS_REGION=${REGION},ARGUS_INSTANCE_CONNECTION_NAME=${PROJECT_ID}:${REGION}:${DB_INSTANCE_NAME}" \
    --set-secrets="ARGUS_DB_PASSWORD=argus-db-password:latest" \
    --timeout=900 \
    --memory=2Gi \
    --cpu=2 \
    --allow-unauthenticated \
    --project="${PROJECT_ID}"

BACKEND_URL=$(gcloud run services describe argus-backend --region="${REGION}" --project="${PROJECT_ID}" --format="value(status.url)")

# Deploy Frontend Cloud Run Service
echo "Deploying argus-frontend service..."
gcloud run deploy argus-frontend \
    --image="${FRONTEND_IMAGE}" \
    --region="${REGION}" \
    --set-env-vars="VITE_API_BASE_URL=${BACKEND_URL}" \
    --memory=512Mi \
    --allow-unauthenticated \
    --project="${PROJECT_ID}"

FRONTEND_URL=$(gcloud run services describe argus-frontend --region="${REGION}" --project="${PROJECT_ID}" --format="value(status.url)")

echo ""
echo "=== Deployment Successful! ==="
echo "Backend API:  ${BACKEND_URL}"
echo "Frontend UI:  ${FRONTEND_URL}"
