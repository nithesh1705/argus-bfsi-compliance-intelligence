"""
ARGUS — Live Login Probe Diagnostic (tests/results/diagnostics/test_live_login.py)
Diagnostic utility to verify live authentication endpoints and frontend reverse proxy.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import requests

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")
load_dotenv(ROOT / "backend" / ".env")

BACKEND_URL = os.getenv("ARGUS_BACKEND_URL", "https://argus-backend-YOUR_PROJECT_NUMBER.asia-south1.run.app")
FRONTEND_URL = os.getenv("ARGUS_FRONTEND_URL", "https://argus-frontend-YOUR_PROJECT_NUMBER.asia-south1.run.app")

def run_login_probe():
    for username, password in [('admin', 'admin12345'), ('audit_officer', 'ARGUS@Audit2026')]:
        try:
            r = requests.post(
                f'{BACKEND_URL}/api/auth/login',
                json={'username': username, 'password': password},
                timeout=10
            )
            print(f"Direct Backend Login [{username}]: Status {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                print(f"  + Access Token: {data['access_token'][:25]}...")
                print(f"  + User: {data['user']['username']} (Role: {data['user']['role']})")
            else:
                print(f"  - Error: {r.text}")
        except Exception as exc:
            print(f"Direct Backend Login [{username}] connection skipped: {exc}")

    # Test through frontend reverse proxy
    try:
        r_front = requests.post(
            f'{FRONTEND_URL}/api/auth/login',
            json={'username': 'admin', 'password': 'admin12345'},
            timeout=10
        )
        print(f"\nFrontend Reverse Proxy Login [admin]: Status {r_front.status_code}")
        if r_front.status_code == 200:
            data = r_front.json()
            print(f"  + Successfully logged in through Frontend URL!")
            print(f"  + User: {data['user']['username']} (Role: {data['user']['role']})")
    except Exception as exc:
        print(f"Frontend Reverse Proxy Login connection skipped: {exc}")

if __name__ == '__main__':
    run_login_probe()
