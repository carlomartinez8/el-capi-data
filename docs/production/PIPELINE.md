# Pipeline Architecture — Stage by Stage

Detailed documentation of every stage in the El Capi data pipeline. For quick start, see [README.md](README.md).

> **Note (March 14, 2026):** This document describes the classic 7-stage pipeline which processes **632 enriched WC players** through `players_golden.json`. The production warehouse now has **1,176 players** — the additional 538 came from squad build operations (WC 2026 projected squads from API-Football) and staging promotion, which bypass the enrichment/verification stages. See `DATA_LINEAGE.md` for the full picture.

---

## Stage 1: Ingest

**Script**: `run_pipeline.py` → `pipeline/ingest/`

Two data sources are ingested into pandas DataFrames:

### 1a. Transfermarkt (`pipeline/ingest/transfermarkt.py`)

- **Source**: CSV files from the [transfermarkt-datasets](https://github.com/dcaribou/transfermarkt-datasets) project
- **Files**: `players.csv` (required), `clubs.csv`, `transfers.csv`, `player_valuations.csv`
- **Location**: Configured via `TRANSFERMARKT_DATA_DIR` env var (defaults to `../la-copa-mundo/scripts/pipeline/data`)
- **Filter**: Only active players with a `current_club_id` are kept
- **Output**: ~34K active players with fields: `source_id`, `name`, `first_name`, `last_name`, `date_of_birth`, `nationality`, `position`, `current_club_name`, `market_value_eur`, `height_cm`, `foot`, `agent`, `contract_expires`, `photo_url`

### 1b. Static Squads (`pipeline/ingest/static_squads.py`)

- **Source**: `la-copa-mundo/src/data/players.ts` — hand-curated TypeScript file with projected WC 2026 rosters
- **Parser**: Regex-based extraction that handles TypeScript syntax, accented characters, and nested objects
- **Output**: 632 players across 48 teams with fields: `name`, `position`, `club`, `jersey_number`, `captain`, `wc_team_code`

### How the parser works

The TypeScript file exports a `SQUADS` object with team codes as keys and player arrays as values:

```typescript
export const SQUADS = {
  ARG: [
    { name: "Lionel Messi", position: "Forward", club: "Inter Miami CF", number: 10, captain: true },
    ...
  ],
  ...
};
```

The parser:
1. Strips single-line comments
2. Finds the `SQUADS` export
3. Iterates team codes via regex `([A-Z]{3})\s*:\s*\[`
4. For each team block, extracts individual player objects `{ ... }`
5. Parses each field with targeted regexes (`name\s*:\s*"([^"]*)"`, etc.)

---

## Stage 2: Deduplicate

**Script**: `run_pipeline.py` → `pipeline/dedup/`

Merges the two DataFrames into one canonical player list by matching static squad players against Transfermarkt records.

### Matching Engine (`pipeline/dedup/matcher.py`)

**Fuzzy name matching** using `thefuzz` library:

```
normalize_name(name) → lowercase, strip accents (unidecode), remove punctuation
name_similarity(a, b) → max of: token_sort_ratio, token_set_ratio, partial_ratio
```

**Multi-signal scoring** in `compute_match_score()`:

| Signal | Impact | Notes |
|--------|--------|-------|
| Name similarity ≥ 60 | Base score | Below 60 = immediate rejection |
| DOB exact match | +15 | Strongest corroborating signal |
| DOB mismatch | -20 | Strong negative signal |
| Club match (≥80%) | +8 | Moderate positive |
| Nationality match | +5 | Mild positive |
| Nationality mismatch | -10 (normal) / -35 (generic name) | Generic names need extra caution |
| Generic name cap | max 75 | Single-token names without corroboration can't auto-merge |

**Thresholds:**
- **≥ 85**: Auto-merge (TM record absorbs WC squad data)
- **70–84**: Review zone (added as new record, flagged in `dedup_review.csv`)
- **< 70**: No match (added as new record)

### Resolver (`pipeline/dedup/resolver.py`)

**Strategy**: Transfermarkt is the base. For each static squad player:

1. **Find candidates** using a token index (avoids N² comparison)
2. **Score** each candidate via the matcher
3. **Nationality guard**: Even if score ≥ 85, block auto-merge if the TM player's nationality doesn't match the WC team (prevents "Maxwell (Brazil)" merging into Côte d'Ivoire's slot)
4. **Merge or add**: Auto-merge winners get WC fields applied to their TM record. Review/no-match players are added as new rows.

**Merge rules when auto-merging:**
- TM wins for: DOB, height, market value, nationality, agent, contract
- Static squad wins for: `wc_team_code`, `jersey_number`, `captain`, `in_wc_squad`
- Club is backfilled from static squad only if TM has none

### Nationality Plausibility Map

A hardcoded map of ~48 WC team codes to accepted nationality strings. Prevents cross-nationality false merges that plagued earlier runs (e.g., "Ben Williams" (Australia) merging with a Welsh player of the same name).

---

## Stage 3: QA

**Script**: `run_pipeline.py` → `pipeline/qa/checks.py`

Runs validation checks on the canonical DataFrame. Each check produces an issue row with severity (`critical`, `error`, `warning`):

| Check | Severity | What It Catches |
|-------|----------|-----------------|
| `missing_name` | critical | Player with no name |
| `missing_position` | warning | No position assigned |
| `missing_nationality` | warning | No nationality |
| `age_too_young` | error | Age < 15 on WC opening day (June 11, 2026) |
| `age_too_old` | warning | Age > 45 |
| `squad_incomplete` | warning | WC team with < 23 players |
| `squad_too_large` | warning | WC team with > 26 players |
| `no_goalkeeper` | error | WC team missing a GK |
| `duplicate_in_team` | error | Same name appears twice in one team |

---

## Stage 4: Export

**Script**: `run_pipeline.py` → `pipeline/export/local.py`

Writes 4 files:

| Output | Location | Format |
|--------|----------|--------|
| Canonical players | `data/output/players_canonical_latest.json` + timestamped copy | JSON + CSV |
| Dedup review | `data/intermediate/dedup_review.csv` | CSV |
| QA report | `data/intermediate/qa_report.csv` | CSV |
| Run summary | `data/output/run_summary.txt` | Text |

The `latest` files are always overwritten. Timestamped copies preserve history.

---

## Stage 5: Enrichment

**Script**: `run_enrichment.py`

Uses **gpt-4o-mini** to generate rich, structured profiles for each WC player.

### How It Works

1. Loads `players_canonical_latest.json`
2. Filters to `in_wc_squad == True` (632 players)
3. For each player, sends a prompt with known facts (name, team, club, position, DOB, nationality)
4. GPT returns a structured JSON object with ~100 fields across 10 sections
5. Results are checkpointed every batch to `enrichment_checkpoint.json`
6. Final output: `players_enriched.json`

### The System Prompt

The enrichment prompt instructs GPT to:
- Be a world-class football journalist and data analyst
- Return ONLY valid JSON matching the exact schema
- Fill every field with the best available information
- Use bilingual content (EN/ES) for narrative fields
- Be specific (clubs, years, numbers) not vague
- Acknowledge uncertainty in the `meta.data_gaps` field
- Make the data tell a story — not just stats

### Rate Limiting & Checkpointing

- **Batch size**: 700 players per run
- **Delay**: 0.3s between API calls
- **Checkpoint**: Progress saved after each player
- **Resume**: `python run_enrichment.py --resume` continues from last checkpoint
- **Single player**: `python run_enrichment.py --player "Messi"` (accent-insensitive search)
- **Token/cost tracking**: Accumulated in checkpoint file

### Cost

~$3.50 for 632 players using gpt-4o-mini (as of March 2026 pricing).

---

## Stage 6: Canonical Dedup

**Script**: `python -m pipeline.dedup.canonical`

Assigns stable UUID `canonical_id` to each enriched player.

### Key Strategy

| Priority | Key Formula | Coverage |
|----------|-------------|----------|
| Primary | `normalize(surname) + DOB + wc_team_code` | ~95% of players |
| Fallback | `normalize(full_name) + wc_team_code + normalize(club)` | Players missing DOB |

- Zero collisions confirmed on 632 players
- Collisions (if any) are merged as aliases pointing to the same canonical_id
- Outputs: `players_canonical.json` (enriched + canonical_id) and `dedup_report.json`

---

## Stage 7: Verification

**Script**: `run_verification.py` → `pipeline/verify/`

Uses **gpt-4o** (not mini — this is the fact-checker) to verify 12 critical fields per player.

### Three-Tier Priority System

| Tier | Name | Fields | Rationale |
|------|------|--------|-----------|
| **1 — Imperdonable** | Can't get wrong | `current_club`, `current_league`, `nationality_for_wc`, `position_primary`, `in_wc_2026_squad` | Wrong club/league = instant credibility loss |
| **2 — Muy Importante** | Should be right | `date_of_birth`, `estimated_value_eur` | Important context, less visible |
| **3 — Importante** | Nice to have right | `current_jersey_number`, `international_caps`, `international_goals`, `injury_fitness_status`, `contract_expires` | Supporting data |

### How Verification Works

1. Load `players_canonical.json`
2. For each player, extract current values of the 12 fields
3. Send to gpt-4o: "Here's what we have. Verify each field. Return corrections as JSON."
4. gpt-4o returns `{ field: { status: "correct"|"incorrect"|"uncertain", correct_value: ..., confidence: ... } }`
5. Compute diff between current and verified values
6. Optionally auto-apply corrections

### Threading & Rate Limits

- **Threads**: 1-2 (gpt-4o has strict rate limits)
- **Delay**: 1.5-3.0s between calls per thread
- **Retry**: `--retry-failed` re-verifies only players that failed with rate limit errors
- **Cost**: ~$0.003 per player, ~$2.35 total for 632 players

### Apply Updates (`pipeline/verify/apply_updates.py`)

- Reads `verification_diff.json`
- Maps each field to its nested location in the enriched JSON via `FIELD_PATHS`
- Can filter by tier: `--tier 1` applies only imperdonable corrections
- Writes changes back to `players_canonical.json` in-place
- Audit trail saved to `verification_applied.json`

### What Verification Caught (Real Examples)

| Issue | Category | Fix |
|-------|----------|-----|
| Cristiano Ronaldo listed at Manchester United | T1: wrong club | Corrected to Al-Nassr |
| Ederson listed as Midfielder | T1: wrong position | Corrected to Goalkeeper |
| "Ben Williams" merged from wrong TM record | Dedup ghost | Flagged as invalid |
| Craig Gordon (age 43) in WC squad | T1: squad status | Flagged as unlikely |

---

## Stage 8: Reconciliation

**Script**: `python -m pipeline.reconcile.merge` → `python -m pipeline.reconcile.conflicts`

Cross-validates critical fields across all 4 data sources, flags conflicts for human review, and blocks players with unresolved CRITICAL issues from reaching Supabase.

### Sources (priority order)

| Priority | Source | Strengths | Weaknesses |
|----------|--------|-----------|------------|
| 1 (highest) | Transfermarkt CSV | Club, DOB, position, value, contracts — ground truth for factual data | Can be stale (CSV may lag real-world transfers by months) |
| 2 | Static bios (`player-bios.ts`) | Hand-curated caps, goals, achievements, DOB | Slug-based matching can hit wrong player with same name |
| 3 | Static squads (`players.ts`) | Jersey number, captain, position — human-verified rosters | Broad position categories only (FWD, MID, DEF, GK) |
| 4 (lowest) | GPT enrichment | Fills gaps, narrative fields, most current knowledge | Can hallucinate facts, especially transfer dates |

### Step 1: Source Priority Merge (`pipeline/reconcile/merge.py`)

For each of the 632 canonical players, loads values for every critical field from all available sources:

```
current_club, current_league, date_of_birth, position, market_value_eur,
contract_expires, agent, international_caps, international_goals,
career_trajectory, jersey_number, captain, major_trophies, height_cm,
photo_url, nationality
```

Each field gets source attribution: `{value, source, all_sources: {src: val}}`.

**Matching logic:**
- Transfermarkt → matched by `source_id` (TM `player_id`)
- Static bios → matched by player slug (name → lowercase-hyphenated)
- Static squads → matched by player slug
- GPT enrichment → extracted from the canonical record itself

**Output**: `data/output/players_merged.json`

### Step 2: Conflict Detection (`pipeline/reconcile/conflicts.py`)

Compares normalized field values across sources. A conflict is when two sources provide different non-null values for the same field.

**Normalization rules:**
- Club names: strip suffixes (FC, Football Club, S.p.A.), apply alias table (Man United → Manchester United, Hearts → Heart of Midlothian)
- Positions: map broad to specific (FWD ≈ Centre-Forward, GK ≈ Goalkeeper)
- Market value: within 3× tolerance is not a conflict
- International caps/goals: within ±10 is not a conflict
- Height: within ±3cm is not a conflict

**Conflict severity:**

| Level | Fields | Policy |
|-------|--------|--------|
| CRITICAL | `current_club`, `current_league`, `date_of_birth`, `nationality` | Player BLOCKED from publishing until resolved |
| IMPORTANT | `position`, `market_value`, `contract`, `caps/goals`, `jersey_number`, `captain` | Highest-priority source wins provisionally; flagged for review |
| INFORMATIONAL | `height`, `agent`, `career_trajectory`, `major_trophies`, `photo_url` | Auto-resolved to highest-priority; logged for audit |

**Consensus detection:**
When 2+ sources agree and only 1 disagrees, and the agreeing sources include the top-priority source, the conflict is dismissed (not a real disagreement). This filters out ~302 false positives from static_bios slug mismatches.

**Output**: `data/output/reconciliation_report.json` + `data/output/reconciliation_review.csv`

### Step 3: Review & Resolve (`pipeline/reconcile/review.py`)

CLI for reviewing and resolving conflicts:

```bash
# Summary of unresolved conflicts
python -m pipeline.reconcile.review --summary

# Auto-resolve where GPT + squads agree (TM is stale)
python -m pipeline.reconcile.review --auto-resolve-agreement

# Auto-resolve all non-critical (highest priority wins)
python -m pipeline.reconcile.review --auto-resolve-non-critical

# Review a specific player
python -m pipeline.reconcile.review --player "Luis Díaz"

# Accept a specific source for a player
python -m pipeline.reconcile.review --player "Lionel Messi" --accept-gpt

# Apply all resolutions to canonical JSON
python -m pipeline.reconcile.review --apply
```

**Resolution flow:**
1. `--auto-resolve-agreement` — resolves club/league conflicts where GPT + squads agree (stale TM)
2. `--auto-resolve-non-critical` — resolves all IMPORTANT/INFORMATIONAL using highest-priority source
3. Human reviews remaining CRITICAL conflicts
4. `--apply` writes resolved values back to `players_canonical.json`

### Career Builder (`pipeline/reconcile/career_builder.py`)

Builds authoritative `career_trajectory` from Transfermarkt `transfers.csv` instead of trusting GPT-generated timelines. Provides ground-truth transfer history with dates, clubs, and fees.

---

## Stage 9: Push to Supabase

**Script**: `push_to_supabase.py`

Pushes enriched player data directly to Supabase via the REST API, bypassing the SQL Editor's size limits. Players blocked by the reconciliation layer are automatically skipped.

### Tables Populated

| Table | Row Count | Conflict Resolution |
|-------|-----------|-------------------|
| `players` | 1,176 (632 from pipeline + 538 from squad build/APIF) | Upsert on `id` |
| `player_career` | 1,176 | Upsert on `player_id` |
| `player_tournament` | 1,176 | Upsert on `player_id` |
| `player_aliases` | ~1,221+ | Insert, skip duplicates |

### Data Transformations

- **`contract_expires`**: Converts "June 2025" → `2025-06-28` (date column)
- **`estimated_value_eur`**: Parses "€30M" → `30000000` (bigint)
- **`social_media`**: Dict → JSON string (stored as text)
- **`career_trajectory`**: Array of objects → JSON string (stored as jsonb)
- **Lists**: Python lists → PostgreSQL arrays

### Alternative: SQL Files

If the REST API approach doesn't work, generate SQL INSERT files:

```bash
python -m pipeline.sync.to_supabase
# Produces: data/output/supabase_seed/
#   players.sql (21K lines)
#   player_aliases.sql (2.3K lines)
#   player_career.sql (14.5K lines)
#   player_tournament.sql (14.5K lines)
```

These are too large for the Supabase SQL Editor web UI. Use `psql` or split them manually.

---

## Re-Running the Pipeline

### Recommended: Use `refresh.py`

The safest way to refresh data. Handles backups, cost estimation, and rollback.

```bash
# Preview what would happen (no changes, no cost)
python refresh.py --dry-run

# Full safe refresh: backup → pipeline → enrich → reconcile → verify → push
python refresh.py

# Cheaper refresh: skip enrichment (only re-verify + push)
python refresh.py --skip-enrich

# Something went wrong? Roll back to the automatic backup
python refresh.py --rollback
```

### Manual refresh (advanced)

Use individual scripts when you need fine-grained control:

```bash
# Full refresh
python run_pipeline.py                          # re-ingest + dedup + QA + export
python run_enrichment.py                        # re-enrich all 632 players (~$3.50)
python -m pipeline.dedup.canonical              # assign canonical IDs
python -m pipeline.reconcile.merge              # cross-validate sources
python -m pipeline.reconcile.conflicts          # detect conflicts
python -m pipeline.reconcile.review --auto-resolve-agreement
python -m pipeline.reconcile.review --auto-resolve-non-critical
python -m pipeline.reconcile.review --summary   # check what's still blocked
python -m pipeline.reconcile.review --apply     # apply resolutions to canonical
python run_verification.py --apply              # verify critical fields
python push_to_supabase.py                      # push to Supabase (skips blocked)
```

### Update after roster changes
```bash
# 1. Update players.ts in la-copa-mundo with new rosters
# 2. Re-run everything safely
python refresh.py
# Or manually:
python run_pipeline.py
python run_enrichment.py --resume   # only enriches new/missing players
python -m pipeline.dedup.canonical
python run_verification.py --apply
python push_to_supabase.py
```

### Verify a specific player
```bash
python run_verification.py --player "Kylian Mbappé"
```

### Backups and rollback
```bash
# List available backups
python refresh.py --list-backups

# Roll back to the most recent backup
python refresh.py --rollback

# Roll back to a specific backup
python refresh.py --rollback --backup 20260312_143000_pre_refresh
```

Backups are stored in `data/backups/` with timestamps. Each backup contains:
- `players_canonical.json` (the source of truth)
- `players_enriched.json`
- Verification results and diffs
- A `manifest.json` with metadata

---

## Error Handling

| Error | Cause | Fix |
|-------|-------|-----|
| `JSONDecodeError` in static squads | Malformed players.ts | Check for unclosed brackets or unescaped quotes |
| `AttributeError: float has no attribute encode` | NaN values in dedup | `_safe_str()` handles this — ensure it's used |
| `RateLimitError` during verification | gpt-4o rate limits | Reduce threads, increase delay, use `--retry-failed` |
| `invalid input syntax for type date` | "June 2025" in date column | `parse_contract_date()` converts to ISO format |
| `foreign key violation` on aliases | Players table not populated | Always push `players` table first |
| `Query is too large` in Supabase SQL Editor | SQL files > 10K lines | Use `push_to_supabase.py` instead |

---

## Dependencies

```
pandas>=2.0.0          # DataFrame operations
python-dotenv>=1.0.0   # .env file loading
tqdm>=4.64.0           # Progress bars
thefuzz[speedup]>=0.22.0  # Fuzzy string matching (uses python-Levenshtein)
unidecode>=1.3.0       # Accent stripping for name normalization
openai>=1.0.0          # ChatGPT API for enrichment and verification
supabase>=2.0.0        # Supabase REST API client
requests>=2.28.0       # HTTP requests
```
