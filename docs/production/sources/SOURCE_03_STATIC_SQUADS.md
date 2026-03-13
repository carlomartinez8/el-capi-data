# Source 03: Static Squads (JSON)

**Priority Rank**: 3
**Type**: Static JSON files (national team rosters)
**Refresh**: Manual (updated for major tournaments)
**Coverage**: Squad lists for WC 2026 qualifying nations

## Fields Provided

| Field | Quality | Notes |
|-------|---------|-------|
| Player name | High | As listed in squad announcement |
| National team | High | Country code |
| Position | High | Squad position |
| Jersey number | High | Tournament-specific |
| Club at time of selection | Medium | Point-in-time |

## Pipeline Integration

- Ingested by: `pipeline/ingest/load_static_squads.py`
- Raw table: `raw.raw_static_squads`
- Priority: Rank 3 — useful for squad composition, national team membership

## TODO

- [ ] Document JSON schema and file naming
- [ ] Document which tournaments/qualifiers are covered
- [ ] Add coverage metrics
