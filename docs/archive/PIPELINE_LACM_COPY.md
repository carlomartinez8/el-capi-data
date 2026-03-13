# La Copa Mundo — Player Data Pipeline

**Last updated:** March 11, 2026
**Pipeline status:** OPERATIONAL
**Maintained by:** Azteca (AI agent) + Carlo (human)

---

## Current Data State

| Table | Records | Source | Last Synced |
|---|---|---|---|
| `pipeline_players` | 35,664 | Transfermarkt + API-Football | 2026-03-11 |
| `clubs` | 491 | Transfermarkt + API-Football | 2026-03-11 |
| `competitions` | 44 | Transfermarkt | 2026-03-11 |
| `transfers` | 100,216 | Transfermarkt | 2026-03-11 |
| `player_valuations` | 525,308 | Transfermarkt | 2026-03-11 |
| `player_bios` | 564 | Wikipedia (87.3% coverage) | 2026-03-11 |
| `active_matches` | 7 | API-Football (live mode) | 2026-03-11 |
| `pipeline_freshness` | 8 | Internal tracking | 2026-03-11 |

### API-Football Squad Coverage

| League | Status | Teams | Players |
|---|---|---|---|
| WC 2026 National Teams | SYNCED | 42 | 1,454 |
| Premier League | SYNCED | 20 | 616 |
| La Liga | SYNCED | 20 | 678 |
| Serie A | SYNCED | 20 | 647 |
| Bundesliga | SYNCED | 18 | 542 |
| Ligue 1 | SYNCED | 18 | 554 |
| MLS | SYNCED | 30 | 842 |
| Liga MX | SYNCED | 18 | 550 |
| Argentine Primera | SYNCED | 30 | 959 |
| Brazilian Série A | SYNCED | 20 | 800 |
| **Total** | **ALL SYNCED** | **236** | **7,642** |

> Pro API plan = 7,500 requests/day. All leagues sync in a single run (~500 credits).

---

## How to Rerun the Pipeline

All commands run from the project root. The `.env.local` file must have `NEXT_PUBLIC_SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and `API_FOOTBALL_KEY`.

### Quick Reference (copy-paste)

```bash
# Full pipeline rerun (historical + bios + squads + live)
pip install -r scripts/pipeline/requirements.txt
python scripts/pipeline/load_transfermarkt.py scripts/pipeline/data/
python scripts/pipeline/enrich_wikipedia.py
python scripts/pipeline/sync_api_football.py all
```

### Step-by-Step Details

#### Step 1 — Install Dependencies (first time only)

```bash
pip install -r scripts/pipeline/requirements.txt
```

Requires: `supabase>=2.0.0`, `requests>=2.28.0`, `pandas>=2.0.0`, `python-dotenv>=1.0.0`, `tqdm>=4.64.0`

#### Step 2 — Download Fresh Transfermarkt CSVs

The CSVs are hosted on Cloudflare R2. Download them into `scripts/pipeline/data/`:

```bash
mkdir -p scripts/pipeline/data && cd scripts/pipeline/data
BASE="https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data"
for f in competitions.csv.gz clubs.csv.gz players.csv.gz transfers.csv.gz player_valuations.csv.gz; do
  curl -sL "$BASE/$f" -o "$f" && gunzip -f "$f"
