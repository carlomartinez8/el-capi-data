# Azteca — Independent Documentation & State Audit

**Date:** March 14, 2026  
**Prompt:** REVIEW_PROMPT.md (cold-start audit, verify claims against code)  
**Rule:** Don't trust the docs — verify them.

---

## Phase 2: Verification (10 Bash Checks)

| # | Check | Result |
|---|--------|--------|
| 1 | `npx tsc --noEmit` (la-copa-mundo) | **PASS** — 0 errors |
| 2 | Admin players API (`head -80 route.ts`) | **PASS** — Warehouse-backed, `data_confidence`, pagination; matches docs |
| 3 | Capi model in code | **MIXED** — Main chat: `CAPI_MODEL \|\| 'claude-sonnet-4-6'` in `chat/route.ts`. Groups Capi: `claude-sonnet-4-5-20250929`. Admin settings & premium config: `claude-sonnet-4-5-20250929`. Docs say "claude-sonnet-4-6" for Capi; main path is correct, others stale |
| 4 | Capi tools | **PASS** — web_search, search_players, get_player_details, get_squad, get_live_matches, get_career_history, run_analytics_query. Doc says "5 tools + web search"; actual is 6 named tools + web_search (get_transfer_history → get_career_history) |
| 5 | System prompt re conflict/confidence | **PASS** — No old conflict model. "confidence" appears only in personality/calibration sense (CONFIDENCE CALIBRATION), not `data_confidence` or "blocked" |
| 6 | Pipeline output files | **FAIL** — `data/output/players_golden.json` has **638** players (verified `len(json.load())`). Docs (OUTSTANDING, DATA_LINEAGE, el-capi-data CLAUDE) say "1,176" for canonical output. Warehouse is 1,176 from other flows (squad build, promote staging, generator); golden file on disk is stale |
| 7 | el-capi-data git | **PASS** — Git repo, up to date with origin. Unstaged: deleted docs (PIPELINE_MIGRATION_STRATEGY, lacopamundo-player-data-pipeline), untracked (CLAUDE.md, data/, archive docx) |
| 8 | la-copa-mundo git | **PASS** — Up to date with origin. Uncommitted: AGENTS.md, CHANGELOG.md, CLAUDE.md, PROJECT-STATUS.md, STATUS.md, ARCHITECTURE.md, CAPI_DATA_SOURCES.md, package.json |
| 9 | Admin players page `data_confidence` | **PASS** — 7 occurrences in `src/app/[locale]/(app)/admin/players/page.tsx` |
| 10 | OUTSTANDING.md exists | **PASS** — Present at repo root, findable |

---

## Phase 3: Assessment

### A. Clarity Test

1. **Could a new agent understand what this project IS in under 2 minutes?**  
   **Mostly yes.** OUTSTANDING.md and the Document Map give a clear "what we are" (1,176 players, 42 squads, Capi, warehouse, admin). The opening paragraph of OUTSTANDING is dense but accurate. A new agent would need to ignore stale numbers in other files (632/638) and trust the top-level summary.

2. **Could they find what to work on next without asking Carlo?**  
   **Yes.** OUTSTANDING.md is the single source of truth; P0/P1/P2/P3 and the Document Map are clear. Reading order is stated (OUTSTANDING first, then CLAUDE.md by repo, etc.).

3. **Are the reading-order instructions clear?**  
   **Yes.** REVIEW_PROMPT and OUTSTANDING both list order (OUTSTANDING → el-capi-data CLAUDE → la-copa-mundo CLAUDE → AGENTS → PROJECT-STATUS → DATA_LINEAGE → STATUS → ARCHITECTURE). No ambiguity.

4. **Circular referencing?**  
   **Minor.** OUTSTANDING points to DATA_LINEAGE and ARCHITECTURE; those point back to OUTSTANDING or each other for "what to do next" or "current state." Not harmful; the loop is intentional (OUTSTANDING = priorities, others = depth).

---

### B. Accuracy Test

1. **Player counts vs reality**  
   **Inconsistent.** Warehouse and generated `players.ts`: **1,176 players, 42 teams** (correct; verified in players.ts header). Docs that are wrong: **ARCHITECTURE.md** line 116 says `players.ts` is "638 players across 48 teams." **el-capi-data CLAUDE.md** line 94 says "players.ts — WC 2026 squad rosters (48 teams)" without updating to 42. **players_golden.json** on disk: **638**; multiple docs say "1,176" for "canonical output" or "players_golden."

2. **Stated model (claude-sonnet-4-6) vs code**  
   **Main Capi:** Matches (`chat/route.ts`). **Groups Capi and admin/settings/premium:** Still reference `claude-sonnet-4-5` or `claude-sonnet-4-5-20250929`.

3. **Data model (data_confidence) vs code**  
   **Matches.** Admin API and players page use `data_confidence`; no "blocked" or old conflict model in active code paths.

