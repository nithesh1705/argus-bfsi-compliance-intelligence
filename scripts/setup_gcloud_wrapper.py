"""
ARGUS — Windows GCloud Wrapper Utility (scripts/setup_gcloud_wrapper.py)
Creates a wrapper script in Python Scripts directory pointing to Google Cloud SDK gcloud.cmd.
Dynamically resolves paths from environment variables.
"""

import os
import sys
from pathlib import Path

def setup_wrapper():
    local_appdata = os.getenv("LOCALAPPDATA", "")
    target = os.getenv(
        "GCLOUD_CMD_PATH",
        str(Path(local_appdata) / "Google" / "Cloud SDK" / "google-cloud-sdk" / "bin" / "gcloud.cmd") if local_appdata else "gcloud.cmd"
    )
    
    python_scripts = Path(sys.executable).parent / "Scripts"
    p = python_scripts / "gcloud.cmd"
    
    if Path(target).exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f'@"{target}" %*\n', encoding="utf-8")
        print(f"[OK] gcloud wrapper created at: {p} -> {target}")
    else:
        print(f"[INFO] Target gcloud.cmd not found at {target}. Wrapper skipped.")

if __name__ == "__main__":
    setup_wrapper()
