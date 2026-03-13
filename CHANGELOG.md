# Changelog — El Capi Data Pipeline

All notable changes to the data pipeline. Format: date, author, what changed.

---

## 2026-03-13 — Documentation Reorganization (Pelé)
- Restructured `docs/` into production / active / brainstorm / archive / log
- Created per-source documentation stubs in `docs/production/sources/`
- Migrated data docs from la-copa-mundo to this repo (proper ownership)
- Architecture blueprint moved to `docs/active/` (target state, not current)

## 2026-03-12 — API-Football in Blueprint (Pelé)
- Added API-Football as Source 5 in architecture blueprint
- Updated all 12 references (tables, coverage map, flow diagram, phases)

## 2026-03-11 — P0 Fixes (Pelé)
- Nationality normalization
- Seed regeneration

## 2026-03-09 — Architecture Blueprint (Pelé)
- Designed 7-stage pipeline architecture
- Modern stack: Prefect 3.x, dbt-core, Soda Core
- Medallion pattern: raw → staging → public

## 2026-03-08 — Pipeline v2 Complete (Pelé)
- All 7 stages operational: INGEST → DEDUP → MERGE → ENRICH → COMBINE → VERIFY → DEPLOY
- End-to-end test passed
- Enrichment refactored to narrative-only mode
