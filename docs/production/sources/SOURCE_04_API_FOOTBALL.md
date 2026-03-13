# Source 04: API-Football (v3)

**Priority Rank**: 4
**Type**: REST API (v3.football.api-sports.io)
**Refresh**: Automated (daily squads, 60s live scores during matches, weekly transfers)
**Coverage**: 12 priority leagues + World Cup

## API Details

- **Endpoint**: `https://v3.football.api-sports.io`
- **Auth**: API key in `x-rapidapi-key` header
- **Plan**: Pro (7,500 credits/day)
- **Rate limit**: 300 requests/minute

## 5 Sync Modes

| Mode | Endpoint | Frequency | Credits/call |
|------|----------|-----------|-------------|
| `squads` | `/players/squads` | Daily | ~1 per team |
| `live` | `/fixtures` | Every 60s during matches | ~1 |
| `wc` | `/fixtures` + `/predictions` | Match days | ~2 |
| `transfers` | `/transfers` | Weekly backfill | ~1 per player |
| `names` | `/players` | On-demand resolution | ~1 per player |

## Fields Provided

| Field | Quality | Notes |
|-------|---------|-------|
| Full name (first + last) | High | Official API registration |
| Current club | High | Real-time from squad endpoint |
| Photo URL | High | Player headshot |
| Age | High | Calculated from DOB |
| Nationality | High | Primary nationality |
| Position | High | Current squad position |
| Live scores | Real-time | During active matches |
| Transfer history | High | Comprehensive for covered leagues |

## Pipeline Integration

- Sync script: `scripts/pipeline/sync_api_football.py` (currently in la-copa-mundo, to be moved)
- Target tables: `raw.raw_apif_players`, `raw.raw_apif_transfers`, `clubs`, `active_matches`, `pipeline_freshness`
- Priority: Rank 4 — wins over GPT for club assignments, full names

## Known Issues

- Not yet integrated into merge layer (clubs still come 100% from GPT)
- Credit budget requires careful management during live matches
- Some smaller leagues have incomplete squad data

## TODO

- [ ] Move sync script to el-capi-data repo
- [ ] Integrate into Prefect as scheduled flows
- [ ] Add to merge layer (critical — fixes stale club problem)
- [ ] Document credit budget allocation across modes
- [ ] Add data quality metrics
