# Reflection

**1. Why should source profiling occur before implementation of ingestion?**
Profiling is what tells you what the ingestion code actually needs to handle. We only knew `customer_id` had 3 duplicates, `email`/`city` had missing values, and `event_id` in the API repeats with a newer `updated_at` because we profiled first — none of that was visible from just reading the task list. Writing ingestion code before profiling would mean guessing at these problems, or worse, not knowing they exist until the pipeline silently produces wrong results.

**2. What is the difference between source event time/updated_at and ingestion time?**
`updated_at` is when the event actually happened or was last changed *at the source* — it comes from the API itself. `_ingested_at`, which our pipeline attaches to every record, is when *our* pipeline happened to pull it in. These can differ by any amount — a record with `updated_at` from hours ago could be ingested just now if the pipeline was down, or if it's the very first run. Conflating the two would make it impossible to tell "when did this happen" from "when did we find out about it."

**3. Why is event_id alone insufficient to decide which duplicate API record to keep in this exercise?**
Because the API deliberately repeats the same `event_id` more than once, each time with a newer `updated_at`. If we kept whichever copy we happened to see first (or last, based on request order rather than actual recency), we could end up keeping stale data instead of the true latest version. `event_id` tells you *which* logical record you're looking at, but only `updated_at` tells you *which copy of it* is current.

**4. Why must watermark state advance only after successful persistence?**
Because the watermark is the pipeline's memory of "what I've already safely saved." If it advanced before or during the write, and that write then failed or crashed partway through, the next run would trust the watermark and never re-request that data — permanently losing it, with no error ever raised. We saw this directly in the Task 3.7 failure test: the watermark stayed exactly where it was after the API connection failed, specifically because `save_watermark()` is the very last line to run, after the raw write already succeeded.

**5. What limitation does updated_after > watermark have when multiple source records can share exactly the same timestamp?**
A strict "greater than" comparison against a single timestamp value can't distinguish between multiple records that share that exact same `updated_at`. If the watermark equals a timestamp that several records share, some or all of them could be skipped (already "past" the cutoff) or fetched again on every run (never conclusively "past" it), because the watermark has no way to say "I already have this specific one, but not that other one with the identical timestamp."

**6. How is duplicate prevention related to idempotency?**
Idempotency means running the pipeline multiple times produces the same logical result as running it once. Duplicate prevention is one half of what makes that true for us — without it, a rerun (or an API that legitimately repeats records) would keep adding more copies of the same logical event every time, so the raw output would keep growing even though nothing new actually happened. Our `best_by_id` dedup logic, combined with the content-hash check for files, is what keeps reruns from silently multiplying data.

**7. Why should the raw area preserve source values instead of applying business transformations?**
Because the raw zone is supposed to be a trustworthy, unmodified record of exactly what the source said, at the time it was ingested. If we cleaned or transformed data on the way in, any mistake in that transformation logic — or any future change in requirements — would be baked in permanently, with no way to go back and redo it correctly, since the original values would already be gone. Keeping raw data untouched means cleaning logic can be fixed and rerun later without needing to re-contact the source at all.

**8. How could querying a production OLTP source for profiling or extraction degrade the application?**
Our lab guide explicitly warned against a large cross join or unbounded full-table scan against `support_tickets`, and that's exactly why every one of our Postgres queries used `LIMIT` or a targeted `COUNT`. In a real production system serving live users, an unbounded query against a large table can consume enough CPU/memory/locks that it slows down or blocks the actual application traffic that table exists to serve — a "just profiling" query can accidentally become an outage.

**9. What would you change if the API had a rate limit of 60 requests per minute?**
Our current pagination loop fires requests as fast as it can, one page after another with no delay. With a 60/minute limit, I'd add a deliberate pause between requests (roughly 1 second, to stay safely under 1-per-second) and wrap `fetch_api_page` with retry logic that specifically detects a 429 (rate-limited) response and backs off before retrying, rather than treating it as a hard failure the way our current `except requests.exceptions.RequestException` does.

**10. How would you extend this pipeline from a local raw area to PostgreSQL while preserving rerun safety?**
Instead of writing to `raw/files/` and `raw/api/events.jsonl` as the final destination, I'd load the same deduplicated, already-validated records into Postgres tables — but I'd preserve the exact same safety guarantees we already built: use `event_id` (or the file's SHA-256) as a real database unique constraint so a rerun can't insert duplicate rows, use an upsert (`INSERT ... ON CONFLICT DO UPDATE`) keyed on the same "greatest `updated_at` wins" logic instead of plain `INSERT`, and keep the watermark update as the last step in the transaction, only advancing it after the database write itself has actually committed successfully.