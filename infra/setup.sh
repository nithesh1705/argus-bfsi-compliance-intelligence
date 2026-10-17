#!/usr/bin/env bash
# ==============================================================================
# ARGUS — Infrastructure Provisioning Script (infra/setup.sh)
#
# Idempotently provisions Google Cloud Platform resources:
# - Required APIs (Cloud Run, Vertex AI, DLP, Cloud SQL, Trace, Logging, Eventarc)
# - Storage Buckets (Calls and Regulations)
# - Service Accounts with Least-Privilege IAM Bindings
# - Cloud SQL for MySQL 8.0 Instance, Database & User
# - Pub/Sub Topic and Eventarc GCS Finalize Trigger
# - Secret Manager Secrets
# ==============================================================================

set -euo pipefail

# Configuration with Defaults
PROJECT_ID="${ARGUS_PROJECT_ID:-YOUR_GCP_PROJECT_ID}"
REGION="${ARGUS_REGION:-asia-south1}"
CALLS_BUCKET="${ARGUS_CALLS_BUCKET:-${PROJECT_ID}-argus-calls}"
REGULATIONS_BUCKET="${ARGUS_REGULATIONS_BUCKET:-${PROJECT_ID}-argus-regulations}"
DB_INSTANCE_NAME="${ARGUS_DB_INSTANCE:-argus-mysql-primary}"
DB_NAME="argus"
DB_USER="argus_user"
DB_PASSWORD="${ARGUS_DB_PASSWORD:-YOUR_DB_PASSWORD}"

BACKEND_SA="argus-backend-sa@${PROJECT_ID}.iam.gserviceaccount.com"
EVENTARC_SA="argus-eventarc-invoker-sa@${PROJECT_ID}.iam.gserviceaccount.com"

echo "=== Provisioning ARGUS Infrastructure on Google Cloud ==="
echo "Project ID: ${PROJECT_ID}"
echo "Region:     ${REGION}"
echo ""

# 1. Enable Required GCP APIs
echo "[1/8] Enabling Google Cloud Services..."
gcloud services enable \
    run.googleapis.com \
    sqladmin.googleapis.com \
    storage.googleapis.com \
    aiplatform.googleapis.com \
    dlp.googleapis.com \
    cloudtrace.googleapis.com \
    logging.googleapis.com \
    eventarc.googleapis.com \
    pubsub.googleapis.com \
    secretmanager.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    generativelanguage.googleapis.com \
    --project="${PROJECT_ID}"

# 2. Create Artifact Registry Repository for Container Images
echo "[2/8] Ensuring Artifact Registry repository exists..."
if ! gcloud artifacts repositories describe argus-repo --location="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    gcloud artifacts repositories create argus-repo \
        --repository-format=docker \
        --location="${REGION}" \
        --description="Docker repository for ARGUS container images" \
        --project="${PROJECT_ID}"
fi

# 3. Create Cloud Storage Buckets
echo "[3/8] Creating Cloud Storage Buckets..."
gcloud storage buckets create "gs://${CALLS_BUCKET}" \
    --location="${REGION}" \
    --uniform-bucket-level-access \
    --project="${PROJECT_ID}" || true

gcloud storage buckets create "gs://${REGULATIONS_BUCKET}" \
    --location="${REGION}" \
    --uniform-bucket-level-access \
    --project="${PROJECT_ID}" || true

# 4. Create Service Accounts
echo "[4/8] Provisioning Least-Privilege Service Accounts..."
gcloud iam service-accounts create argus-backend-sa \
    --display-name="ARGUS Backend Cloud Run Service Account" \
    --project="${PROJECT_ID}" || true

gcloud iam service-accounts create argus-eventarc-invoker-sa \
    --display-name="ARGUS Eventarc Pub/Sub Push Invoker" \
    --project="${PROJECT_ID}" || true

# 5. Assign IAM Roles to Backend SA
echo "[5/8] Binding IAM Roles..."
ROLES=(
    "roles/cloudsql.client"
    "roles/aiplatform.user"
    "roles/dlp.user"
    "roles/cloudtrace.agent"
    "roles/logging.logWriter"
    "roles/secretmanager.secretAccessor"
)

for role in "${ROLES[@]}"; do
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
        --member="serviceAccount:${BACKEND_SA}" \
        --role="${role}" \
        --condition=None >/dev/null
done

# Grant bucket storage access
gcloud storage buckets add-iam-policy-binding "gs://${CALLS_BUCKET}" \
    --member="serviceAccount:${BACKEND_SA}" \
    --role="roles/storage.objectAdmin" >/dev/null

gcloud storage buckets add-iam-policy-binding "gs://${REGULATIONS_BUCKET}" \
    --member="serviceAccount:${BACKEND_SA}" \
    --role="roles/storage.objectAdmin" >/dev/null

# 6. Provision Cloud SQL for MySQL Instance (Cost-Effective Tier)
echo "[6/8] Provisioning Cloud SQL for MySQL (db-f1-micro, no HA for judging)..."
if ! gcloud sql instances describe "${DB_INSTANCE_NAME}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    gcloud sql instances create "${DB_INSTANCE_NAME}" \
        --database-version=MYSQL_8_0 \
        --tier=db-f1-micro \
        --region="${REGION}" \
        --storage-size=10GB \
        --storage-type=SSD \
        --no-backup \
        --project="${PROJECT_ID}"

    # Create database and user
    gcloud sql databases create "${DB_NAME}" --instance="${DB_INSTANCE_NAME}" --project="${PROJECT_ID}"
    gcloud sql users create "${DB_USER}" --instance="${DB_INSTANCE_NAME}" --password="${DB_PASSWORD}" --project="${PROJECT_ID}"
fi

# 7. Store Secrets in Secret Manager
echo "[7/8] Storing Database Credentials in Secret Manager..."
printf "%s" "${DB_PASSWORD}" | gcloud secrets create argus-db-password \
    --data-file=- \
    --replication-policy="automatic" \
    --project="${PROJECT_ID}" || true

# 8. Eventarc Pub/Sub Topic and GCS Finalize Trigger
echo "[8/8] Setting up Eventarc Object Finalize Trigger for calls/incoming/..."
gcloud eventarc triggers create argus-gcs-finalize-trigger \
    --location="${REGION}" \
    --destination-run-service="argus-backend" \
    --destination-run-path="/events/gcs" \
    --event-filters="type=google.cloud.storage.object.v1.finalized" \
    --event-filters="bucket=${CALLS_BUCKET}" \
    --service-account="${EVENTARC_SA}" \
    --project="${PROJECT_ID}" || true

echo ""
echo "=== ARGUS Infrastructure Provisioning Complete ==="
