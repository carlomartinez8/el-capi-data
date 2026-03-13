# Source 01: Transfermarkt CSV

**Priority Rank**: 1 (highest — ground truth for factual fields)
**Type**: Static CSV export
**Refresh**: Manual (CSV re-export from Transfermarkt)
**Coverage**: ~650 players across 12 WC 2026 qualifying leagues

## Fields Provided

| Field | Quality | Notes |
|-------|---------|-------|
| Full name | High | Official registered name |
| Date of birth | High | Verified |
| Nationality | High | Primary nationality |
| Current club | Medium | Stale if CSV not refreshed |
| Market value | Medium | Point-in-time snapshot |
| Position | High | Primary position |
| Height | Medium | Not always present |
| Foot | Medium | Not always present |

## Known Issues

- CSV is a point-in-time snapshot — club assignments go stale
- Some players have abbreviated first names
- Market values are in euros, formatted inconsistently

## Pipeline Integration

- Ingested by: `pipeline/ingest/load_transfermarkt.py`
- Raw table: `raw.raw_tm_players`
- Priority: Wins over all other sources for factual fields (DOB, nationality, name)

## TODO

- [ ] Document exact CSV column names and types
- [ ] Document refresh procedure
- [ ] Add data quality metrics (null rates, coverage percentages)
