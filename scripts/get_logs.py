import subprocess
import json

cmd = 'gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=argus-backend" --limit=100 --format=json'
out = subprocess.check_output(cmd, shell=True, text=True, encoding="utf-8")
logs = json.loads(out)
for entry in reversed(logs):
    ts = entry.get('timestamp')
    msg = entry.get('textPayload') or entry.get('jsonPayload', {}).get('message', '')
    if msg:
        print(f"{ts} | {msg.strip()}")