4. **Docs referencing things that no longer exist**  
   - **ARCHITECTURE.md** §18 / project structure: "638 players across 48 teams" for `players.ts` — file is now 1,176 / 42.  
   - **el-capi-data PIPELINE.md, DATA-SOURCES.md, DATA-PIPELINE-AUDIT.md:** Still say 632 players, 632 in warehouse tables — outdated.  
   - **AGENTS.md** completed bullets: Many "632" references (e.g. "632 players", "632/632 verified", "browse all 632 players") — historical but confusing alongside "Current State: 1,176."

5. **TODO items marked done that aren’t**  
   OUTSTANDING "Completed" lists "Commit & Push Both Repos" as P0 #2; at audit time both repos had uncommitted changes. So either the item was completed and new changes were made after, or the checklist is ahead of state. Not a "done but not really" — more a "state changed after completion."

---

### C. Completeness Test

1. **Important system behavior not documented**  
   - **How the warehouse got to 1,176** is only partly in DATA_LINEAGE (squad build, promote staging, generator). The fact that `players_golden.json` is 638 and not the current load path for 1,176 could be stated explicitly (e.g. "Current warehouse is not built from a single run of players_golden; it was expanded via WC squad build and staging promotion").  
   - **Generator as bridge:** `generate_players_ts` is the bridge from warehouse → `players.ts`; DATA_LINEAGE and OUTSTANDING mention it but a one-line "frontend roster comes from this script" in ARCHITECTURE would help.

2. **Config / env / setup a new person would miss**  
   - **CAPI_MODEL** is optional (defaults to claude-sonnet-4-6); documented implicitly via code.  
   - **API_FOOTBALL_KEY** for APIF sync is in task docs (AZTECA_APIF_SYNC) but not in a single "required env vars" list in CLAUDE or DATA_LINEAGE.  
   - **SUPABASE_DATABASE_URI** vs **DATABASE_URL** (used in runbooks) — both appear in scripts; not clearly documented which to use where.

3. **Error recovery**  
   - OUTSTANDING says "After completing any P0 or P1 item… Did the change break anything? (run `npx tsc --noEmit`)". No "what to do when pipeline fails" or "how to rollback warehouse" in one place. DATA_LINEAGE has lessons learned but not a runbook.

4. **Cost model**  
   - DATA_LINEAGE §7 has a cost table (enrichment, verification, APIF). Clear. OUTSTANDING doesn’t repeat it but points to DATA_LINEAGE. Adequate.

---

### D. Contradiction Test

1. **Two documents disagree on facts**  
   - **Player count:** 632/638 vs 1,176 across AGENTS.md (completed vs current), ARCHITECTURE.md (structure vs schema), PIPELINE.md, DATA-SOURCES.md, DATA_LINEAGE (current state), OUTSTANDING.  
   - **players.ts:** ARCHITECTURE says "638 players across 48 teams"; file and OUTSTANDING say 1,176 / 42.  
   - **Tool count:** OUTSTANDING says "5 tools + web search"; tools.ts has 6 named tools + web_search (get_career_history is the 6th; doc may count get_transfer_history as one of five but it was renamed).

2. **Priority levels (P0/P1/P2/P3) consistent?**  
   **Yes.** OUTSTANDING drives; el-capi-data and la-copa-mundo CLAUDE refer to OUTSTANDING. No conflicting P0/P1 labels.

3. **AGENTS.md ownership vs reality**  
   **Largely consistent.** Admin players page and API are in Azteca’s area; Capi tools and system prompt in Pelé’s. No obvious ownership conflicts.

---

### E. Navigation Test

1. **"How does the pipeline work?" → ≤2 hops**  
   **Yes.** OUTSTANDING Document Map → DATA_LINEAGE.md. One hop.

2. **"What's broken right now?" → 1 hop**  
   **Yes.** OUTSTANDING.md "What doesn't work yet" and P0/P1 list.

3. **"Who owns the admin dashboard?"**  
   **Clear.** AGENTS.md Ownership Map: Azteca (admin layout, players, reconciliation, pipeline, API routes).

4. **Document map in OUTSTANDING accurate and complete?**  
   **Mostly.** Table covers "what to work on," pipeline, architecture, agents, strategy, setup, log, lessons. Missing: a single "env vars for all scripts" entry (could point to each repo’s CLAUDE or a shared env doc).

---

## Phase 4: Concrete Fixes (File Paths + Severity)

