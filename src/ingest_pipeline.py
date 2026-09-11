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
    watermark = load_watermark()
    per_page = 20
    page = 1
    fetched_items = []

    while True:
        try:
            data = fetch_api_page(page, per_page=per_page, updated_after=watermark)
        except requests.exceptions.RequestException as e:
            print(f"ERROR: API request failed on page {page}: {e}")
            raise

        items = data['items']
        for item in items:
            item['_ingested_at'] = utc_now()
            item['_source'] = 'api:/api/events'
        fetched_items.extend(items)

        if not data['has_more']:
            break
        page = data['next_page']

    print(f"Fetched {len(fetched_items)} new record(s) from API (watermark={watermark})")

    raw_api_dir = RAW/'api'
    raw_api_dir.mkdir(parents=True, exist_ok=True)
    events_path = raw_api_dir/'events.jsonl'

    existing_items = []
    if events_path.exists():
        with events_path.open('r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    existing_items.append(json.loads(line))

    combined = existing_items + fetched_items
    best_by_id = {}
    for item in combined:
        eid = item['event_id']
        if eid not in best_by_id or item['updated_at'] > best_by_id[eid]['updated_at']:
            best_by_id[eid] = item
    deduped = list(best_by_id.values())
    duplicates_removed = len(combined) - len(deduped)

    tmp_path = events_path.with_suffix('.jsonl.tmp')
    with tmp_path.open('w', encoding='utf-8') as f:
        for item in deduped:
            f.write(json.dumps(item) + '\n')
    tmp_path.replace(events_path)

    print(f"Wrote {len(deduped)} deduplicated record(s) to raw/api/events.jsonl ({duplicates_removed} duplicate(s) removed)")

    if fetched_items:
        new_watermark = max(item['updated_at'] for item in fetched_items)
        if watermark is None or new_watermark > watermark:
            save_watermark(new_watermark)
            print(f"Watermark updated: {watermark} -> {new_watermark}")
    else:
        print("No new records fetched; watermark unchanged")

if __name__=='__main__':
   RAW.mkdir(exist_ok=True); STATE.mkdir(exist_ok=True)
   ingest_files(); ingest_api()
