import subprocess
import json

cmd = 'gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=argus-backend AND logName:\"run.googleapis.com\"" --limit=30 --format=json'
out = subprocess.check_output(cmd, shell=True, text=True, encoding="utf-8")
logs = json.loads(out)
for entry in reversed(logs):
    ts = entry.get('timestamp')
    msg = entry.get('textPayload') or entry.get('jsonPayload')
    print(f"{ts} | {msg}")
