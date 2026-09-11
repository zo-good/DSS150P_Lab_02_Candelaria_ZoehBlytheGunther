# Ingestion Design (Task 2.4 & 2.5)

## Task 2.4 — Ingestion design by source

| Source | Method | Raw destination | Duplicate key | Incremental state |
|---|---|---|---|---|
| CSV/JSON/Parquet | File copy + manifest | raw/files/ | File SHA-256 | N/A |
| REST API | Paginated GET | raw/api/events.jsonl | event_id | max(updated_at) |
| PostgreSQL | Inspection only in this lab | N/A | ticket_id | Discuss possible timestamp/CDC strategy |

## Task 2.5 — Watermark semantics

The API watermark is the greatest successfully persisted `updated_at` value. On the next run, the pipeline requests only records with `updated_at` greater than the saved watermark. The watermark is operational state, not source data.

**What could go wrong if the watermark were saved before the raw file is successfully written?**
If the pipeline crashes or the write fails after the watermark is advanced but before the raw file is actually saved, the next run would believe those records were already ingested — because the watermark says so — and would never request them again. The data would be permanently lost from the pipeline's perspective, even though it was never actually written anywhere. This is exactly why Task 3.4 requires updating the watermark only *after* the raw write has succeeded, not before or during.

**What could go wrong if the source allows multiple records with exactly the same timestamp?**
If two or more records share the exact same `updated_at` as the current watermark, `updated_after` (a strict "greater than" comparison) would either skip all of them if the watermark already equals that timestamp, or re-fetch all of them repeatedly if the watermark hasn't advanced past their exact timestamp yet. Either way, a timestamp-only watermark can't tell those tied records apart, so it can't guarantee each one is fetched exactly once.

**One limitation of this simplified watermark, and one production-grade mitigation:**
Limitation: a single `max(updated_at)` value has no way to distinguish "already processed" from "not yet processed" among records sharing that exact same boundary timestamp — it's a coarse, second- (or whatever unit) resolution cutoff, not a precise per-record marker.
Mitigation: a production system would pair the timestamp with a unique, strictly increasing identifier (e.g. an auto-incrementing sequence number or a composite watermark of `(updated_at, event_id)`), so ties at the same timestamp can still be ordered and resumed from an exact position rather than a fuzzy one.