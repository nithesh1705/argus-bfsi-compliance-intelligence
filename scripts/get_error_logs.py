import subprocess
import json

cmd = 'gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=argus-backend AND severity>=WARNING" --limit=50 --format=json'
out = subprocess.check_output(cmd, shell=True, text=True, encoding="utf-8")
logs = json.loads(out)
for entry in reversed(logs):
    ts = entry.get('timestamp')
    sev = entry.get('severity')
    msg = entry.get('textPayload') or entry.get('jsonPayload', {}).get('message', '')
    print(f"{ts} [{sev}] | {msg.strip() if msg else ''}")
