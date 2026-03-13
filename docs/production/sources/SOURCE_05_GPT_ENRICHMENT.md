# Source 05: GPT Enrichment

**Priority Rank**: 5 (lowest — fills gaps only, never overwrites higher-ranked sources)
**Type**: OpenAI GPT-4o API calls
**Refresh**: On-demand during pipeline enrichment stage
**Coverage**: All players — used to fill missing fields and generate narratives

## Fields Provided

| Field | Quality | Notes |
|-------|---------|-------|
| Narrative bio | High | Creative, fan-friendly player descriptions |
| Fun facts | Medium | Sometimes hallucinated — needs verification |
| Playing style | Medium | Subjective but engaging |
| Club assignment | **Low** | Often stale or wrong (root cause of Luis Díaz issue) |
| DOB | **Low** | Drops ~25% of input fields |
| Height | **Low** | Drops ~25% of input fields |

## Critical Known Issue

GPT enrichment currently provides 100% of club assignments in the pipeline output. This is wrong — clubs should come from API-Football (Source 04) or Transfermarkt (Source 01). The enrichment step drops ~25% of fields that were present in the input, causing data loss.

**Root cause**: Field name mismatches between GPT schema and admin app expectations. The merged data (with complete coverage from higher-ranked sources) never feeds back to canonical output.

## Pipeline Integration

- Script: `pipeline/enrich/run_enrichment.py` (refactored to narrative-only mode)
- Priority: Rank 5 — should ONLY provide narrative content, fun facts, playing style
- Factual fields (club, DOB, height) should come from Sources 1-4

## Business Rules

1. GPT enrichment NEVER overwrites factual fields from higher-ranked sources
2. GPT is the exclusive source for: narrative bios, fun facts, playing style descriptions
3. All GPT-generated factual claims must be verified against source data
4. Confidence score attached to every GPT-generated field

## TODO

- [ ] Verify narrative-only refactor is working correctly
- [ ] Remove GPT as source for factual fields in merge layer
- [ ] Add hallucination detection for fun facts
- [ ] Document prompt templates used for enrichment
