"""
ARGUS — Storage Layer Adapter (backend/adapters/storage.py)

Provides unified ObjectStore interface with:
- Live implementation using Google Cloud Storage (google-cloud-storage)
- Mock implementation using a local filesystem folder structure
- HTTP Range streaming support for WaveSurfer audio seek
"""

import io
import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Generator, List, Optional, Tuple

from backend.core.config import settings


class ObjectMetadata:
    def __init__(self, name: str, size: int, updated_at: str, generation: str = "1", content_type: str = "audio/wav"):
        self.name = name
        self.size = size
        self.updated_at = updated_at
        self.generation = generation
        self.content_type = content_type

    @property
    def size_bytes(self) -> int:
        return self.size


class ObjectStore(ABC):
    """Abstract interface for object storage operations."""

    @abstractmethod
    def list_objects(self, prefix: str) -> List[str]:
        """List object keys matching prefix."""
        pass

    @abstractmethod
    def read_bytes(self, key: str) -> bytes:
        """Read full object content as bytes."""
        pass

    @abstractmethod
    def read_range(self, key: str, start: int, length: int) -> bytes:
        """Read byte range for HTTP Range requests."""
        pass

    @abstractmethod
    def upload_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Upload raw bytes to key and return object URI."""
        pass

    @abstractmethod
    def upload_file(self, key: str, local_file_path: Path, content_type: Optional[str] = None) -> str:
        """Upload local file to key and return object URI."""
        pass

    @abstractmethod
    def copy_object(self, source_key: str, dest_key: str) -> str:
        """Copy object from source_key to dest_key."""
        pass

    @abstractmethod
    def delete_object(self, key: str) -> bool:
        """Delete object at key."""
        pass

    @abstractmethod
    def get_metadata(self, key: str) -> Optional[ObjectMetadata]:
        """Retrieve object metadata."""
        pass

    @abstractmethod
    def get_uri(self, key: str) -> str:
        """Get canonical storage URI (gs:// or file://)."""
        pass

    def download_bytes(self, key: str) -> bytes:
        return self.read_bytes(key)

    def download_range(self, key: str, start_byte: int, end_byte: int) -> bytes:
        length = end_byte - start_byte + 1
        return self.read_range(key, start_byte, length)

    def move_object(self, source_key: str, dest_key: str) -> str:
        uri = self.copy_object(source_key, dest_key)
        self.delete_object(source_key)
        return uri

    def exists(self, key: str) -> bool:
        return self.get_metadata(key) is not None


class LocalObjectStore(ObjectStore):
    """
    Mock ObjectStore using the local filesystem.
    Mirrors GCS layout: calls/incoming/, calls/archive/, regulations/.
    """

    def __init__(self, root_dir: Optional[Path] = None):
        if not settings.is_mock():
            raise RuntimeError(
                f"ABSOLUTE RULE 1 VIOLATION: Mock adapter 'LocalObjectStore' instantiated "
                f"while ARGUS_PROVIDER_MODE='{settings.PROVIDER_MODE}'. Mock usage is strictly prohibited in live mode!"
            )
        self.root = root_dir or settings.STORAGE_LOCAL_ROOT
        self._ensure_layout()

    def _ensure_layout(self):
        (self.root / "calls" / "incoming").mkdir(parents=True, exist_ok=True)
        (self.root / "calls" / "archive").mkdir(parents=True, exist_ok=True)
        (self.root / "regulations").mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        clean_key = key.lstrip("/").replace("gs://", "").replace(f"{settings.CALLS_BUCKET}/", "").replace(f"{settings.REGULATIONS_BUCKET}/", "")
        return (self.root / clean_key).resolve()

    def list_objects(self, prefix: str) -> List[str]:
        target_dir = self._resolve(prefix)
        if not target_dir.exists():
            return []
        if target_dir.is_file():
            return [prefix]
        results = []
        for p in target_dir.rglob("*"):
            if p.is_file():
                rel = p.relative_to(self.root).as_posix()
                results.append(rel)
        return results

    def read_bytes(self, key: str) -> bytes:
        p = self._resolve(key)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"Mock ObjectStore: key not found '{key}' at {p}")
        with open(p, "rb") as f:
            return f.read()

    def read_range(self, key: str, start: int, length: int) -> bytes:
        p = self._resolve(key)
        if not p.exists():
            raise FileNotFoundError(f"Mock ObjectStore: key not found '{key}'")
        with open(p, "rb") as f:
            f.seek(start)
            return f.read(length)

    def upload_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        p = self._resolve(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "wb") as f:
            f.write(data)
        return self.get_uri(key)

    def upload_file(self, key: str, local_file_path: Path, content_type: Optional[str] = None) -> str:
        p = self._resolve(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_file_path, p)
        return self.get_uri(key)

    def copy_object(self, source_key: str, dest_key: str) -> str:
        src = self._resolve(source_key)
        dst = self._resolve(dest_key)
        if not src.exists():
            raise FileNotFoundError(f"Cannot copy non-existent source '{source_key}'")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return self.get_uri(dest_key)

    def delete_object(self, key: str) -> bool:
        p = self._resolve(key)
        if p.exists() and p.is_file():
            p.unlink()
            return True
        return False

    def get_metadata(self, key: str) -> Optional[ObjectMetadata]:
        p = self._resolve(key)
        if not p.exists() or not p.is_file():
            return None
        stat = p.stat()
        return ObjectMetadata(
            name=p.name,
            size=stat.st_size,
            updated_at=str(stat.st_mtime),
            generation=str(int(stat.st_mtime)),
            content_type="audio/wav" if p.suffix.lower() == ".wav" else "application/pdf" if p.suffix.lower() == ".pdf" else "application/octet-stream"
        )

    def get_uri(self, key: str) -> str:
        clean = key.lstrip("/").replace("gs://", "")
        return f"mock://{clean}"


