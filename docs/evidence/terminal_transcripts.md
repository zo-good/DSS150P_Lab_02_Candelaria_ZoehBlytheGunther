# Terminal Transcripts — Task 1 & Task 3 Evidence

## PostgreSQL row-count and null check (Task 1.6)

    dss150p=# SELECT COUNT(*) FROM support_tickets;
     count
    -------
       250
    (1 row)

    dss150p=# SELECT COUNT(*) FROM support_tickets WHERE assigned_agent IS NULL;
     count
    -------
         4
    (1 row)

(See postgres_describe_table.png and postgres_sample_rows.png for \d and SELECT * LIMIT 10 output.)

## API pagination (Task 1.5)

    Page 1 has_more: True | total: 122
    Page 1 event_ids: ['E0001', 'E0002', 'E0003', 'E0004', 'E0005', 'E0006', 'E0007', 'E0008', 'E0009', 'E0010']
    Page 2 event_ids: ['E0011', 'E0012', 'E0013', 'E0014', 'E0015', 'E0016', 'E0017', 'E0018', 'E0019', 'E0020']

## First clean ingestion run, from scratch (Task 3.1-3.4, and Task 3.6 clean-rerun proof)

    COPIED customers.csv -> raw/files/customers.csv (sha256=4229a20fde87...)
    COPIED orders.json -> raw/files/orders.json (sha256=5d9aa263ea52...)
    COPIED products.parquet -> raw/files/products.parquet (sha256=cf3b6afd1eea...)
    Fetched 122 new record(s) from API (watermark=None)
    Wrote 120 deduplicated record(s) to raw/api/events.jsonl (2 duplicate(s) removed)
    Watermark updated: None -> 2026-08-21T10:00:00

Validation immediately after:

    [PASS] raw/files/customers.csv exists
    [PASS] raw/files/orders.json exists
    [PASS] raw/files/products.parquet exists
    [PASS] raw/files/manifest.json exists
    [PASS] raw/api/events.jsonl exists
    [PASS] All 120 event_id values are unique
    [PASS] All records have required fields: event_id, customer_id, event_type, amount, updated_at, _ingested_at, _source
    [PASS] All updated_at values parse as valid ISO 8601 timestamps
    [PASS] Saved watermark (2026-08-21T10:00:00) equals max updated_at in raw data (2026-08-21T10:00:00)

    9/9 checks passed

## Idempotent rerun, nothing changed (Task 3.6)

    SKIP customers.csv: content hash already ingested, nothing changed
    SKIP orders.json: content hash already ingested, nothing changed
    SKIP products.parquet: content hash already ingested, nothing changed
    Fetched 0 new record(s) from API (watermark=2026-08-21T10:00:00)
    Wrote 120 deduplicated record(s) to raw/api/events.jsonl (0 duplicate(s) removed)
    No new records fetched; watermark unchanged

## Failure experiment — API server stopped (Task 3.7)

    SKIP customers.csv: content hash already ingested, nothing changed
    SKIP orders.json: content hash already ingested, nothing changed
    SKIP products.parquet: content hash already ingested, nothing changed
    ERROR: API request failed on page 1: HTTPConnectionPool(host='127.0.0.1', port=8000): Max retries exceeded with url: /api/events?page=1&per_page=20&updated_after=2026-08-21T10%3A00%3A00 (Caused by NewConnectionError("HTTPConnection(host='127.0.0.1', port=8000): Failed to establish a new connection: [WinError 10061] No connection could be made because the target machine actively refused it"))

Watermark confirmed unchanged after the failure:

    {
      "updated_at": "2026-08-21T10:00:00"
    }

Corresponding run log row (state/pipeline_run_log.csv):

    4cd44499,2026-09-11T03:00:46.799315+00:00,2026-09-11T03:00:46.807945+00:00,SUCCESS,files,3,0,0,,,
    4cd44499,2026-09-11T03:00:46.808872+00:00,2026-09-11T03:00:48.845395+00:00,FAILED,api,,,,2026-08-21T10:00:00,2026-08-21T10:00:00,"HTTPConnectionPool(host='127.0.0.1', port=8000): Max retries exceeded..."

## Recovery — server restarted (Task 3.7)

    SKIP customers.csv: content hash already ingested, nothing changed
    SKIP orders.json: content hash already ingested, nothing changed
    SKIP products.parquet: content hash already ingested, nothing changed
    Fetched 0 new record(s) from API (watermark=2026-08-21T10:00:00)
    Wrote 120 deduplicated record(s) to raw/api/events.jsonl (0 duplicate(s) removed)
    No new records fetched; watermark unchanged