# Source 02: Static Bios (JSON)

**Priority Rank**: 2
**Type**: Static JSON files (manually curated)
**Refresh**: Manual
**Coverage**: Biographical data for key players

## Fields Provided

| Field | Quality | Notes |
|-------|---------|-------|
| Full name | High | Curated |
| Date of birth | High | Verified against multiple sources |
| Birth place | High | City + country |
| Nationality | High | Including dual nationality |
| Height | Medium | Not always present |
| Biography text | High | Narrative content |

## Pipeline Integration

- Ingested by: `pipeline/ingest/load_static_bios.py`
- Raw table: `raw.raw_static_bios`
- Priority: Rank 2 — wins over Squads, API-Football, GPT for fields it covers

## TODO

- [ ] Document JSON schema
- [ ] Document file location and naming convention
- [ ] Add coverage metrics
