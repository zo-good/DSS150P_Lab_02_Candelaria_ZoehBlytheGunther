# Source Profiling Report

## 1. Source Inventory

| Source | Type | Rows/Records | Key | Update Pattern | Quality Findings |
|---|---|---:|---|---|---|
| customers.csv | CSV file | 250 | customer_id | Unknown (static file; needs source owner confirmation) | 3 duplicate customer_id values, 2 exact duplicate rows, 3 missing email, 2 missing city |
| orders.json | JSON file | 250 | order_id | Unknown (static file; needs source owner confirmation) | No missing values across 9 keys; nested shipping object; order_timestamp is plain text, not a native timestamp |
| products.parquet | Parquet file | 200 | product_id | Unknown (static file; needs source owner confirmation) | No missing values across 7 columns; type-preserving (e.g. stock_quantity stored as int32, vs int64 if re-inferred from CSV/JSON) |
| REST API /api/events | Paginated REST API | 122 total (per API's own total field) | event_id (NOT unique alone) | Live; supports updated_after for incremental polling | 2 event_id values deliberately repeated with a newer updated_at each time |
| support_tickets (PostgreSQL) | Database table | 250 | ticket_id | Unknown; inspected only, not ingested in this lab | 4 tickets with no assigned_agent (NULL); resolved_at NULL for any still-open ticket |

## 2. Schema Findings

All five sources have a real, enforced or effectively-fixed schema, but they arrive at "type" very differently:

- **customers.csv / orders.json**: every field is plain text at the source. Pandas/Python guesses a type on read (e.g. `signup_date` and `order_timestamp` both come back as plain strings, not real date/timestamp types) — the logical type has to be declared separately (see `config/schema_customers.yml`, `config/schema_events.yml`), it isn't something the file itself carries.
- **products.parquet**: unlike the two above, Parquet stores its schema *inside the file* — types like `int32` are preserved exactly as written, with no guessing needed on read. Confirmed by direct comparison against CSV/JSON twins of the same data (`products_optional_compare.csv/.json`), where the same integer column came back as the wider `int64` once written as plain text and re-inferred.
- **REST API events**: JSON types (str, int, float, nested dict for `metadata`) are consistent across all 122 records, but `updated_at` is transmitted as ISO 8601 text, not a native timestamp — same "logical vs. physical" gap as the two flat files.
- **support_tickets (Postgres)**: the only source with a database-enforced schema from the start (`\d support_tickets` reported real, certain types and nullability — no guessing required, since Postgres has always known the schema with certainty).

## 3. Data Quality Findings

- customers.csv has real, deliberate defects: 3 duplicate `customer_id` values, 2 fully duplicate rows, and missing `email`/`city` values.
- orders.json and products.parquet were both clean — zero missing values found across all checked fields — which is itself a documented finding, not an absence of one.
- The REST API deliberately repeats 2 `event_id` values with a newer `updated_at` each time, meaning `event_id` alone cannot be trusted as a unique key without deduplication logic.
- support_tickets has 4 unassigned tickets and, by design, a NULL `resolved_at` for any ticket that isn't yet Resolved/Closed — expected, not a defect.
- At small scale (200 rows), `products.parquet` (14,652 bytes) was actually *larger* than its CSV twin (11,560 bytes) — Parquet's columnar/compression overhead only pays off at bigger row counts than this lab's data uses.

## 4. Recommended Acquisition Method

| Source | Method |
|---|---|
| CSV / JSON / Parquet | File copy into a raw zone, with SHA-256 content hashing and a manifest, so unchanged files are never re-copied on rerun |
| REST API | Paginated GET requests looping until `has_more` is false, using `updated_after` + a persisted watermark for incremental fetching after the first run |
| PostgreSQL | Bounded, read-only inspection queries only (no full-table scans) — this lab does not ingest this source |

## 5. Risks and Assumptions

- **Owner and update cadence are unknown for every static file source** (`customers.csv`, `orders.json`, `products.parquet`) — profiling a snapshot can't reveal who produces it or how often it refreshes; this would need to be confirmed with a real source owner before production use.
- **`event_id` cannot be assumed unique** in any downstream system that consumes this API — any consumer must apply the same "keep greatest `updated_at`" logic this pipeline uses, or risk double-counting events.
- **The watermark is timestamp-only**, so if the source ever produced multiple records sharing the *exact* same `updated_at` as the current watermark boundary, this simple design could not guarantee each is processed exactly once (see `docs/ingestion_design.md` for the full watermark-limitation discussion).
- **This report reflects the state of the data at profiling time** — since `customers.csv`/`orders.json`/`products.parquet` are static snapshots with no version or change-log, any future modification to these source files would require re-profiling, not just re-running the pipeline.