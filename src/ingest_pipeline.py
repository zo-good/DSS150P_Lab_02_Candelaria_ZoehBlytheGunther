"""Week 3 starter: rerunnable ingestion to a raw area.
Students implement file ingestion + paginated REST API ingestion + watermark + duplicate prevention.
"""
from pathlib import Path
from datetime import datetime, timezone
import json, hashlib, shutil
import requests

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'; RAW=ROOT/'raw'; STATE=ROOT/'state'
API_URL='http://127.0.0.1:8000/api/events'

def utc_now(): return datetime.now(timezone.utc).isoformat()

def sha256_file(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def load_watermark():
    p=STATE/'api_watermark.json'
    if not p.exists(): return None
    return json.loads(p.read_text())['updated_at']

def save_watermark(value):
    STATE.mkdir(exist_ok=True)
    (STATE/'api_watermark.json').write_text(json.dumps({'updated_at':value},indent=2))

def ingest_files():
    files_dir = RAW/'files'
    files_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = files_dir/'manifest.json'

    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
    else:
        manifest = []

    already_ingested_hashes = {entry['sha256'] for entry in manifest}

    source_files = ['customers.csv', 'orders.json', 'products.parquet']

    for filename in source_files:
        source_path = DATA/filename
        file_hash = sha256_file(source_path)
        file_size = source_path.stat().st_size

        if file_hash in already_ingested_hashes:
            print(f"SKIP {filename}: content hash already ingested, nothing changed")
            continue

        dest_path = files_dir/filename
        shutil.copy2(source_path, dest_path)

        manifest.append({
            'source_file': filename,
            'ingested_at': utc_now(),
            'sha256': file_hash,
            'bytes': file_size,
        })
        already_ingested_hashes.add(file_hash)
        print(f"COPIED {filename} -> raw/files/{filename} (sha256={file_hash[:12]}...)")

    manifest_path.write_text(json.dumps(manifest, indent=2))

def fetch_api_page(page, per_page=20, updated_after=None):
    params={'page':page,'per_page':per_page}
    if updated_after: params['updated_after']=updated_after
    r=requests.get(API_URL,params=params,timeout=30); r.raise_for_status(); return r.json()

def ingest_api():
    # TODO:
    # 1) read watermark
    # 2) follow pagination until has_more=False
    # 3) append ingestion metadata (_ingested_at, _source)
    # 4) deduplicate by event_id keeping greatest updated_at
    # 5) write raw/api/events.jsonl atomically
    # 6) update watermark only after successful write
    pass

if __name__=='__main__':
    RAW.mkdir(exist_ok=True); STATE.mkdir(exist_ok=True)
    ingest_files(); ingest_api()