class GCSObjectStore(ObjectStore):
    """
    Live ObjectStore adapter utilizing Google Cloud Storage.
    Uses Application Default Credentials (ADC).
    """

    def __init__(self, bucket_name: Optional[str] = None):
        self.bucket_name = bucket_name or settings.CALLS_BUCKET
        self._client = None

    def _get_client(self):
        # TODO(PHASE2-VERIFY): Verify ADC authentication from Cloud Run to Google Cloud Storage
        if self._client is None:
            try:
                from google.cloud import storage
                self._client = storage.Client(project=settings.PROJECT_ID)
            except Exception as exc:
                raise RuntimeError(f"GCSObjectStore requires google-cloud-storage and ADC credentials: {exc}")
        return self._client

    def _get_bucket(self):
        return self._get_client().bucket(self.bucket_name)

    def list_objects(self, prefix: str) -> List[str]:
        blobs = self._get_bucket().list_blobs(prefix=prefix)
        return [b.name for b in blobs]

    def read_bytes(self, key: str) -> bytes:
        blob = self._get_bucket().blob(key)
        return blob.download_as_bytes()

    def read_range(self, key: str, start: int, length: int) -> bytes:
        blob = self._get_bucket().blob(key)
        end = start + length - 1
        return blob.download_as_bytes(start=start, end=end)

    def upload_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        blob = self._get_bucket().blob(key)
        blob.upload_from_string(data, content_type=content_type)
        return self.get_uri(key)

    def upload_file(self, key: str, local_file_path: Path, content_type: Optional[str] = None) -> str:
        blob = self._get_bucket().blob(key)
        blob.upload_from_filename(str(local_file_path), content_type=content_type)
        return self.get_uri(key)

    def copy_object(self, source_key: str, dest_key: str) -> str:
        bucket = self._get_bucket()
        source_blob = bucket.blob(source_key)
        bucket.copy_blob(source_blob, bucket, dest_key)
        return self.get_uri(dest_key)

    def delete_object(self, key: str) -> bool:
        blob = self._get_bucket().blob(key)
        if blob.exists():
            blob.delete()
            return True
        return False

    def get_metadata(self, key: str) -> Optional[ObjectMetadata]:
        blob = self._get_bucket().get_blob(key)
        if not blob:
            return None
        return ObjectMetadata(
            name=blob.name,
            size=blob.size or 0,
            updated_at=blob.updated.isoformat() if blob.updated else "",
            generation=str(blob.generation or 1),
            content_type=blob.content_type or "application/octet-stream",
        )

    def get_uri(self, key: str) -> str:
        return f"gs://{self.bucket_name}/{key.lstrip('/')}"


def get_object_store() -> ObjectStore:
    """Factory creating ObjectStore based on ARGUS_PROVIDER_MODE."""
    if settings.is_mock():
        return LocalObjectStore()
    return GCSObjectStore()
