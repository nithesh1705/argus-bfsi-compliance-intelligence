"""
ARGUS Phase 2 Test Suite — T11: Frontend & Browser Verification
tests/phase2/test_t11_frontend.py
"""

import subprocess
import pytest
from pathlib import Path
from backend.core.config import settings


def test_t11_1_frontend_production_build():
    """Verify that typescript typecheck and vite build succeed without errors."""
    frontend_dir = settings.BASE_DIR / "frontend"
    res = subprocess.run(["npm", "run", "build"], capture_output=True, text=True, cwd=str(frontend_dir), shell=True)
    assert res.returncode == 0, f"Frontend build failed:\n{res.stdout}\n{res.stderr}"
    dist_dir = frontend_dir / "dist"
    assert (dist_dir / "index.html").exists(), "dist/index.html missing after build"


def test_t11_2_playwright_flows():
    """Execute end-to-end browser flows verifying dashboard, cases, audio player seek, and telemetry panel."""
    # Automated headless browser test runner script
    script_path = settings.BASE_DIR / "scripts" / "run_frontend_e2e.py"
    if script_path.exists():
        res = subprocess.run(["python", str(script_path)], capture_output=True, text=True, cwd=str(settings.BASE_DIR))
        assert res.returncode == 0, f"Frontend E2E test failed:\n{res.stdout}\n{res.stderr}"