```
ISSUE: ARCHITECTURE.md says players.ts is "638 players across 48 teams"; file is 1,176 / 42.
FILE: la-copa-mundo/docs/production/ARCHITECTURE.md
FIX: Line 116 (project structure): change "638 players across 48 teams" to "1,176 players across 42 confirmed squads (auto-generated from warehouse)."
SEVERITY: IMPORTANT

ISSUE: el-capi-data CLAUDE.md says "players.ts — WC 2026 squad rosters (48 teams)".
FILE: el-capi-data/CLAUDE.md
FIX: Line 94 (Static data): change "(48 teams)" to "(42 confirmed squads; generated from warehouse)."
SEVERITY: IMPORTANT

ISSUE: Docs claim "canonical output" or "players_golden.json" has 1,176 players; file on disk has 638.
FILE: el-capi-data/CLAUDE.md (and DATA_LINEAGE.md if it says golden is 1,176)
FIX: In CLAUDE.md Critical Output Files table, add a note: "players_golden.json may be from an earlier run (638); current warehouse (1,176) was populated via squad build + staging promotion + generator. Regenerate seeds or use generator for current state." In DATA_LINEAGE §8, same caveat next to players_golden.json.
SEVERITY: IMPORTANT

ISSUE: OUTSTANDING says "5 tools + web search"; code has 6 named tools + web_search.
FILE: ~/el-capi/OUTSTANDING.md
FIX: Line 24: change "via 5 tools + web search" to "via 6 tools + web search (search_players, get_player_details, get_squad, get_live_matches, get_career_history, run_analytics_query)."
SEVERITY: MINOR

ISSUE: System prompt still references "get_transfer_history" in guidance; tool was renamed to get_career_history.
FILE: la-copa-mundo/src/lib/capi/system-prompt.ts
FIX: Lines 149 and 1325: replace "get_transfer_history" with "get_career_history".
SEVERITY: MINOR

ISSUE: Groups Capi and admin/settings/premium use claude-sonnet-4-5; docs say Capi is claude-sonnet-4-6.
FILE: la-copa-mundo/src/app/api/groups/[groupId]/capi/route.ts (MODEL), la-copa-mundo/src/app/api/admin/settings/route.ts, la-copa-mundo/src/lib/premium/config.ts
FIX: Either (a) align all routes to CAPI_MODEL || 'claude-sonnet-4-6' for consistency, or (b) document that only main chat uses 4-6 and groups/admin use 4-5. Prefer (a) if product intent is "Capi = 4-6 everywhere."
SEVERITY: IMPORTANT

ISSUE: AGENTS.md "Completed" bullets use 632/638 everywhere; "Current State" uses 1,176. Confusing for new readers.
FILE: la-copa-mundo/AGENTS.md
FIX: Add a one-line note after "Current State (as of Mar 14, 2026)": "All player counts in 'Completed' bullets below are historical (632/638/677); current warehouse and app use 1,176." Optionally add (historical) next to 632/638 in a few key bullets.
SEVERITY: MINOR

ISSUE: PIPELINE.md and DATA-SOURCES.md still say 632 players and 632 in warehouse tables.
FILE: el-capi-data/docs/production/PIPELINE.md, el-capi-data/docs/production/DATA-SOURCES.md
FIX: Add a "Current state (Mar 14, 2026)" callout at top: "Warehouse now has 1,176 players across 42 squads (see DATA_LINEAGE.md). Numbers in this doc refer to the classic pipeline run (632)." Then leave body as-is for pipeline logic, or update table row counts to "632 (classic) / 1,176 (current warehouse)."
SEVERITY: IMPORTANT

ISSUE: la-copa-mundo CLAUDE.md says el-capi-data stack is "Python 3.11+, pandas, Prefect, dbt"; el-capi-data CLAUDE says "pandas, thefuzz, OpenAI SDK" (no Prefect/dbt in main flow).
FILE: la-copa-mundo/CLAUDE.md
FIX: Line 24 (Repos table): change "Prefect, dbt" to "pandas, thefuzz, OpenAI SDK" (or "Python 3.11+, pandas, thefuzz") to match actual pipeline.
SEVERITY: MINOR

ISSUE: P0 #2 "Commit & Push Both Repos" — at audit time both repos had uncommitted changes.
FILE: ~/el-capi/OUTSTANDING.md
FIX: If P0 #2 is considered done, no change. If not, move it back to P0 and run git add/commit/push. If done but new edits exist, add a note under Completed: "Commit & Push (Mar 14) — subsequent uncommitted edits in both repos; re-commit when ready."
SEVERITY: MINOR
```

---

## Summary Table

| Dimension      | Verdict | Notes |
|----------------|---------|--------|
| **Clarity**    | Good    | Single entry point (OUTSTANDING), clear order and doc map. Stale numbers elsewhere reduce clarity. |
| **Accuracy**   | Mixed   | Top-level docs (OUTSTANDING, current-state sections) accurate; ARCHITECTURE, pipeline docs, AGENTS completed bullets, and golden file count are wrong or stale. |
| **Completeness** | Good  | Pipeline, costs, and ownership covered. Env vars and error recovery could be centralized. |
| **Contradictions** | Present | 632/638 vs 1,176; players.ts 48 vs 42; 5 vs 6 tools; model 4-5 vs 4-6 in secondary routes. |
| **Navigation** | Good    | ≤2 hops to pipeline and "what's broken"; document map accurate. |

**Bottom line:** A new agent who reads OUTSTANDING.md first and trusts it over scattered bullets will understand priorities and current state. If they grep the codebase and key files (players.ts header, chat route model, tools.ts), they will find the inaccuracies above. Applying the fixes by severity will bring docs in line with reality.
