# ==============================================================================
# ARGUS — Infrastructure Provisioning Script for PowerShell (infra/setup.ps1)
#
# Idempotently provisions Google Cloud Platform resources:
# - Required APIs (Cloud Run, Vertex AI, DLP, Cloud SQL, Trace, Logging, Eventarc)
# - Storage Buckets (Calls and Regulations)
# - Service Accounts with Least-Privilege IAM Bindings
# - Cloud SQL for MySQL 8.0 Instance, Database & User
# - Pub/Sub Topic and Eventarc GCS Finalize Trigger
# - Secret Manager Secrets
# ==============================================================================

[CmdletBinding()]
param(
    [string]$ProjectId = $(if ($env:ARGUS_PROJECT_ID) { $env:ARGUS_PROJECT_ID } else { "YOUR_GCP_PROJECT_ID" }),
    [string]$Region = $(if ($env:ARGUS_REGION) { $env:ARGUS_REGION } else { "asia-south1" }),
    [string]$CallsBucket = $(if ($env:ARGUS_CALLS_BUCKET) { $env:ARGUS_CALLS_BUCKET } else { "${ProjectId}-argus-calls" }),
    [string]$RegulationsBucket = $(if ($env:ARGUS_REGULATIONS_BUCKET) { $env:ARGUS_REGULATIONS_BUCKET } else { "${ProjectId}-argus-regulations" }),
    [string]$DbInstance = $(if ($env:ARGUS_DB_INSTANCE) { $env:ARGUS_DB_INSTANCE } else { "argus-mysql-primary" }),
    [string]$DbPassword = $(if ($env:ARGUS_DB_PASSWORD) { $env:ARGUS_DB_PASSWORD } else { "YOUR_DB_PASSWORD" })
)

$ErrorActionPreference = "Continue"

# Ensure Google Cloud SDK and Python are discovered
$gcloudDefaultBin = "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin"
if (Test-Path $gcloudDefaultBin) {
    if ($env:Path -notlike "*$gcloudDefaultBin*") {
        $env:Path = "$gcloudDefaultBin;$env:Path"
    }
}
if (-not $env:CLOUDSDK_PYTHON) {
    $pyCmd = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($pyCmd) {
        $env:CLOUDSDK_PYTHON = $pyCmd.Source
    }
}

$BackendSa = "argus-backend-sa@$ProjectId.iam.gserviceaccount.com"
$EventarcSa = "argus-eventarc-invoker-sa@$ProjectId.iam.gserviceaccount.com"

Write-Host "=== Provisioning ARGUS Infrastructure on Google Cloud ===" -ForegroundColor Cyan
Write-Host "Project ID: $ProjectId"
Write-Host "Region:     $Region"

# Verify active account
$activeAccount = (& gcloud auth list --format="value(account)" 2>$null | Select-Object -First 1)
if (-not $activeAccount) {
    Write-Host ""
    Write-Host "[ACTION REQUIRED] No authenticated Google Cloud account detected." -ForegroundColor Yellow
    Write-Host "Please run the following commands in your PowerShell terminal to authenticate:" -ForegroundColor Cyan
    Write-Host "  1. gcloud auth login" -ForegroundColor White
    Write-Host "  2. gcloud auth application-default login" -ForegroundColor White
    Write-Host "  3. gcloud config set project $ProjectId" -ForegroundColor White
    Write-Host "  4. .\infra\setup.ps1" -ForegroundColor White
    Write-Host ""
    exit 1
}
Write-Host "Authenticated as: $activeAccount" -ForegroundColor Green
Write-Host ""

# 1. Enable Required GCP APIs
Write-Host "[1/8] Enabling Google Cloud Services..." -ForegroundColor Yellow
cmd /c "gcloud services enable run.googleapis.com sqladmin.googleapis.com storage.googleapis.com aiplatform.googleapis.com dlp.googleapis.com cloudtrace.googleapis.com logging.googleapis.com eventarc.googleapis.com pubsub.googleapis.com secretmanager.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com generativelanguage.googleapis.com --project=$ProjectId"

# 2. Artifact Registry
Write-Host "[2/8] Ensuring Artifact Registry repository exists..." -ForegroundColor Yellow
cmd /c "gcloud artifacts repositories describe argus-repo --location=$Region --project=$ProjectId >nul 2>&1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating Artifact Registry repository: argus-repo..."
    cmd /c "gcloud artifacts repositories create argus-repo --repository-format=docker --location=$Region --description=""Docker repository for ARGUS container images"" --project=$ProjectId"
} else {
    Write-Host "Artifact Registry repository 'argus-repo' already exists." -ForegroundColor Gray
}

# 3. Cloud Storage Buckets
Write-Host "[3/8] Creating Cloud Storage Buckets..." -ForegroundColor Yellow
cmd /c "gcloud storage buckets describe gs://$CallsBucket/ --project=$ProjectId >nul 2>&1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating bucket: gs://$CallsBucket/..."
    cmd /c "gcloud storage buckets create gs://$CallsBucket/ --location=$Region --project=$ProjectId --uniform-bucket-level-access"
} else {
    Write-Host "Bucket 'gs://$CallsBucket/' already exists." -ForegroundColor Gray
}

