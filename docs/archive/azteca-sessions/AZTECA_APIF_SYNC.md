# Azteca Task: API-Football → Warehouse Sync

## Context
The warehouse has stale club data for some players. The Transfermarkt CSV doesn't track players who move to smaller leagues (MLS, Liga BetPlay, etc.). API-Football has current data and our API key is configured. A new script syncs API-Football directly to the warehouse.

## Priority: Start with Colombia (the test case)
Carlo's friends caught errors in the Colombian squad. Three specific players:
- **James Rodríguez** — warehouse says Olympiakos, actually at Minnesota United (MLS)
- **David Ospina** — warehouse says Napoli, actually at Atlético Nacional (Liga BetPlay)
- **Luis Díaz** — warehouse correctly says Bayern München (but verify photo is correct)

## Steps

### Step 1: Dry Run — Colombia
```bash
cd /path/to/el-capi-data
python -m pipeline.sync.sync_apif_warehouse team COL --dry-run
```

**Expected:** List of ~28 Colombian players with current warehouse clubs and confidence levels.

**Checkpoint:** Verify James Rodríguez and David Ospina appear in the list. Their clubs should be Olympiakos and Napoli (the stale data we're about to fix).

### Step 2: Sync Colombia
```bash
python -m pipeline.sync.sync_apif_warehouse team COL
```

**Expected output:**
- James Rodríguez: club change (Olympiakos → current club from APIF)
- David Ospina: club change (Napoli → current club from APIF)
- Luis Díaz: likely no changes (Bayern München is correct)
- Photo URLs updated for players that APIF has better photos for
- APIF IDs saved as aliases for future direct lookups

**Report:** For each player that changed, list the old and new club.

### Step 3: Verify the Three Test Cases
After sync, query the warehouse directly:
```sql
SELECT p.known_as, pc.current_club, pc.current_league, p.photo_url, p.data_confidence
FROM players p
JOIN player_career pc ON pc.player_id = p.id
WHERE p.id IN (
  '47184c5c-44dd-4743-b132-c0faadb10331',  -- Luis Díaz
  '35aae03f-c874-4a61-8a74-82f340ce08c7',  -- James Rodríguez
  -- Find Ospina's UUID from the sync output
)
```

### Step 4: Regenerate players.ts
After confirming the warehouse is updated, regenerate the static file:
```bash
python -m pipeline.generators.generate_players_ts
```

This pushes the fresh club data into the frontend.

### Step 5: Sync Remaining WC Teams (Optional)
If Colombia worked well:
```bash
# Sync all WC 2026 players
python -m pipeline.sync.sync_apif_warehouse all --limit 50  # test batch first
python -m pipeline.sync.sync_apif_warehouse all              # full run (~1,200 players)
```

Or target stale players only:
```bash
python -m pipeline.sync.sync_apif_warehouse stale
```

### Step 6: Report
Report back with:
1. Colombia sync results (which players changed, old → new clubs)
2. Verification of the three test cases
3. Any players APIF couldn't find (not_found / no_match)
4. Total API credits used
5. Recommendation on whether to run full sync

## Notes
- API-Football Pro plan has 7,500 credits/day. Colombia sync uses ~42 credits (safe).
- Full WC sync uses ~1,800 credits (well within budget).
- The script saves APIF IDs as aliases in `player_aliases` — subsequent syncs are faster (direct ID lookup instead of name search).
- Photo URLs from APIF are fresh headshots. The `/default.jpg` filter in the app layer still applies.
- The script updates `player_career.current_club` and `player_career.current_league` directly.
- After any warehouse update, run `generate_players_ts` to push changes to the frontend.
