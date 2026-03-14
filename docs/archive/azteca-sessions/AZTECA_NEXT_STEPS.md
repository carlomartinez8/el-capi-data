# Azteca — Two tasks, run in order

## Task 1: Photo Audit (run first)

Before we promote staging to production, we need to know the state of photos. We had mismatching issues in prod.

Run every query in **`AZTECA_PHOTO_AUDIT.md`** and save output to `AZTECA_PHOTO_AUDIT_RESULTS.md`. Do not modify any data — this is read-only.

## Task 2: Promote Staging to Production Warehouse

Once the photo audit is saved, run **`AZTECA_PROMOTE_STAGING.md`** step by step. This loads our 43,447 deduped profiles into the production `players`, `player_aliases`, and `player_career` tables.

**Key rule for Step 2:** The 677 existing players have GPT-generated stories and personality data we want to keep. But their identity fields (name, DOB, nationality, photo) came from the old broken pipeline and need to be overwritten with staging data. The doc explains exactly which fields get overwritten and which stay. Read it carefully.

Save output to `AZTECA_PROMOTE_STAGING_RESULTS.md`.

Both docs are in the el-capi repo root. Run Task 1 first, then Task 2. Paste full output for both — don't truncate.