done
cd ../../..
```

The dataset is updated weekly by the [transfermarkt-datasets](https://github.com/dcaribou/transfermarkt-datasets) project.

#### Step 3 — Load Transfermarkt Data

```bash
python scripts/pipeline/load_transfermarkt.py scripts/pipeline/data/
```

Loads in order: competitions → clubs → players → transfers → player_valuations. Uses batched upserts (500 rows/batch). All scripts use `on_conflict` upsert so they are **safe to rerun** — duplicates are overwritten, not doubled.

**Expected output and timing (~4 min total):**
```
→ Loading competitions...     ✓ 44 competitions
→ Loading clubs...            ✓ 451 clubs
→ Loading players...          ✓ ~34,000 players       (~25s)
→ Loading transfers...        ✓ ~100,000 transfers     (~45s)
→ Loading player valuations...✓ ~525,000 records       (~2.5 min)
```

If valuations time out, reduce `BATCH_SIZE` from 500 to 100 in `load_transfermarkt.py`.

#### Step 4 — Enrich Wikipedia Bios

```bash
python scripts/pipeline/enrich_wikipedia.py
```

Fetches the top ~650 players by market value, looks each up on Wikipedia, and stores bios in `player_bios`. Rate limited at ~1.6 requests/sec.

**Expected:** ~550-600 bios (85%+ hit rate). Takes ~7 minutes. Safe to rerun.

#### Step 5 — Sync API-Football Squads

```bash
python scripts/pipeline/sync_api_football.py squads
```

Syncs current squad rosters from API-Football. Players get `apif_` prefixed IDs (no collision with Transfermarkt). The script runs Premier League + La Liga first (highest priority).

**API budget:** Pro plan = 7,500 requests/day. All leagues sync in one run (~500 credits, ~22 min). Use `all` mode for full sync including World Cup national teams and live matches.

#### Step 6 — Verify (optional)

Run this SQL in the Supabase dashboard, or use the Python verification script:

```sql
SELECT 'pipeline_players' as tbl, COUNT(*) FROM pipeline_players
UNION ALL SELECT 'clubs', COUNT(*) FROM clubs
UNION ALL SELECT 'competitions', COUNT(*) FROM competitions
UNION ALL SELECT 'transfers', COUNT(*) FROM transfers
UNION ALL SELECT 'player_valuations', COUNT(*) FROM player_valuations
UNION ALL SELECT 'player_bios', COUNT(*) FROM player_bios;

SELECT data_type, last_updated, records_updated, status
FROM pipeline_freshness ORDER BY last_updated DESC;

SELECT name, position, current_club_name, market_value_eur
FROM pipeline_players WHERE name ILIKE '%Messi%';
```

---

## Rerun Schedules

| Script | Frequency | Why |
|---|---|---|
| `load_transfermarkt.py` | Weekly (Sunday) | Transfermarkt dataset updates weekly |
| `enrich_wikipedia.py` | Weekly (after Transfermarkt) | New players may enter top-value list |
| `sync_api_football.py squads` | Daily (6am) | Squad changes, transfers, injuries |
| `sync_api_football.py live` | Every 60s during matches | Live scores for Capi |

### Automated Sync (Vercel Cron)

The cron route at `src/app/api/cron/pipeline-sync/route.ts` supports three modes:

```
GET /api/cron/pipeline-sync?mode=squads   → daily squad refresh
GET /api/cron/pipeline-sync?mode=live     → live match polling
GET /api/cron/pipeline-sync?mode=freshness → check data freshness
```

Protected by `CRON_SECRET` bearer token. To enable in `vercel.json`:

```json
{
  "crons": [
    {
      "path": "/api/cron/pipeline-sync?mode=squads",
      "schedule": "0 6 * * *"
    }
  ]
}
```

Live match polling (`mode=live`, every 60s) burns API credits fast — only enable during actual match windows.

---

## Architecture

```
HISTORICAL (weekly)                    LIVE (daily/60s)
┌──────────────┐                     ┌──────────────────┐
│ Transfermarkt │ ─CSV──→ load_      │  API-Football    │
│   (R2 CDN)    │        transfermarkt│  (REST API)      │
└──────────────┘        .py          └────────┬─────────┘
                          │                    │
                          ▼                    ▼
┌──────────────┐    ┌──────────────────────────────────┐
│  Wikipedia   │    │          SUPABASE                  │
│  (REST API)  │───→│  pipeline_players, clubs,          │
└──────────────┘    │  transfers, player_valuations,     │
  enrich_           │  player_bios, active_matches,      │
  wikipedia.py      │  competitions, pipeline_freshness  │
                    └───────────────┬──────────────────┘
                                    │
                                    ▼
                    ┌──────────────────────────────────┐
                    │     Capi (Anthropic Tool Use)      │
                    │                                    │
                    │  5 tools: search_players,           │
                    │  get_player_details, get_squad,     │
                    │  get_live_matches,                  │
                    │  get_transfer_history               │
                    │                                    │
                    │  Agentic loop in chat/route.ts      │
                    │  (max 3 tool rounds per message)    │
                    └──────────────────────────────────┘
