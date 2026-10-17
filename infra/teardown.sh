#!/usr/bin/env bash
# ==============================================================================
# ARGUS — Resource Teardown Script (infra/teardown.sh)
#
# Tears down billable Cloud SQL, Cloud Run, and Eventarc resources after judging.
# ==============================================================================

set -euo pipefail

PROJECT_ID="${ARGUS_PROJECT_ID:-YOUR_GCP_PROJECT_ID}"
REGION="${ARGUS_REGION:-asia-south1}"
DB_INSTANCE_NAME="${ARGUS_DB_INSTANCE:-argus-mysql-primary}"

echo "=== ARGUS Resource Teardown ==="
read -p "Are you sure you want to delete ARGUS Cloud Run and Cloud SQL resources? (y/N): " -r CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Teardown aborted."
    exit 0
fi

echo "Deleting Cloud Run services..."
gcloud run services delete argus-backend --region="${REGION}" --project="${PROJECT_ID}" --quiet || true
gcloud run services delete argus-frontend --region="${REGION}" --project="${PROJECT_ID}" --quiet || true

echo "Deleting Eventarc triggers..."
gcloud eventarc triggers delete argus-gcs-finalize-trigger --location="${REGION}" --project="${PROJECT_ID}" --quiet || true

echo "Deleting Cloud SQL instance..."
gcloud sql instances delete "${DB_INSTANCE_NAME}" --project="${PROJECT_ID}" --quiet || true

echo "Teardown complete."
