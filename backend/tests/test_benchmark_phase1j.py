"""
ARGUS — Benchmark & Phase 1J Unit Tests (backend/tests/test_benchmark_phase1j.py)
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.benchmark.run_benchmark import run_benchmark_evaluation, CALL_9_ID

client = TestClient(app)


def test_benchmark_evaluation_structure_and_metrics():
    """Verify that the three-way benchmark runs and computes all metrics accurately."""
    report = run_benchmark_evaluation()

    assert report is not None
    assert "comparative_metrics" in report
    metrics = report["comparative_metrics"]

    assert "keyword_baseline" in metrics
    assert "gemini_detection_only" in metrics
    assert "full_argus_pipeline" in metrics

    # Verify each system contains valid precision, recall, F1
    for key in ["keyword_baseline", "gemini_detection_only", "full_argus_pipeline"]:
        sys_metric = metrics[key]
        assert "precision" in sys_metric
        assert "recall" in sys_metric
        assert "f1" in sys_metric
        assert 0.0 <= sys_metric["precision"] <= 1.0
        assert 0.0 <= sys_metric["recall"] <= 1.0
        assert 0.0 <= sys_metric["f1"] <= 1.0

    # Call 9 must be excluded and analyzed separately
    assert "call_9_analysis" in report
    assert report["call_9_analysis"]["call_id"] == CALL_9_ID

    # Stage latencies must exist
    assert "stage_latency_diagnostics" in report
    timings = report["stage_latency_diagnostics"]
    assert len(timings) > 0


def test_benchmark_api_endpoint():
    """Verify GET /api/benchmark returns 200 OK and valid report JSON."""
    response = client.get("/api/benchmark")
    assert response.status_code == 200
    data = response.json()
    assert "comparative_metrics" in data
    assert "full_argus_pipeline" in data["comparative_metrics"]
    assert data["mock_mode"] is True
