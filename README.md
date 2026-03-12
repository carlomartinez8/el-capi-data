# El Capi Data Pipeline

The data backbone for [La Copa Mundo](https://lacopamundo.com) — ingests, deduplicates, enriches, verifies, and delivers clean World Cup 2026 player data to power **Capi** (El Capitán del Conocimiento), the AI soccer personality.

## What This Does

Takes raw player data from multiple sources (Transfermarkt CSVs + hand-curated World Cup rosters) and produces a clean, enriched, verified dataset of 632 World Cup 2026 players — then pushes it to Supabase where Capi's Analytics Mode can query it.

```
Raw CSVs + players.ts + player-bios.ts
  → Ingest → Dedup → QA → Export (34K+ players, flat)
  → Enrich via gpt-4o-mini (632 WC players, rich nested schema)
  → Reconcile (cross-validate 4 sources, flag conflicts, block bad data)
  → Verify via gpt-4o (12 critical fields, 3 tiers)
  → Push to Supabase (4 warehouse tables, blocked players skipped)
```

## Quick Start

```bash
# 1. Set up
cd el-capi-data
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in your keys

# 2. Run the base pipeline (ingest → dedup → QA → export)
python run_pipeline.py

# 3. Enrich WC players via ChatGPT (~$3.50 for 632 players)
python run_enrichment.py

# 4. Assign canonical IDs
python -m pipeline.dedup.canonical

# 5. Reconcile across sources (flags conflicts)
python -m pipeline.reconcile.merge
python -m pipeline.reconcile.conflicts
python -m pipeline.reconcile.review --auto-resolve-agreement
python -m pipeline.reconcile.review --auto-resolve-non-critical
python -m pipeline.reconcile.review --apply

# 6. Verify critical fields via gpt-4o (~$2.35 for 632 players)
python run_verification.py --apply

# 7. Push to Supabase (blocked players skipped)
python push_to_supabase.py
```

## Project Structure

```
el-capi-data/
├── refresh.py                   # Safe refresh: backup → pipeline → enrich → verify → push
├── run_pipeline.py              # Orchestrates: ingest → dedup → QA → export
├── run_enrichment.py            # ChatGPT enrichment (gpt-4o-mini)
├── run_verification.py          # Critical field verification (gpt-4o)
├── push_to_supabase.py          # Direct REST API push to Supabase
│
├── pipeline/
│   ├── config.py                # Shared config, env vars, paths, league lookup
│   ├── ingest/
│   │   ├── transfermarkt.py     # Loads Transfermarkt CSVs (34K+ players)
│   │   ├── static_squads.py     # Parses players.ts (WC 2026 rosters)
│   │   └── static_bios.py       # Parses player-bios.ts (caps, goals, achievements)
│   ├── dedup/
│   │   ├── matcher.py           # Fuzzy matching engine (thefuzz)
│   │   ├── resolver.py          # Merge logic + nationality guards
│   │   └── canonical.py         # UUID assignment for enriched players
│   ├── reconcile/
│   │   ├── merge.py             # Load 4 sources, build per-player field map
│   │   ├── conflicts.py         # Detect cross-source conflicts, generate report
│   │   ├── review.py            # CLI for reviewing/resolving conflicts
│   │   └── career_builder.py    # Build career_trajectory from transfers.csv
│   ├── qa/
│   │   └── checks.py            # Validation: ages, squads, positions, names
│   ├── export/
│   │   └── local.py             # JSON/CSV export with timestamped versions
│   ├── verify/
│   │   ├── critical_fields.py   # gpt-4o verification engine (3-tier)
│   │   └── apply_updates.py     # Apply verified corrections
│   └── sync/
│       └── to_supabase.py       # Generate SQL INSERT files (alternative to push)
│
├── data/
│   ├── raw/                     # (gitignored) raw source data
│   ├── intermediate/            # (gitignored) dedup reviews, QA reports
│   └── output/                  # (gitignored) canonical JSON, enriched JSON, seeds
│
├── requirements.txt
├── .env.example
└── .gitignore
```

## Pipeline Stages

See [PIPELINE.md](PIPELINE.md) for detailed stage-by-stage documentation.

| # | Stage | Script | Model | Cost | Output |
|---|-------|--------|-------|------|--------|
| 1 | Ingest | `run_pipeline.py` | — | free | 34K+ players in DataFrames |
| 2 | Deduplicate | `run_pipeline.py` | — | free | Merged canonical list |
| 3 | QA | `run_pipeline.py` | — | free | `qa_report.csv` |
| 4 | Export | `run_pipeline.py` | — | free | `players_canonical_latest.json/csv` |
| 5 | Enrich | `run_enrichment.py` | gpt-4o-mini | ~$3.50 | `players_enriched.json` |
| 6 | Canonical ID | `pipeline/dedup/canonical.py` | — | free | `players_canonical.json` |
| 7 | **Reconcile** | `pipeline/reconcile/` | — | free | `reconciliation_report.json` + CSV |
| 8 | Verify | `run_verification.py` | gpt-4o | ~$2.35 | corrections applied in-place |
| 9 | Push | `push_to_supabase.py` | — | free | 4 Supabase tables populated |

**Total cost per full run: ~$5.85** for 632 World Cup players.

## Data Sources

| Source | Type | Records | What It Provides |
|--------|------|---------|------------------|
| [Transfermarkt](https://github.com/dcaribou/transfermarkt-datasets) | CSVs | 34K+ active players | Name, DOB, nationality, club, market value, height, position, agent, contract, transfers |
| `la-copa-mundo/src/data/players.ts` | TypeScript | 632 players / 48 teams | WC 2026 rosters: name, position, club, jersey number, captain status |
| `la-copa-mundo/src/data/player-bios.ts` | TypeScript | 636 bios | Caps, goals, achievements, DOB, height, previous clubs (hand-curated + generated) |
| GPT enrichment (`gpt-4o-mini`) | API | 632 players | Rich narrative fields, fills gaps not covered by other sources |

## Enrichment Schema

Each enriched player is a nested JSON object with these sections. See [DATA-SCHEMA.md](DATA-SCHEMA.md) for the full field reference.

| Section | Fields | Example |
|---------|--------|---------|
| **identity** | full_legal_name, known_as, DOB, birth_city, nationality, height, preferred_foot, languages, nicknames | `"Lionel Andrés Messi Cuccittini"` |
| **career** | current_club, league, position, caps, goals, trophies, records, career_trajectory | `"Inter Miami CF"` |
| **playing_style** | style_summary (en/es), signature_moves, strengths, weaknesses, comparable_to | `"Comparable to Diego Maradona"` |
| **story** | origin_story (en/es), breakthrough_moment, career_defining_quote, controversy | Bilingual narratives |
| **personality** | celebration, superstitions, interests, charity, tattoos, fun_facts, social_media | `"The GOAT celebration"` |
| **world_cup_2026** | previous WC appearances, qualifying contribution, tournament_role (en/es), narrative_arc (en/es) | `"His last dance"` |
| **big_game_dna** | WC goals, UCL goals, derby performances, clutch_moments | `13 World Cup goals` |
| **market** | estimated_value_eur, endorsement_brands, agent | `"€50M"` |
| **injury_history** | notable_injuries, injury_prone | `true/false` |
| **meta** | data_confidence, data_gaps | `"high"` |

## Verification System

The verification layer uses **gpt-4o** (not mini) to fact-check 12 critical fields, organized into 3 priority tiers:

| Tier | Name | Fields | Policy |
|------|------|--------|--------|
| **T1** | Imperdonable | current_club, current_league, nationality_for_wc, position_primary, in_wc_2026_squad | Wrong = user trust destroyed. Auto-apply. |
| **T2** | Muy Importante | date_of_birth, estimated_value_eur | Important but less visible. Review recommended. |
| **T3** | Importante | jersey_number, international_caps, international_goals, injury_fitness_status, contract_expires | Nice to have accurate. Lower priority. |

```bash
# Test on 5 players first (~$0.015)
python run_verification.py --batch 5

# Full verification (~$2.35, ~15 min)
python run_verification.py --apply

# Retry any rate-limit failures
python run_verification.py --retry-failed --apply

# Single player check
python run_verification.py --player "Lionel Messi"
```

## Source Reconciliation

The reconciliation layer cross-validates critical fields across all 4 data sources before publishing. Players with unresolved CRITICAL conflicts are blocked from reaching Supabase.

### How It Works

1. **Merge** — loads Transfermarkt, static bios, static squads, and GPT enrichment for each player. Highest-priority source with a non-null value wins.
2. **Detect** — compares sources for 16 critical fields. Normalizes club names, positions, and values before comparing to avoid false positives.
3. **Auto-resolve** — safely resolves conflicts where sources agree (GPT + squads consensus over stale TM) or where the field is non-critical.
4. **Review** — remaining CRITICAL conflicts are flagged for human review.
5. **Publish** — only clean players (no unresolved CRITICAL conflicts) are pushed to Supabase.

### Conflict Severity

| Level | Fields | Policy |
|-------|--------|--------|
| **CRITICAL** | current_club, current_league, date_of_birth, nationality | Blocks player from publishing |
| **IMPORTANT** | position, market_value, contract, caps/goals, jersey, captain | Highest-priority wins; flagged |
| **INFORMATIONAL** | height, agent, trophies, career_trajectory | Auto-resolved; logged |

### CLI

```bash
python -m pipeline.reconcile.merge                           # merge all sources
python -m pipeline.reconcile.conflicts                       # detect conflicts
python -m pipeline.reconcile.conflicts --summary             # view last report
python -m pipeline.reconcile.review --summary                # summary of unresolved
python -m pipeline.reconcile.review --auto-resolve-agreement # resolve GPT+squads consensus
python -m pipeline.reconcile.review --auto-resolve-non-critical
python -m pipeline.reconcile.review --player "Luis Díaz"     # inspect one player
python -m pipeline.reconcile.review --player "Messi" --accept-gpt
python -m pipeline.reconcile.review --apply                  # write resolutions to canonical
```

### Output Files

| File | Description |
|------|-------------|
| `reconciliation_report.json` | Full report: conflicts, blocked players, missing fields |
| `reconciliation_review.csv` | Flat CSV for quick human scanning |
| `reconciliation_resolutions.json` | Track of all resolved conflicts |
| `players_merged.json` | Per-player field map with source attribution |

---

## Supabase Warehouse

The enriched data lands in 4 normalized tables in Supabase:

| Table | Purpose | Rows |
|-------|---------|------|
| `players` | Identity, story, personality (static) | 632 |
| `player_career` | Club, position, style, market value (semi-static) | 632 |
| `player_tournament` | WC 2026 data, caps, goals, narrative (dynamic) | 632 |
| `player_aliases` | Cross-source IDs, nicknames, alternate names | ~1,148 |

These tables power Capi's **Analytics Mode** — premium users ask natural-language questions and Capi generates SQL that queries this warehouse via a read-only RPC function.

```bash
# Push directly via REST API (recommended)
python push_to_supabase.py

# Or generate SQL files to run manually
python -m pipeline.sync.to_supabase
# Then run files in: data/output/supabase_seed/
```

## Environment Variables

```bash
# Required
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
OPENAI_API_KEY=your-openai-api-key

# Optional (defaults work if la-copa-mundo is sibling directory)
TRANSFERMARKT_DATA_DIR=../la-copa-mundo/scripts/pipeline/data
STATIC_SQUADS_PATH=../la-copa-mundo/src/data/players.ts
API_FOOTBALL_KEY=your-api-football-key
```

## Safe Refresh

The `refresh.py` script is the **recommended way to update data**. It handles backups, cost estimation, and rollback automatically.

```bash
# Preview what would happen (no changes, no cost)
python refresh.py --dry-run

# Full safe refresh: backup → pipeline → enrich → reconcile → verify → push
python refresh.py

# Just re-run the pipeline (no enrichment/verification/push)
python refresh.py --pipeline-only

# Just run reconciliation on existing canonical data
python refresh.py --reconcile-only

# Re-verify and push (skip pipeline and enrichment)
python refresh.py --verify-only

# Just push existing data to Supabase
python refresh.py --push-only

# Skip expensive steps
python refresh.py --skip-enrich      # skip enrichment (~$3.50 saved)
python refresh.py --skip-verify      # skip verification (~$2.35 saved)
python refresh.py --skip-reconcile   # skip reconciliation

# Rollback to last backup if something went wrong
python refresh.py --rollback

# List available backups
python refresh.py --list-backups

# Rollback to a specific backup
python refresh.py --rollback --backup 20260312_143000_pre_refresh
```

### What refresh.py does

1. **Backs up** all critical files (`players_canonical.json`, `players_enriched.json`, verification results) to `data/backups/` with a timestamp
2. **Runs the pipeline** (ingest → dedup → QA → export)
3. **Enriches** new/missing players via ChatGPT (`--resume` mode, only pays for new players)
4. **Reconciles** across sources — auto-resolves safe conflicts, flags CRITICAL ones for review
5. **Verifies** critical fields via gpt-4o and auto-applies T1 (imperdonable) corrections
6. **Pushes** to Supabase via REST API (upserts, skips blocked players)

### Cost per refresh

| Step | Cost | When It Charges |
|------|------|----------------|
| Pipeline (ingest/dedup/QA/export) | Free | Always |
| Enrichment (gpt-4o-mini) | ~$3.50 | Only for new/un-enriched players |
| Verification (gpt-4o) | ~$2.35 | All 632 players |
| Push to Supabase | Free | Always |
| **Total (first run)** | **~$5.85** | |
| **Total (refresh, no new players)** | **~$2.35** | Only verification |

## CLI Reference

| Command | What It Does |
|---------|--------------|
| `python refresh.py --dry-run` | Preview refresh plan with cost estimates |
| `python refresh.py` | Full safe refresh with backups |
| `python refresh.py --rollback` | Restore from last backup |
| `python run_pipeline.py` | Full pipeline: ingest → dedup → QA → export |
| `python run_pipeline.py --ingest` | Ingest only (save intermediate CSVs) |
| `python run_pipeline.py --dedup` | Dedup + QA on previously ingested data |
| `python run_enrichment.py` | Enrich all WC players via ChatGPT |
| `python run_enrichment.py --player "Messi"` | Enrich a single player |
| `python run_enrichment.py --resume` | Resume from last checkpoint |
| `python -m pipeline.dedup.canonical` | Assign canonical UUIDs to enriched players |
| `python run_verification.py` | Verify all players (dry run) |
| `python run_verification.py --apply` | Verify and auto-apply all corrections |
| `python run_verification.py --apply --tier 1` | Apply only T1 (imperdonable) corrections |
| `python run_verification.py --retry-failed --apply` | Re-verify rate-limited failures |
| `python run_verification.py --player "Ronaldo"` | Verify a single player |
| `python run_verification.py --batch 10` | Test on 10 players |
| `python -m pipeline.reconcile.merge` | Merge all 4 sources with priority |
| `python -m pipeline.reconcile.conflicts` | Detect cross-source conflicts |
| `python -m pipeline.reconcile.conflicts --summary` | View last conflict report |
| `python -m pipeline.reconcile.review --summary` | Summary of unresolved conflicts |
| `python -m pipeline.reconcile.review --auto-resolve-agreement` | Auto-resolve where GPT+squads agree |
| `python -m pipeline.reconcile.review --auto-resolve-non-critical` | Auto-resolve non-critical conflicts |
| `python -m pipeline.reconcile.review --player "Messi"` | Inspect a player's conflicts |
| `python -m pipeline.reconcile.review --player "Messi" --accept-gpt` | Accept GPT value for player |
| `python -m pipeline.reconcile.review --apply` | Apply resolutions to canonical JSON |
| `python push_to_supabase.py` | Push canonical data to Supabase (skips blocked) |
| `python push_to_supabase.py --no-skip-blocked` | Push ALL players (ignore blocks) |
| `python -m pipeline.sync.to_supabase` | Generate SQL INSERT files |
| `python -m pipeline.verify.apply_updates` | Preview pending corrections |
| `python -m pipeline.verify.apply_updates --apply` | Apply pending corrections |

## Key Output Files

All in `data/output/` (gitignored):

| File | Description |
|------|-------------|
| `players_canonical_latest.json` | Full canonical list (34K+ players, flat schema) |
| `players_canonical_latest.csv` | Same, CSV format |
| `players_enriched.json` | Enriched WC players (632, nested schema) |
| `players_canonical.json` | **THE source of truth** — enriched + verified + canonical IDs |
| `enrichment_checkpoint.json` | Enrichment progress (resume from here) |
| `verification_results.json` | Verification results per player |
| `verification_diff.json` | Detected changes |
| `verification_applied.json` | Audit trail of applied changes |
| `players_merged.json` | Per-player field map with source attribution |
| `reconciliation_report.json` | Cross-source conflict report |
| `reconciliation_review.csv` | Flat CSV for scanning conflicts |
| `reconciliation_resolutions.json` | Resolved conflicts audit trail |
| `supabase_seed/*.sql` | Generated SQL INSERT files |
| `run_summary.txt` | Last pipeline run summary |

## Admin Panel (Web UI)

Conflicts can also be reviewed and resolved through the La Copa Mundo admin panel at `/admin/reconciliation`. This is the preferred interface for human curators.

**Features:**
- View all blocked/flagged players with severity badges
- Side-by-side comparison of all 4 sources per conflict
- One-click accept from any source, or manual override
- Batch actions (auto-resolve consensus, non-critical, accept GPT for all leagues/clubs)
- Apply resolutions to canonical JSON
- Player browser with search and team filters
- Pipeline health dashboard with command reference

**Access:** Requires `is_admin` or `is_curator` role in Supabase `profiles` table.

**See:** `la-copa-mundo/docs/ADMIN-PANEL.md` for full architecture.

## For Agents

If you're an AI agent working on this codebase:

1. **Read `AGENTS.md`** in `la-copa-mundo/` first — it has the full project state and ownership map
2. **`players_canonical.json`** is the source of truth for enriched player data — never overwrite without verification
3. **The enrichment checkpoint** (`enrichment_checkpoint.json`) tracks which players have been enriched — use `--resume` to continue
4. **Rate limits matter** — gpt-4o has strict rate limits. Use 1-2 threads with 1.5-3s delay for verification
5. **Two table systems exist** in Supabase — old (`pipeline_players`) and new warehouse (`players` + `player_career` + `player_tournament`). Analytics Mode uses the new warehouse.
6. **Supabase DNS** doesn't resolve from sandboxed VMs — use `push_to_supabase.py` from a machine with network access

---

*Part of the [El Capi](https://github.com/carlomartinez8) monorepo — `la-copa-mundo` (Next.js app) + `el-capi-data` (data pipeline).*
