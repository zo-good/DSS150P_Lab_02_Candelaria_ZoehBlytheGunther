"""Starter validation checks for raw outputs."""
from pathlib import Path
from datetime import datetime
import json
ROOT=Path(__file__).resolve().parents[1]

def check(condition, message, results):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {message}")
    results.append(condition)

def main():
    results = []

    files_dir = ROOT/'raw'/'files'
    manifest_path = files_dir/'manifest.json'
    events_path = ROOT/'raw'/'api'/'events.jsonl'
    watermark_path = ROOT/'state'/'api_watermark.json'

    check((files_dir/'customers.csv').exists(), "raw/files/customers.csv exists", results)
    check((files_dir/'orders.json').exists(), "raw/files/orders.json exists", results)
    check((files_dir/'products.parquet').exists(), "raw/files/products.parquet exists", results)
    check(manifest_path.exists(), "raw/files/manifest.json exists", results)
    check(events_path.exists(), "raw/api/events.jsonl exists", results)

    max_updated_at = None
    if events_path.exists():
        events = []
        with events_path.open('r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))

        event_ids = [e.get('event_id') for e in events]
        check(len(event_ids) == len(set(event_ids)),
              f"All {len(event_ids)} event_id values are unique", results)

        required_fields = ['event_id', 'customer_id', 'event_type', 'amount', 'updated_at', '_ingested_at', '_source']
        all_present = all(field in e for e in events for field in required_fields)
        check(all_present, f"All records have required fields: {', '.join(required_fields)}", results)

        parseable = True
        for e in events:
            try:
                datetime.fromisoformat(e['updated_at'])
                if max_updated_at is None or e['updated_at'] > max_updated_at:
                    max_updated_at = e['updated_at']
            except (ValueError, KeyError):
                parseable = False
        check(parseable, "All updated_at values parse as valid ISO 8601 timestamps", results)

    if watermark_path.exists() and max_updated_at is not None:
        saved_watermark = json.loads(watermark_path.read_text())['updated_at']
        check(saved_watermark == max_updated_at,
              f"Saved watermark ({saved_watermark}) equals max updated_at in raw data ({max_updated_at})", results)
    else:
        check(False, "Watermark file exists and is comparable to max updated_at in raw data", results)

    print(f"\n{sum(results)}/{len(results)} checks passed")
    if not all(results):
        raise SystemExit(1)

if __name__=='__main__': main()