```

---

## Database Schema

8 tables defined in `supabase/migrations/20260311_player_data_pipeline.sql`. All have RLS enabled: `SELECT` for anon, full access for `service_role`.

| Table | Primary Key | Notable Columns |
|---|---|---|
| `pipeline_players` | `id TEXT` | name, nationality, position, market_value_eur, current_club_id, photo_url |
| `clubs` | `id TEXT` | name, country, domestic_league, squad_size, total_market_value |
| `competitions` | `id TEXT` | name, country, confederation |
| `transfers` | `id TEXT` | player_id, from/to club, transfer_fee_eur, season |
| `player_valuations` | `BIGSERIAL` + `UNIQUE(player_id, valuation_date)` | market_value_eur, valuation_date, club_id |
| `player_bios` | `player_id TEXT` (FK) | bio_summary, wikipedia_url |
| `active_matches` | `id TEXT` | home/away club+score, minute, status |
| `pipeline_freshness` | `data_type TEXT` | last_updated, records_updated, status |

---

## Capi Integration

Once pipeline data is loaded, Capi's tools query it in real time — no redeploy needed for data changes.

**Code that powers Capi's data access:**

| File | Role |
|---|---|
| `src/lib/capi/tools.ts` | 5 Anthropic tool definitions + Supabase query handlers |
| `src/app/api/capi/chat/route.ts` | Agentic loop (non-streaming `create()` with simulated SSE) |
| `src/lib/capi/system-prompt.ts` | System prompt with `LIVE_DATA_TOOLS_NOTE` layer |
| `src/app/api/cron/pipeline-sync/route.ts` | Vercel cron endpoint for automated syncs |

**Capi's 5 tools:**
1. `search_players` — fuzzy name search with filters (nationality, position, club)
2. `get_player_details` — full profile + bio + valuation history for one player
3. `get_squad` — current roster for a club
4. `get_live_matches` — active match scores (requires live sync to be running)
5. `get_transfer_history` — transfer timeline for a player

---

## Environment Variables

| Variable | Required For | Notes |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | All scripts + Capi | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | All scripts + Capi | Full DB write access |
| `API_FOOTBALL_KEY` | `sync_api_football.py` + cron | API-Football v3 key |
| `CRON_SECRET` | Cron route only | Protects `/api/cron/pipeline-sync` |
| `ANTHROPIC_API_KEY` | Capi chat only | Claude API key |

All values live in `.env.local` (not committed to git).

---

## Files Reference

| File | Purpose |
|---|---|
| `supabase/migrations/20260311_player_data_pipeline.sql` | DDL for 8 pipeline tables |
| `scripts/pipeline/requirements.txt` | Python dependencies |
| `scripts/pipeline/load_transfermarkt.py` | Transfermarkt CSV → Supabase loader |
| `scripts/pipeline/enrich_wikipedia.py` | Wikipedia bio enrichment |
| `scripts/pipeline/sync_api_football.py` | API-Football squad + live sync |
| `scripts/pipeline/data/` | Downloaded CSV files (gitignored) |
| `docs/lacopamundo-player-data-pipeline.md` | Original detailed pipeline design doc |

---

## Troubleshooting

**"Row violates row-level security policy"**
You're using the anon key. Scripts need `SUPABASE_SERVICE_ROLE_KEY`.

**"invalid input syntax for type integer"**
A CSV field has float values (e.g., `184.0`) where the DB expects integer. The loader scripts handle this with `int(float(...))` conversions — if you see this, check for new columns.

**Wikipedia 404s**
Normal. Player names from Transfermarkt don't always match Wikipedia article titles. The script skips misses gracefully. ~85% coverage for top players is expected.

**API-Football "Too many requests"**
Pro plan = 7,500 requests/day. Full sync uses ~500 credits. If you see rate limits, check your daily usage at `https://dashboard.api-football.com`.

**player_valuations taking forever**
It's ~525k rows. Reduce `BATCH_SIZE` to 100 in `load_transfermarkt.py` if timing out.

**Supabase upsert conflicts**
Transfermarkt uses numeric IDs, API-Football uses `apif_` prefixed IDs. Check: `SELECT id FROM pipeline_players LIMIT 10`.

**"ON CONFLICT DO UPDATE cannot affect row a second time"**
Duplicate IDs within a single batch. The transfer loader now deduplicates with a counter suffix. If you see this in other tables, apply the same pattern.