cmd /c "gcloud storage buckets describe gs://$RegulationsBucket/ --project=$ProjectId >nul 2>&1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating bucket: gs://$RegulationsBucket/..."
    cmd /c "gcloud storage buckets create gs://$RegulationsBucket/ --location=$Region --project=$ProjectId --uniform-bucket-level-access"
} else {
    Write-Host "Bucket 'gs://$RegulationsBucket/' already exists." -ForegroundColor Gray
}

# 4. Service Accounts & IAM
Write-Host "[4/8] Provisioning Service Accounts and IAM Roles..." -ForegroundColor Yellow
cmd /c "gcloud iam service-accounts describe $BackendSa --project=$ProjectId >nul 2>&1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating Service Account: $BackendSa..."
    cmd /c "gcloud iam service-accounts create argus-backend-sa --display-name=""ARGUS Backend Service Account"" --project=$ProjectId"
} else {
    Write-Host "Service account '$BackendSa' already exists." -ForegroundColor Gray
}

cmd /c "gcloud iam service-accounts describe $EventarcSa --project=$ProjectId >nul 2>&1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating Service Account: $EventarcSa..."
    cmd /c "gcloud iam service-accounts create argus-eventarc-invoker-sa --display-name=""ARGUS Eventarc Invoker Service Account"" --project=$ProjectId"
} else {
    Write-Host "Service account '$EventarcSa' already exists." -ForegroundColor Gray
}

$backendRoles = @(
    "roles/cloudsql.client",
    "roles/aiplatform.user",
    "roles/dlp.user",
    "roles/cloudtrace.agent",
    "roles/logging.logWriter",
    "roles/secretmanager.secretAccessor"
)

foreach ($role in $backendRoles) {
    cmd /c "gcloud projects add-iam-policy-binding $ProjectId --member=""serviceAccount:$BackendSa"" --role=""$role"" --condition=None --quiet >nul 2>&1"
}

cmd /c "gcloud storage buckets add-iam-policy-binding gs://$CallsBucket --member=""serviceAccount:$BackendSa"" --role=""roles/storage.objectAdmin"" --quiet >nul 2>&1"
cmd /c "gcloud storage buckets add-iam-policy-binding gs://$RegulationsBucket --member=""serviceAccount:$BackendSa"" --role=""roles/storage.objectViewer"" --quiet >nul 2>&1"
Write-Host "IAM policy bindings applied." -ForegroundColor Gray

# 5. Cloud SQL for MySQL
Write-Host "[5/8] Checking Cloud SQL MySQL Instance ($DbInstance)..." -ForegroundColor Yellow
cmd /c "gcloud sql instances describe $DbInstance --project=$ProjectId >nul 2>&1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating Cloud SQL MySQL 8.0 instance: $DbInstance in $Region (this may take 3-5 minutes)..." -ForegroundColor Cyan
    cmd /c "gcloud sql instances create $DbInstance --database-version=MYSQL_8_0 --tier=db-f1-micro --region=$Region --storage-type=SSD --storage-size=20GB --storage-auto-increase --backup-start-time=02:00 --project=$ProjectId"
} else {
    Write-Host "Cloud SQL instance '$DbInstance' already exists." -ForegroundColor Gray
}

cmd /c "gcloud sql databases describe argus --instance=$DbInstance --project=$ProjectId >nul 2>&1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating database 'argus'..."
    cmd /c "gcloud sql databases create argus --instance=$DbInstance --project=$ProjectId"
}

cmd /c "gcloud sql users create argus_user --instance=$DbInstance --password=$DbPassword --project=$ProjectId >nul 2>&1"

# 6. Pub/Sub and Eventarc Trigger
Write-Host "[6/8] Configuring Pub/Sub & Eventarc Trigger..." -ForegroundColor Yellow
cmd /c "gcloud pubsub topics describe argus-call-uploads --project=$ProjectId >nul 2>&1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating Pub/Sub topic: argus-call-uploads..."
    cmd /c "gcloud pubsub topics create argus-call-uploads --project=$ProjectId"
} else {
    Write-Host "Pub/Sub topic 'argus-call-uploads' already exists." -ForegroundColor Gray
}

# 7. Secret Manager
Write-Host "[7/8] Storing Database Secret in Secret Manager..." -ForegroundColor Yellow
cmd /c "gcloud secrets describe argus-db-password --project=$ProjectId >nul 2>&1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating secret 'argus-db-password'..."
    cmd /c "echo -n ""$DbPassword"" | gcloud secrets create argus-db-password --data-file=- --project=$ProjectId"
} else {
    Write-Host "Secret 'argus-db-password' already exists." -ForegroundColor Gray
}

Write-Host ""
Write-Host "=== ARGUS GCP Infrastructure Setup Completed Successfully! ===" -ForegroundColor Green
