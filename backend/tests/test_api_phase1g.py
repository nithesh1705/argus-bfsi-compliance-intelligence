"""
ARGUS — Phase 1G API & Pipeline Integration Tests (backend/tests/test_api_phase1g.py)
"""

import base64
import json
import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_api_health_probe():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "argus-backend"
    assert data["mock_mode"] is True


def test_system_health():
    resp = client.get("/api/system/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["mock_mode"] is True
    assert "cloud_sql" in data["services"]
    assert "cloud_storage" in data["services"]
    assert "vertex_ai" in data["services"]
    assert data["active_models"]["flash"] == "gemini-3.5-flash"


def test_dashboard_summary():
    resp = client.get("/api/dashboard/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_calls" in data
    assert "severity_counts" in data
    assert "pipeline_latency" in data


def test_calls_list_and_detail():
    resp = client.get("/api/calls")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "items" in data

    if data["items"]:
        call_id = data["items"][0]["call_id"]
        detail_resp = client.get(f"/api/calls/{call_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["id"] == call_id
        assert "transcript" in detail


def test_audio_streaming_range():
    # Test audio streaming with range header on an existing call
    resp = client.get("/api/calls")
    items = resp.json().get("items", [])
    if items:
        call_id = items[0]["call_id"]
        # Full content
        full_res = client.get(f"/api/calls/{call_id}/audio")
        if full_res.status_code == 200:
            assert len(full_res.content) > 0

            # Partial content (bytes=0-10)
            range_res = client.get(f"/api/calls/{call_id}/audio", headers={"Range": "bytes=0-10"})
            assert range_res.status_code == 206
            assert len(range_res.content) == 11
            assert "bytes 0-10/" in range_res.headers.get("Content-Range", "")


def test_cases_workflow_and_conflicts():
    resp = client.get("/api/cases")
    assert resp.status_code == 200
    data = resp.json()
    items = data.get("items", [])
    if items:
        case_id = items[0]["case_id"]
        # Detail
        detail_resp = client.get(f"/api/cases/{case_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["case_id"] == case_id
        assert "finding" in detail

        # Add note
        note_resp = client.post(f"/api/cases/{case_id}/notes", json={"reviewer_id": "REV001", "notes": "Test review note"})
        assert note_resp.status_code == 200

        # Assign
        assign_resp = client.post(f"/api/cases/{case_id}/assign", json={"reviewer_id": "REV001", "assignee_reviewer_id": "REV002"})
        assert assign_resp.status_code == 200


def test_events_gcs_endpoint():
    # Simulated Eventarc Pub/Sub push message
    gcs_event_data = {
        "bucket": "argus-calls",
        "name": "calls/incoming/RM001_CUST001_20260310_1030.wav",
        "generation": "123456789"
    }
    b64_data = base64.b64encode(json.dumps(gcs_event_data).encode("utf-8")).decode("utf-8")

    payload = {
        "message": {
            "data": b64_data,
            "messageId": "msg-001",
            "publishTime": "2026-10-15T08:00:00Z"
        }
    }

    resp = client.post("/events/gcs", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACK_PROCESSED"


def test_chat_message_endpoint():
    payload = {
        "message": "Which SEBI regulations cover guaranteed returns for mutual funds?",
        "session_id": "session-test",
    }
    resp = client.post("/api/chat/message", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert "tools_called" in data
    assert "search_regulations" in data["tools_called"]
    assert len(data["grounded_results"]) > 0
