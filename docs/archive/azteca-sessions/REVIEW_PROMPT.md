# Azteca: Independent Documentation & State Audit

**From:** Carlo Martinez
**Date:** March 14, 2026
**Priority:** HIGH — Do this before any other work

---

## Your Task

You are Azteca, the infrastructure and data pipeline agent. I need you to do a **cold-start audit** of both repos as if you were a new agent picking up this project for the first time. The goal is to answer one question honestly:

**If I dropped a brand new agent (or a human contributor) into ~/el-capi/ today, would they be able to understand where we are, what works, what's broken, and what to do next — without asking anyone?**

---

## Instructions

### Phase 1: Read Everything (Do NOT write anything yet)

Read these files in order. Do not skim — read them fully.

1. `~/el-capi/OUTSTANDING.md`
2. `~/el-capi/el-capi-data/CLAUDE.md`
3. `~/el-capi/la-copa-mundo/CLAUDE.md`
4. `~/el-capi/la-copa-mundo/AGENTS.md`
5. `~/el-capi/la-copa-mundo/PROJECT-STATUS.md`
6. `~/el-capi/el-capi-data/docs/production/DATA_LINEAGE.md`
7. `~/el-capi/la-copa-mundo/docs/log/STATUS.md`
8. `~/el-capi/la-copa-mundo/docs/production/ARCHITECTURE.md`

### Phase 2: Verify Claims Against Reality

Don't trust the docs — verify them. Run these checks:

```bash
# 1. Does the code compile?
cd ~/el-capi/la-copa-mundo && npx tsc --noEmit

# 2. What's actually in the admin players API? Does it match what the docs say?
head -80 src/app/api/admin/players/route.ts

# 3. What model is Capi actually using? Check the source of truth.
grep -r "claude-" src/lib/capi/ --include="*.ts" | head -20

# 4. What tools does Capi actually have?
grep -A2 "name:" src/lib/capi/tools.ts | head -40

# 5. Does the system prompt reference data_confidence or old conflict model?
grep -i "conflict\|confidence\|blocked" src/lib/capi/system-prompt.ts | head -20

# 6. What does the pipeline actually output? Check file dates and sizes.
ls -la ~/el-capi/el-capi-data/data/output/*.json 2>/dev/null
ls -la ~/el-capi/el-capi-data/data/output/supabase_seed/*.sql 2>/dev/null

# 7. Is el-capi-data a git repo?
cd ~/el-capi/el-capi-data && git status 2>&1 | head -5

# 8. What's uncommitted in la-copa-mundo?
cd ~/el-capi/la-copa-mundo && git status 2>&1 | head -20

# 9. Check the actual admin players page — does it use data_confidence?
grep -c "data_confidence" src/app/\\[locale\\]/\\(app\\)/admin/players/page.tsx

# 10. Does OUTSTANDING.md actually exist and is it findable?
cat ~/el-capi/OUTSTANDING.md | head -5
```

### Phase 3: Write Your Assessment

After reading everything and running the verification checks, write a report answering these questions. Be brutally honest — I need truth, not politeness.

#### A. Clarity Test
1. Could a new agent understand what this project IS in under 2 minutes of reading?
2. Could they find what to work on next without asking Carlo?
3. Are the reading-order instructions clear? (Which file first, second, third?)
4. Is there any circular referencing that would confuse someone? (Doc A says "see Doc B", Doc B says "see Doc A")

#### B. Accuracy Test
1. Do the player counts in the docs match reality? (Check actual DB/file counts if possible)
2. Does the stated model (claude-sonnet-4-6) match what's in the code?
3. Does the stated data model (data_confidence) match what's in the code?
4. Are there any docs that reference things that no longer exist? (old files, old models, old table names, archived docs)
5. Are there any TODO items marked as done that aren't actually done?

#### C. Completeness Test
1. Is there anything important about the system that ISN'T documented anywhere?
2. Are there config files, env vars, or setup steps that a new person would miss?
3. Are error recovery procedures documented? (What to do when things break)
4. Is the cost model clear? (What costs money, how much, when)

#### D. Contradiction Test
1. Do any two documents disagree with each other on facts?
2. Are priority levels (P0/P1/P2/P3) consistent across docs?
3. Do ownership assignments in AGENTS.md match reality?

#### E. Navigation Test
1. If I ask "how does the pipeline work?" — can you get to the answer in ≤2 hops?
2. If I ask "what's broken right now?" — can you get to the answer in 1 hop?
3. If I ask "who owns the admin dashboard?" — can you get a clear answer?
4. Is the document map in OUTSTANDING.md accurate and complete?

### Phase 4: Recommendations

If you find problems, list them as concrete fixes with file paths. Don't just say "this could be better" — say exactly what to change and where.

Format:
```
ISSUE: [description]
FILE: [path]
FIX: [exact change needed]
SEVERITY: BLOCKING / IMPORTANT / MINOR
```

---

## Rules

- Do NOT make any changes to any files during this audit. Read only.
- Do NOT skip the verification commands. The whole point is checking docs against reality.
- If you can't run a command (e.g., Supabase is blocked), note it and move on.
- Be specific. "The docs are mostly good" is not useful. "AGENTS.md line 130 says 632 players but warehouse has 1,176" is useful.
- Timebox this to ~30 minutes. If you're spending longer, you're going too deep.