---

## Known Data Gaps

### 1. ~~Squad coverage is partial~~ — RESOLVED
All 9 club leagues + 42 World Cup national teams are now synced (7,642 players across 236 teams). Upgraded to Pro API plan on 2026-03-11.

### 2. Only active players are loaded from Transfermarkt
The loader filters to players with a `current_club_id` (i.e., currently registered to a club). This excludes ~25,000 retired or unattached players from the source dataset. Transfers and valuations are also filtered to only reference loaded player IDs. **Impact:** Capi cannot look up retired legends (e.g., Pelé, Maradona) unless they happen to be in the dataset with a club. **Potential fix:** Load all players (remove the `active` filter in `load_transfermarkt.py`) — would add ~25k rows but also historical depth.

### 3. ~~Wikipedia bios miss ~13% of top players~~ — IMPROVED
Previously 82/646 top players missed due to name mismatches. Now `enrich_wikipedia.py` has a two-step strategy: direct title lookup → Wikipedia search API fallback with "footballer" keyword hint. Also added Phase 3 targeting all APIF squad players (who have NULL market values and were previously skipped). Re-run is in progress to measure the new hit rate.

### 4. Live match data — snapshot captured, no continuous polling yet
The `active_matches` table has 7 rows from the initial full sync (2026-03-11). Continuous live polling (`sync_api_football.py live`) is not yet enabled. **Impact:** Capi's `get_live_matches` tool shows a one-time snapshot, not real-time scores. **Fix:** Enable the Vercel cron to poll every 60s during known fixture windows.

### 5. No appearance/game event data yet
The `appearances` table (defined in the migration) is empty. The Transfermarkt dataset includes `appearances.csv` (~1.5M rows) but the loader doesn't process it yet. **Impact:** Capi cannot answer questions about goals, assists, cards, or minutes played per game. **Potential fix:** Add an `appearances` loader step to `load_transfermarkt.py`.

### 6. Market values reflect Transfermarkt's last update — ASSESSED 2026-03-10
Player market values come from the Transfermarkt dataset which updates weekly. As of 2026-03-10, valuations are **current through 2026-03-09** — data is fresh.

**Coverage:** 32,618 of 34,370 active TM players (94.9%) have market values. 1,752 are NULL (mostly youth/reserve). Top value: Mbappé/Haaland/Yamal at €200M. 1,115 players above €10M.

**Known quirk:** A few high-profile players (e.g., Messi) have stale *club assignments* in TM (still shows PSG) even though valuations update. Capi's dedup logic handles this: picks APIF's current club (Inter Miami) and merges TM's market value + DOB.

**APIF players (6,953) have NULL market values** since API-Football doesn't provide them. The `deduplicatePlayers()` function in `tools.ts` merges TM market values into matching APIF records when available. Players only in APIF (no TM match) will show NULL market value — this is expected.

API-Football squad syncs do NOT include market values — they only bring in current squad membership.

---

## Run Log

| Date | Operator | Script | Result | Notes |
|---|---|---|---|---|
| 2026-03-11 | Azteca | `load_transfermarkt.py` | 44 competitions, 451 clubs, 34,370 players, 100,216 transfers, 525,308 valuations | First full load. Fixed float→int casting and duplicate transfer IDs. |
| 2026-03-11 | Azteca | `enrich_wikipedia.py` | 564 / 646 bios (87.3%) | ~7 min runtime. |
| 2026-03-11 | Azteca | `sync_api_football.py squads` | Premier League (616) + La Liga (678) = 1,294 players | Free tier limited to 2 leagues. |
| 2026-03-11 | Azteca | `sync_api_football.py all` | 42 national teams (1,454), 9 club leagues (6,188), 7 live matches | Pro plan upgrade. Full sync in ~22 min. |

### Next Actions
- [x] ~~Sync remaining leagues~~ — Done (Pro plan, all leagues synced 2026-03-11)
- [ ] Deploy code to Vercel so Capi can use the tools in production
- [ ] Enable Vercel cron for daily squad sync
- [ ] Test Capi tool use end-to-end with live data
- [ ] Schedule weekly Transfermarkt refresh (Sunday)
- [ ] Enable live match polling during fixture windows
