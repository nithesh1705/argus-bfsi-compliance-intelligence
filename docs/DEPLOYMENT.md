# ARGUS — Production Deployment Guide for Google Cloud

Comprehensive deployment procedures, infrastructure automation, IAM permissions, Cloud Run configuration, and cost control for Google Cloud Platform.

[Back to documentation index](./INDEX.md) | [Next: Observability & APM](./OBSERVABILITY.md)

---

## Table of Contents

- [Overview & Architecture Map](#overview--architecture-map)
- [Deployment Prerequisites](#deployment-prerequisites)
- [Order of Operations](#order-of-operations)
  - [Step 1: Enable Google Cloud APIs](#step-1-enable-google-cloud-apis)
  - [Step 2: Create Artifact Registry Repository](#step-2-create-artifact-registry-repository)
  - [Step 3: Provision Cloud Storage Buckets](#step-3-provision-cloud-storage-buckets)
  - [Step 4: Provision Service Accounts](#step-4-provision-service-accounts)
  - [Step 5: Bind Least-Privilege IAM Roles](#step-5-bind-least-privilege-iam-roles)
  - [Step 6: Provision Cloud SQL for MySQL](#step-6-provision-cloud-sql-for-mysql)
  - [Step 7: Store Database Secrets](#step-7-store-database-secrets)
  - [Step 8: Build and Push Container Images](#step-8-build-and-push-container-images)
  - [Step 9: Deploy Services to Cloud Run](#step-9-deploy-services-to-cloud-run)
  - [Step 10: Configure Eventarc & Pub/Sub Ingestion](#step-10-configure-eventarc--pubsub-ingestion)
- [Service Accounts & IAM Roles Reference](#service-accounts--iam-roles-reference)
- [Vertex AI Location Configuration](#vertex-ai-location-configuration)
- [Post-Deployment Health Checks](#post-deployment-health-checks)
- [Cost Control & Resource Teardown](#cost-control--resource-teardown)
- [Related Documents](#related-documents)

---

## Overview & Architecture Map

ARGUS deploys as a fully managed, serverless compliance system on Google Cloud Platform:
- **Compute:** Google Cloud Run (containerized backend API and frontend Nginx SPA)
- **Data Layer:** Cloud SQL for MySQL 8.0 (`db-f1-micro`) and Cloud Storage buckets
- **Event Mesh:** Google Eventarc triggering authenticated Pub/Sub push
- **AI Core:** Google Vertex AI Gemini Flash endpoints
- **Data Protection:** Google Cloud Sensitive Data Protection (DLP)
- **Observability:** Google Cloud Trace and Cloud Logging

Infrastructure automation scripts are located in [`../infra/`](../infra/):
- [`setup.sh`](../infra/setup.sh): Idempotent resource provisioning and IAM configuration
- [`deploy.sh`](../infra/deploy.sh): Container compilation and Cloud Run deployment
- [`teardown.sh`](../infra/teardown.sh): Safe deletion of billable resources

---

## Deployment Prerequisites

Before deploying, ensure:
1. A Google Cloud project exists with an active billing account.
2. The Google Cloud CLI (`gcloud`) and Docker are installed locally.
3. You are authenticated with sufficient administrative privileges:
   ```bash
   gcloud auth login
   gcloud auth configure-docker <YOUR_REGION>-docker.pkg.dev
   gcloud config set project <YOUR_GCP_PROJECT_ID>
   ```

---

## Order of Operations

Follow this sequential workflow. The commands mirror [`../infra/setup.sh`](../infra/setup.sh) and [`../infra/deploy.sh`](../infra/deploy.sh).

### Step 1: Enable Google Cloud APIs
Enable the required managed APIs:

```bash
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
    --project="<YOUR_GCP_PROJECT_ID>"
```

### Step 2: Create Artifact Registry Repository
Create a Docker registry repository in your target region:

```bash
gcloud artifacts repositories create argus-repo \
    --repository-format=docker \
    --location="<YOUR_REGION>" \
    --description="Docker repository for ARGUS container images" \
    --project="<YOUR_GCP_PROJECT_ID>"
```

### Step 3: Provision Cloud Storage Buckets
Create dedicated buckets with uniform bucket-level access:

```bash
# Calls bucket (incoming telephony and permanent archive)
gcloud storage buckets create "gs://<YOUR_CALLS_BUCKET>" \
    --location="<YOUR_REGION>" \
    --uniform-bucket-level-access \
    --project="<YOUR_GCP_PROJECT_ID>"

# Regulations bucket (statutory circular PDFs)
gcloud storage buckets create "gs://<YOUR_REGULATIONS_BUCKET>" \
    --location="<YOUR_REGION>" \
    --uniform-bucket-level-access \
    --project="<YOUR_GCP_PROJECT_ID>"
```

### Step 4: Provision Service Accounts
Provision two distinct service accounts to maintain security boundaries:

```bash
# 1. Backend runtime service account
gcloud iam service-accounts create argus-backend-sa \
    --display-name="ARGUS Backend Cloud Run Service Account" \
    --project="<YOUR_GCP_PROJECT_ID>"

# 2. Eventarc invoker service account
gcloud iam service-accounts create argus-eventarc-invoker-sa \
    --display-name="ARGUS Eventarc Pub/Sub Push Invoker" \
    --project="<YOUR_GCP_PROJECT_ID>"
```

### Step 5: Bind Least-Privilege IAM Roles
Assign least-privilege roles to `argus-backend-sa`:

```bash
ROLES=(
    "roles/cloudsql.client"
    "roles/aiplatform.user"
    "roles/dlp.user"
    "roles/cloudtrace.agent"
    "roles/logging.logWriter"
    "roles/secretmanager.secretAccessor"
)

for role in "${ROLES[@]}"; do
    gcloud projects add-iam-policy-binding "<YOUR_GCP_PROJECT_ID>" \
        --member="serviceAccount:argus-backend-sa@<YOUR_GCP_PROJECT_ID>.iam.gserviceaccount.com" \
        --role="${role}" \
        --condition=None
done

# Grant bucket storage access
gcloud storage buckets add-iam-policy-binding "gs://<YOUR_CALLS_BUCKET>" \
    --member="serviceAccount:argus-backend-sa@<YOUR_GCP_PROJECT_ID>.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

gcloud storage buckets add-iam-policy-binding "gs://<YOUR_REGULATIONS_BUCKET>" \
    --member="serviceAccount:argus-backend-sa@<YOUR_GCP_PROJECT_ID>.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"
```

### Step 6: Provision Cloud SQL for MySQL
Deploy a lightweight Cloud SQL instance for MySQL 8.0:

```bash
gcloud sql instances create "argus-mysql-primary" \
    --database-version=MYSQL_8_0 \
    --tier=db-f1-micro \
    --region="<YOUR_REGION>" \
    --storage-size=10GB \
    --storage-type=SSD \
    --no-backup \
    --project="<YOUR_GCP_PROJECT_ID>"

# Create database and user
gcloud sql databases create "argus" --instance="argus-mysql-primary" --project="<YOUR_GCP_PROJECT_ID>"
gcloud sql users create "argus_user" --instance="argus-mysql-primary" --password="<YOUR_DB_PASSWORD>" --project="<YOUR_GCP_PROJECT_ID>"
```

Apply the database schema and seed data via [`../scripts/init_argus_db.py`](../scripts/init_argus_db.py).

### Step 7: Store Database Secrets
Store the database password securely in Secret Manager:

```bash
printf "%s" "<YOUR_DB_PASSWORD>" | gcloud secrets create argus-db-password \
    --data-file=- \
    --replication-policy="automatic" \
    --project="<YOUR_GCP_PROJECT_ID>"
```

### Step 8: Build and Push Container Images

```bash
REPO="<YOUR_REGION>-docker.pkg.dev/<YOUR_GCP_PROJECT_ID>/argus-repo"

# Build & Push Backend
docker build -t "${REPO}/argus-backend:latest" -f backend/Dockerfile .
docker push "${REPO}/argus-backend:latest"

# Build & Push Frontend
docker build -t "${REPO}/argus-frontend:latest" -f frontend/Dockerfile ./frontend
docker push "${REPO}/argus-frontend:latest"
```

### Step 9: Deploy Services to Cloud Run

Deploy the backend API:

```bash
gcloud run deploy argus-backend \
    --image="<YOUR_REGION>-docker.pkg.dev/<YOUR_GCP_PROJECT_ID>/argus-repo/argus-backend:latest" \
    --region="<YOUR_REGION>" \
    --service-account="argus-backend-sa@<YOUR_GCP_PROJECT_ID>.iam.gserviceaccount.com" \
    --add-cloudsql-instances="<YOUR_GCP_PROJECT_ID>:<YOUR_REGION>:argus-mysql-primary" \
    --set-env-vars="ARGUS_PROVIDER_MODE=live,ARGUS_PROJECT_ID=<YOUR_GCP_PROJECT_ID>,ARGUS_REGION=<YOUR_REGION>,ARGUS_VERTEX_LOCATION=us-central1,ARGUS_INSTANCE_CONNECTION_NAME=<YOUR_GCP_PROJECT_ID>:<YOUR_REGION>:argus-mysql-primary" \
    --set-secrets="ARGUS_DB_PASSWORD=argus-db-password:latest" \
    --timeout=900 \
    --memory=2Gi \
    --cpu=2 \
    --allow-unauthenticated \
    --project="<YOUR_GCP_PROJECT_ID>"
```

Retrieve the deployed backend URL:
```bash
BACKEND_URL=$(gcloud run services describe argus-backend --region="<YOUR_REGION>" --project="<YOUR_GCP_PROJECT_ID>" --format="value(status.url)")
```

Deploy the frontend UI:

```bash
gcloud run deploy argus-frontend \
    --image="<YOUR_REGION>-docker.pkg.dev/<YOUR_GCP_PROJECT_ID>/argus-repo/argus-frontend:latest" \
    --region="<YOUR_REGION>" \
    --set-env-vars="VITE_API_BASE_URL=${BACKEND_URL}" \
    --memory=512Mi \
    --allow-unauthenticated \
    --project="<YOUR_GCP_PROJECT_ID>"
```

### Step 10: Configure Eventarc & Pub/Sub Ingestion

Connect Cloud Storage finalize events to the backend webhook:

```bash
gcloud eventarc triggers create argus-gcs-finalize-trigger \
    --location="<YOUR_REGION>" \
    --destination-run-service="argus-backend" \
    --destination-run-path="/events/gcs" \
    --event-filters="type=google.cloud.storage.object.v1.finalized" \
    --event-filters="bucket=<YOUR_CALLS_BUCKET>" \
    --service-account="argus-eventarc-invoker-sa@<YOUR_GCP_PROJECT_ID>.iam.gserviceaccount.com" \
    --project="<YOUR_GCP_PROJECT_ID>"
```

---

## Service Accounts & IAM Roles Reference

| Service Account | Role Assigned | Purpose & Scope | Least-Privilege Assessment |
|---|---|---|---|
| `argus-backend-sa` | `roles/cloudsql.client` | Connects to Cloud SQL via unix domain socket | Least privilege for Cloud SQL proxy |
| `argus-backend-sa` | `roles/aiplatform.user` | Invokes Vertex AI Gemini Flash models | Required for prediction and token counting |
| `argus-backend-sa` | `roles/dlp.user` | De-identifies text using Sensitive Data Protection | Scoped to project content inspection |
| `argus-backend-sa` | `roles/cloudtrace.agent` | Exports OpenTelemetry traces to Cloud Trace | Write-only telemetry ingestion |
| `argus-backend-sa` | `roles/logging.logWriter` | Emits structured JSON logs to Cloud Logging | Standard logging agent role |
| `argus-backend-sa` | `roles/secretmanager.secretAccessor` | Reads database passwords and JWT secrets | Read-only secret payload access |
| `argus-backend-sa` | `roles/storage.objectAdmin` | Reads, writes, moves audio in calls/regulations buckets | Scoped to individual bucket boundaries |
| `argus-eventarc-invoker-sa` | `roles/run.invoker` | Pushes authenticated OIDC requests to `/events/gcs` | Strictly limited to invoking `argus-backend` |

---

## Vertex AI Location Configuration

To balance model quota availability and data residency:
- **Cloud SQL, Cloud Storage, Cloud Run:** Hosted in `asia-south1` (Mumbai) to comply with Indian BFSI data localization norms.
- **Vertex AI Endpoint:** Configured via `ARGUS_VERTEX_LOCATION=us-central1`. The backend allows the model endpoint region to be configured independently from the storage region, preventing model availability bottlenecks during judging periods.

---

## Post-Deployment Health Checks

After deployment completes:

1. **Service Probe:**
   ```bash
   curl -s "${BACKEND_URL}/health"
   # Expected: {"status": "ok", "service": "argus-backend", "version": "1.0.0", "mock_mode": false}
   ```
2. **System Health & Dependency Latency:**
   ```bash
   curl -s "${BACKEND_URL}/api/system/health"
   # Verify database.status == "connected" and object_store.status == "connected"
   ```
3. **Frontend Ingress:** Open the frontend URL in a browser and verify that the login page loads with active audio waveforms.

---

## Cost Control & Resource Teardown

To avoid ongoing charges after judging:
1. Cloud Run services scale to zero automatically when idle.
2. To permanently delete billable Cloud SQL and Cloud Run instances, execute [`../infra/teardown.sh`](../infra/teardown.sh):
   ```bash
   bash infra/teardown.sh
   ```
   This deletes `argus-backend`, `argus-frontend`, `argus-gcs-finalize-trigger`, and `argus-mysql-primary`.

---

## Related Documents

- [Configuration Reference](./CONFIGURATION.md)
- [Security & Governance](./SECURITY.md)
- [Observability Architecture](./OBSERVABILITY.md)
- [Testing & Benchmark](./TESTING.md)
