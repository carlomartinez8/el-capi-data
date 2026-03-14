# Azteca Task: Generate players.ts from Warehouse

## Context
We've built the app-to-warehouse bridge. The frontend reads player data from a static TypeScript file (`la-copa-mundo/src/data/players.ts`). We've created a Python generator script that queries the warehouse and regenerates this file with warehouse UUIDs embedded, replacing the old hand-curated static data.

This is the first run. After this, the generator becomes a repeatable pipeline step.

## Prerequisites
- Supabase credentials (SUPABASE_URL + SUPABASE_SERVICE_KEY)
- `supabase` Python package installed
- Warehouse tables populated: `players`, `player_career`, `player_tournament`

## Steps

### Step 1: Dry Run — Verify data before writing
```bash
cd /path/to/el-capi-data
python -m pipeline.generators.generate_players_ts --dry-run
```

**Expected output:**
- ~42 teams with data
- ~1,092 players (42 teams × 26 primary squad each)
- Position breakdown should show reasonable distribution (GK ~84, DEF ~300+, MID ~350+, FWD ~300+)
- All players should have warehouseId (With UUID count = total)
- Some players may have age=0 (missing DOB) or Unknown club

**Checkpoint:** Review the stats. If any team has 0 players, or total is wildly off from ~1,092, STOP and report.

### Step 2: Generate the file
```bash
python -m pipeline.generators.generate_players_ts
```

This writes to `../la-copa-mundo/src/data/players.ts` by default.

**Verify the output file:**
```bash
wc -l ../la-copa-mundo/src/data/players.ts
head -20 ../la-copa-mundo/src/data/players.ts
```

Should show:
- Header comment with "AUTO-GENERATED from warehouse data"
- Generation timestamp
- Team and player counts matching dry-run

### Step 3: Validate structure
```bash
# Check TypeScript compiles (if ts toolchain available)
cd ../la-copa-mundo
npx tsc --noEmit src/data/players.ts 2>&1 | head -20

# Or just verify the file is valid JS/TS syntax
node -e "
const fs = require('fs');
const content = fs.readFileSync('src/data/players.ts', 'utf-8');
// Check for key exports
const hasSquads = content.includes('export const SQUADS');
const hasPlayerSlug = content.includes('export function playerSlug');
const hasFindPlayer = content.includes('export function findPlayerBySlug');
const hasGetSquad = content.includes('export function getSquad');
const hasWarehouseId = content.includes('warehouseId');
console.log('SQUADS export:', hasSquads);
console.log('playerSlug export:', hasPlayerSlug);
console.log('findPlayerBySlug export:', hasFindPlayer);
console.log('getSquad export:', hasGetSquad);
console.log('warehouseId field:', hasWarehouseId);
console.log('ALL CHECKS PASSED:', hasSquads && hasPlayerSlug && hasFindPlayer && hasGetSquad && hasWarehouseId);
"
```

### Step 4: Spot-check specific teams
```bash
# Count players per team
node -e "
const fs = require('fs');
const content = fs.readFileSync('src/data/players.ts', 'utf-8');
// Extract team codes and their player counts using regex
const teamPattern = /^\s+([A-Z]{3}):\s*\[/gm;
let match;
const teams = [];
while ((match = teamPattern.exec(content)) !== null) {
  teams.push(match[1]);
}
console.log('Teams found:', teams.length);
console.log('Teams:', teams.join(', '));
"
```

Spot-check these teams have ~26 players each:
- ARG (Argentina)
- BRA (Brazil)
- USA (United States)
- MEX (Mexico)
- FRA (France)

### Step 5: Report
Report back with:
1. Dry-run stats (teams, players, positions, warnings)
2. File generation result (lines written, file size)
3. Validation results (all exports present, warehouseId present)
4. Spot-check team counts
5. Any warnings or issues found

## Notes
- The generator maps positions: Goalkeeper→GK, Defender→DEF, Midfielder→MID, Forward→FWD, Missing→MID
- Ages are calculated as of WC 2026 kickoff (June 11, 2026)
- Players with missing DOB will show age=0
- Players with no career record will show club="Unknown"
- Squads are sorted: captain first, then by jersey number
- Playoff placeholder codes (PLA, PLB, PLC, PLD, PL1, PL2) are included as empty arrays
- The `/default.jpg` photo URLs from Transfermarkt are filtered out in the app layer (player-photos.ts), not in the generator
