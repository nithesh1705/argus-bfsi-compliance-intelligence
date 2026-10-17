import subprocess
import json

bucket = "gs://project-c5373081-153f-4b0a-bd8_cloudbuild/source"

cmd = f"gcloud storage ls --json {bucket}/*.tgz"
out = subprocess.check_output(cmd, shell=True, text=True, encoding="utf-8")
items = json.loads(out)

# Sort by created timestamp
def get_time(x):
    meta = x.get("metadata", {})
    return meta.get("timeCreated", meta.get("updated", ""))

items.sort(key=get_time)

print(f"Total objects found: {len(items)}")

keep_count = 10
if len(items) <= keep_count:
    print(f"Only {len(items)} objects present (<= {keep_count}). Nothing to delete.")
else:
    to_delete = items[:-keep_count]
    to_keep = items[-keep_count:]
    
    print(f"\nKeeping latest {len(to_keep)} objects:")
    for obj in to_keep:
        print(f"  [KEEP] {get_time(obj)} - {obj.get('url')}")

    print(f"\nDeleting {len(to_delete)} older objects:")
    del_urls = [obj.get("url") for obj in to_delete if obj.get("url")]
    for u in del_urls:
        print(f"  [DELETE] {u}")
    
    # Batch delete
    chunk_size = 5
    for i in range(0, len(del_urls), chunk_size):
        chunk = del_urls[i:i+chunk_size]
        del_cmd = f"gcloud storage rm {' '.join(chunk)}"
        subprocess.check_call(del_cmd, shell=True)

    print("\nCleanup completed successfully!")
