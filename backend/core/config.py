"""
ARGUS — Core Configuration & Environment Management (backend/core/config.py)

Manages all runtime configuration, model IDs, service account bindings,
feature flags, and dual-provider mode switches (mock vs live).
Never hardcodes model IDs, project IDs, or secrets.
"""

import os
import json
from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory of the repository
ROOT_DIR = Path(__file__).resolve().parents[2]
BASE_DIR = ROOT_DIR


class ArgusSettings(BaseSettings):
    """
    Central application settings for ARGUS.
    Environment variables prefixed with ARGUS_ override these defaults.
    """
    model_config = SettingsConfigDict(
        env_prefix="ARGUS_",
        env_file=[str(ROOT_DIR / ".env"), str(ROOT_DIR / "backend" / ".env")],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Base repository directory
    BASE_DIR: Path = Field(default=ROOT_DIR, description="Root directory of ARGUS project")

    # Core Environment & Execution Mode
    PROVIDER_MODE: str = Field(
        default="mock",
        description="Selects provider adapter implementation: 'mock' (offline) or 'live' (Vertex AI / GCP)",
    )
    ENVIRONMENT: str = Field(default="development", description="development | staging | production")
    PROJECT_ID: str = Field(
        default_factory=lambda: os.getenv("ARGUS_PROJECT_ID", "your-gcp-project-id"),
        description="GCP Project ID"
    )
    PROJECT_NAME: str = Field(
        default_factory=lambda: os.getenv("ARGUS_PROJECT_NAME", "argus-compliance-prod"),
        description="GCP Project Name"
    )
    PROJECT_NUMBER: str = Field(
        default_factory=lambda: os.getenv("ARGUS_PROJECT_NUMBER", "000000000000"),
        description="GCP Project Number"
    )
    REGION: str = Field(default="asia-south1", description="Default GCP region (Mumbai for Cloud SQL/GCS)")
    VERTEX_LOCATION: str = Field(
        default_factory=lambda: os.getenv("ARGUS_VERTEX_LOCATION", os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")),
        description="Vertex AI model endpoint location (configurable separately from resource region)",
    )

    # Model Identifiers (Configurable — never hardcoded)
    GEMINI_FLASH_MODEL: str = Field(
        default_factory=lambda: os.getenv("ARGUS_GEMINI_FLASH_MODEL", "gemini-3.5-flash"),
        description="Model ID for detection, investigation, chat, and general reasoning"
    )

    GEMINI_TRANSCRIBE_MODEL: str = Field(
        default_factory=lambda: os.getenv("ARGUS_GEMINI_TRANSCRIBE_MODEL", "gemini-3.5-flash"),
        description="Model ID for audio transcription & diarization"
    )

    GEMINI_ROLE_MAPPING_MODEL: str = Field(
        default_factory=lambda: os.getenv("ARGUS_GEMINI_ROLE_MAPPING_MODEL", "gemini-2.5-flash"),
        description="Model ID for speaker label finding & role mapping"
    )

    # Cloud Storage Buckets
    CALLS_BUCKET: str = Field(
        default_factory=lambda: os.getenv("ARGUS_CALLS_BUCKET", "project-c5373081-153f-4b0a-bd8-argus-calls"),
        description="GCS Bucket for incoming and archived calls"
    )
    REGULATIONS_BUCKET: str = Field(
        default_factory=lambda: os.getenv("ARGUS_REGULATIONS_BUCKET", "project-c5373081-153f-4b0a-bd8-argus-regulations"),
        description="GCS Bucket for statutory regulation PDFs and metadata"
    )

    # Local Storage Root (Used in mock mode)
    STORAGE_LOCAL_ROOT: Path = Field(
        default=ROOT_DIR / "data" / "storage",
        description="Local folder path simulating GCS bucket layout in mock mode",
    )

    # Database Configuration (Cloud SQL for MySQL)
    DB_USER: str = Field(default_factory=lambda: os.getenv("ARGUS_DB_USER", os.getenv("MYSQL_USER", "root")), description="Database user")
    DB_PASSWORD: str = Field(default_factory=lambda: os.getenv("ARGUS_DB_PASSWORD", os.getenv("MYSQL_PASSWORD", "qwerty12345")), description="Database password")
    DB_NAME: str = Field(default_factory=lambda: os.getenv("ARGUS_DB_NAME", "argus"), description="Database name")
    DB_HOST: str = Field(default_factory=lambda: os.getenv("ARGUS_DB_HOST", os.getenv("MYSQL_HOST", "127.0.0.1")), description="Database host (local proxy or container)")
    DB_PORT: int = Field(default_factory=lambda: int(os.getenv("ARGUS_DB_PORT", os.getenv("MYSQL_PORT", 3306))), description="Database port")
    INSTANCE_CONNECTION_NAME: Optional[str] = Field(
        default_factory=lambda: os.getenv("ARGUS_INSTANCE_CONNECTION_NAME", None),
        description="Cloud SQL instance connection name (e.g. project:region:instance) for Cloud SQL Connector",
    )
    DB_IS_MOCK: bool = Field(
        default_factory=lambda: os.getenv("ARGUS_DB_IS_MOCK", "false").lower() in ("true", "1", "yes") if os.getenv("ARGUS_PROVIDER_MODE", "live") == "live" else os.getenv("ARGUS_DB_IS_MOCK", "true").lower() in ("true", "1", "yes"),
        description="Safety flag to prevent mock data writes to live DB"
    )

    # Regulatory File Search Configuration
    FS_STRATEGY: str = Field(default="chunks", description="File Search strategy: 'chunks' (Strategy A) or 'pdf' (Strategy B)")
    FS_AUTH_MODE: str = Field(default="vertex", description="'vertex' (ADC) or 'api_key'")
    GEMINI_API_KEY: Optional[str] = Field(default=None, description="Optional Gemini API Key for File Search if required")
    FILE_SEARCH_STORE_NAME: str = Field(default="argus-regulation-store", description="Name/ID of File Search store")

    # Feature Flags
    DLP_ENABLED: bool = Field(default=True, description="Enable Sensitive Data Protection (PII redaction)")
    MODEL_ARMOR_ENABLED: bool = Field(default=False, description="Tier 3: Model Armor prompt screening")
    FIREBASE_AUTH_ENABLED: bool = Field(default=False, description="Tier 3: Firebase Authentication for API users")
    CLOUD_TASKS_ENABLED: bool = Field(default=False, description="Tier 3: Cloud Tasks async dispatch")

    # Security & Pub/Sub Ingestion
    OIDC_AUDIENCE: str = Field(
        default_factory=lambda: os.getenv("ARGUS_OIDC_AUDIENCE", "https://argus-backend-cloudrun-url"),
        description="Expected OIDC token audience"
    )
    ALLOWED_SERVICE_ACCOUNTS: List[str] = Field(
        default_factory=lambda: [
            sa.strip() for sa in os.getenv(
                "ARGUS_ALLOWED_SERVICE_ACCOUNTS",
                "argus-eventarc-invoker-sa@your-gcp-project-id.iam.gserviceaccount.com,eventarc-invoker@your-gcp-project-id.iam.gserviceaccount.com"
            ).strip("[]").replace('"', "").replace("'", "").split(",") if sa.strip()
        ],
        description="Service account emails authorized to push GCS finalize events",
    )

    # Observability & Tracing
    TRACE_ENABLED: bool = Field(default=True, description="Enable OpenTelemetry tracing to Google Cloud Trace")
    CLOUD_TRACE_DEEP_LINK_TEMPLATE: str = Field(
        default="https://console.cloud.google.com/traces/explorer?project={project_id}&tid={trace_id}",
        description="Deep link template to Google Cloud Trace Explorer",
    )

    # CORS
    CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: [
            origin.strip() for origin in os.getenv(
                "ARGUS_CORS_ORIGINS",
                "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"
            ).strip("[]").replace('"', "").replace("'", "").split(",") if origin.strip()
        ],
        description="Allowed CORS origins for the frontend",
    )

    def is_mock(self) -> bool:
        return self.PROVIDER_MODE.lower() == "mock"


# Singleton instance
settings = ArgusSettings()
