#!/usr/bin/env python3
"""
El Capi Data Pipeline v2 — Full Orchestrator with Assertion Gates

Runs all stages end-to-end with contracts between stages that halt on failure.

Stages:
  1. INGEST     — Load raw data from all sources (TM CSV, static squads, static bios)
  2. DEDUP      — Fuzzy-match TM players to WC squads, produce flat canonical
  3. MERGE      — Source-priority merge with field-level attribution (FACTS)
  4. ENRICH     — GPT narrative enrichment (STORIES only, no facts) [optional]
  5. COMBINE    — Merge facts + narratives → golden canonical output
  6. VERIFY     — GPT-4o accuracy check on critical fields [optional]
  7. DEPLOY     — Generate Supabase SQL seed files

Usage:
    python run_full_pipeline.py                    # full pipeline (no GPT steps)
    python run_full_pipeline.py --with-enrichment  # include GPT narrative enrichment
    python run_full_pipeline.py --with-verify      # include GPT-4o verification
    python run_full_pipeline.py --all              # all steps including GPT
    python run_full_pipeline.py --from merge       # resume from a specific stage
    python run_full_pipeline.py --strict           # halt on ANY assertion failure (default)
    python run_full_pipeline.py --lenient          # warn on assertion failures, don't halt
"""

import sys
import json
import time
import shutil
from datetime import datetime
from pathlib import Path

from pipeline.config import OUTPUT_DIR, RAW_DIR, INTERMEDIATE_DIR
from pipeline.assertions import (
    gate,
    assert_wc_team_sizes,
    assert_no_cross_team_duplicates,
    assert_field_coverage,
    assert_merged_field_coverage,
    assert_canonical_ids_unique,
    assert_min_player_count,
    PipelineAssertionError,
)


# ─── Stage definitions ────────────────────────────────────────────────

STAGES = ["ingest", "dedup", "merge", "enrich", "combine", "verify", "deploy"]


def snapshot_raw(label: str):
    """Save a timestamped snapshot of current output for audit trail."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    snap_dir = RAW_DIR / f"snapshot_{ts}_{label}"
    snap_dir.mkdir(parents=True, exist_ok=True)

    for fname in ["players_canonical_latest.json", "players_merged.json", "players_golden.json"]:
        src = OUTPUT_DIR / fname
        if src.exists():
            shutil.copy2(src, snap_dir / fname)

    print(f"  📸 Snapshot saved: {snap_dir.name}")
    return snap_dir


# ─── STAGE 1: INGEST ──────────────────────────────────────────────────

def stage_ingest():
    print("\n" + "=" * 60)
    print("  STAGE 1: INGEST")
    print("=" * 60)

    from pipeline.ingest.transfermarkt import load_players as load_tm_players
    from pipeline.ingest.static_squads import load_static_squads

    print("\n  [Transfermarkt CSV]")
    tm_df = load_tm_players()

    print("\n  [Static WC Squads]")
    static_df = load_static_squads()

    # Save intermediates
    tm_df.to_csv(INTERMEDIATE_DIR / "tm_ingested.csv", index=False)
    static_df.to_csv(INTERMEDIATE_DIR / "static_ingested.csv", index=False)

    print(f"\n  Ingested: {len(tm_df):,} TM players + {len(static_df)} squad players")

    return tm_df, static_df


# ─── STAGE 2: DEDUP ──────────────────────────────────────────────────

def stage_dedup(tm_df, static_df, strict: bool = True):
    print("\n" + "=" * 60)
    print("  STAGE 2: DEDUP")
    print("=" * 60)

    from pipeline.dedup.resolver import deduplicate
    from pipeline.qa.checks import run_checks
    from pipeline.export.local import export_canonical, export_review, export_qa_report, export_summary

    canonical_df, review_df = deduplicate(tm_df, static_df)
    qa_df = run_checks(canonical_df)
    export_canonical(canonical_df)
    export_review(review_df)
    export_qa_report(qa_df)
    export_summary(canonical_df, review_df, qa_df)

    # Load the flat canonical output for assertions
    latest_path = OUTPUT_DIR / "players_canonical_latest.json"
    with open(latest_path) as f:
        flat_players = json.load(f)

    wc_players = [p for p in flat_players if p.get("in_wc_squad")]

    # ── Assertion gate ──
    gate("DEDUP", [
        assert_min_player_count(wc_players, 600, "WC squad players"),
        assert_wc_team_sizes(wc_players, min_size=20, max_size=30),
        assert_no_cross_team_duplicates(wc_players),
        assert_field_coverage(wc_players, "date_of_birth", min_pct=90.0, label="DOB (flat)"),
        assert_field_coverage(wc_players, "position", min_pct=90.0, label="Position (flat)"),
        assert_field_coverage(wc_players, "current_club_name", min_pct=85.0, label="Club (flat)"),
    ], strict=strict)

    return canonical_df, review_df


# ─── STAGE 3: MERGE ──────────────────────────────────────────────────

def stage_merge(strict: bool = True) -> list[dict]:
    print("\n" + "=" * 60)
    print("  STAGE 3: SOURCE-PRIORITY MERGE")
    print("=" * 60)

    from pipeline.reconcile.merge import run_merge_from_flat

    merged = run_merge_from_flat(wc_only=True)

    # ── Assertion gate ──
    gate("MERGE", [
        assert_min_player_count(merged, 600, "merged players"),
        assert_merged_field_coverage(merged, "date_of_birth", min_pct=95.0),
        assert_merged_field_coverage(merged, "position", min_pct=90.0),
        assert_merged_field_coverage(merged, "current_club", min_pct=85.0),
        assert_merged_field_coverage(merged, "nationality", min_pct=95.0),
        assert_merged_field_coverage(merged, "height_cm", min_pct=85.0),
        assert_merged_field_coverage(merged, "market_value_eur", min_pct=75.0),
    ], strict=strict)

    return merged


# ─── STAGE 4: ENRICH (optional) ──────────────────────────────────────

def stage_enrich(strict: bool = True):
    """
    GPT narrative enrichment — ONLY narrative fields, not facts.
    This is optional; the pipeline works without it (facts come from merge).
    """
    print("\n" + "=" * 60)
    print("  STAGE 4: GPT NARRATIVE ENRICHMENT")
    print("=" * 60)

    # For now, use existing enrichment and just note it's optional
    enriched_path = OUTPUT_DIR / "players_enriched.json"
    if enriched_path.exists():
        with open(enriched_path) as f:
            enriched = json.load(f)
        print(f"  Using existing enriched data: {len(enriched)} players")
        print(f"  (To re-run enrichment: python run_enrichment.py)")
    else:
        print(f"  ⚠ No enriched data found — golden output will be facts-only")
        print(f"  Run: python run_enrichment.py")
        return

    # ── Assertion gate (lenient — narratives are nice-to-have) ──
    gate("ENRICH", [
        assert_min_player_count(enriched, 500, "enriched players"),
        assert_field_coverage(enriched, "story.origin_story_en", min_pct=70.0, label="Origin stories"),
        assert_field_coverage(enriched, "playing_style.style_summary_en", min_pct=70.0, label="Style summaries"),
    ], strict=False)  # Always lenient — narratives don't block


# ─── STAGE 5: COMBINE ────────────────────────────────────────────────

def stage_combine(strict: bool = True) -> list[dict]:
    print("\n" + "=" * 60)
    print("  STAGE 5: GOLDEN OUTPUT COMBINER")
    print("=" * 60)

    from pipeline.combine import run_combine

    golden = run_combine()

    # ── Assertion gate ──
    gate("COMBINE", [
        assert_min_player_count(golden, 600, "golden players"),
        assert_canonical_ids_unique(golden),
        assert_field_coverage(golden, "identity.date_of_birth", min_pct=95.0, label="Golden DOB"),
        assert_field_coverage(golden, "career.position_primary", min_pct=90.0, label="Golden Position"),
        assert_field_coverage(golden, "career.current_club", min_pct=85.0, label="Golden Club"),
        assert_field_coverage(golden, "identity.nationality_primary", min_pct=95.0, label="Golden Nationality"),
        assert_field_coverage(golden, "identity.height_cm", min_pct=85.0, label="Golden Height"),
    ], strict=strict)

    return golden


# ─── STAGE 6: VERIFY (optional) ──────────────────────────────────────

def stage_verify(strict: bool = True):
    """GPT-4o verification of critical fields — expensive, run on schedule."""
    print("\n" + "=" * 60)
    print("  STAGE 6: VERIFICATION (GPT-4o)")
    print("=" * 60)

    from pipeline.verify.critical_fields import run_verification

    print("  Running GPT-4o verification on critical fields...")
    print("  (This costs ~$1.90 and takes ~5 minutes)")
    run_verification()

    # Load results
    diff_path = OUTPUT_DIR / "verification_diff.json"
    if diff_path.exists():
        with open(diff_path) as f:
            diffs = json.load(f)

        tier1_changes = [d for d in diffs if any(c.get("tier") == 1 for c in d.get("changes", []))]
        if tier1_changes and strict:
            print(f"\n  ⚠️  {len(tier1_changes)} players have Tier 1 (IMPERDONABLE) corrections")
            print(f"  Review verification_diff.json and apply with:")
            print(f"    python -m pipeline.verify.apply_updates --tier 1 --apply")
            # Don't block — just warn strongly
        elif tier1_changes:
            print(f"\n  ℹ️  {len(tier1_changes)} Tier 1 corrections found (review recommended)")

        total_changes = sum(len(d.get("changes", [])) for d in diffs)
        print(f"\n  Verification found {total_changes} total field corrections across {len(diffs)} players")
    else:
        print(f"  No verification results found")


# ─── STAGE 7: DEPLOY ─────────────────────────────────────────────────

def stage_deploy(strict: bool = True):
    print("\n" + "=" * 60)
    print("  STAGE 7: DEPLOY (SQL Seed Generation)")
    print("=" * 60)

    from pipeline.sync.to_supabase import generate_sql

    generate_sql()

    # ── Verify output ──
    seed_dir = OUTPUT_DIR / "supabase_seed"
    expected_files = ["players.sql", "player_career.sql", "player_tournament.sql", "player_aliases.sql"]
    missing = [f for f in expected_files if not (seed_dir / f).exists()]

    if missing:
        print(f"\n  ⚠️  Missing seed files: {missing}")
        if strict:
            from pipeline.assertions import PipelineAssertionError
            raise PipelineAssertionError("DEPLOY", [f"Missing seed file: {f}" for f in missing])
    else:
        sizes = {f: (seed_dir / f).stat().st_size for f in expected_files}
        print(f"\n  Seed files generated:")
        for f, s in sizes.items():
            print(f"    {f}: {s/1024:.1f} KB")


# ─── Main orchestrator ───────────────────────────────────────────────

def run_full_pipeline(
    with_enrichment: bool = False,
    with_verify: bool = False,
    from_stage: str | None = None,
    strict: bool = True,
):
    start = time.time()

    print("=" * 60)
    print("  EL CAPI DATA PIPELINE v2")
    print("  Full orchestrator with assertion gates")
    print("=" * 60)
    print(f"  Enrichment: {'ON' if with_enrichment else 'OFF (facts-only)'}")
    print(f"  Verification: {'ON' if with_verify else 'OFF'}")
    print(f"  Strict mode: {'ON' if strict else 'LENIENT'}")
    if from_stage:
        print(f"  Resuming from: {from_stage}")

    stages_to_run = STAGES.copy()
    if from_stage:
        if from_stage not in STAGES:
            print(f"  ERROR: Unknown stage '{from_stage}'. Valid: {STAGES}")
            sys.exit(1)
        idx = STAGES.index(from_stage)
        stages_to_run = STAGES[idx:]

    try:
        # ── Stage 1: Ingest ──
        tm_df = static_df = None
        if "ingest" in stages_to_run:
            tm_df, static_df = stage_ingest()

        # ── Stage 2: Dedup ──
        if "dedup" in stages_to_run:
            if tm_df is None:
                import pandas as pd
                print("\n  Loading previously ingested data...")
                tm_df = pd.read_csv(INTERMEDIATE_DIR / "tm_ingested.csv")
                static_df = pd.read_csv(INTERMEDIATE_DIR / "static_ingested.csv")
            stage_dedup(tm_df, static_df, strict=strict)

        # ── Stage 3: Merge ──
        if "merge" in stages_to_run:
            stage_merge(strict=strict)

        # ── Stage 4: Enrich (optional) ──
        if "enrich" in stages_to_run and with_enrichment:
            stage_enrich(strict=strict)
        elif "enrich" in stages_to_run:
            print("\n  [STAGE 4: ENRICH — SKIPPED (use --with-enrichment to enable)]")

        # ── Stage 5: Combine ──
        if "combine" in stages_to_run:
            golden = stage_combine(strict=strict)
            snapshot_raw("combine")

        # ── Stage 6: Verify (optional) ──
        if "verify" in stages_to_run and with_verify:
            stage_verify(strict=strict)
        elif "verify" in stages_to_run:
            print("\n  [STAGE 6: VERIFY — SKIPPED (use --with-verify to enable)]")

        # ── Stage 7: Deploy ──
        if "deploy" in stages_to_run:
            stage_deploy(strict=strict)

    except PipelineAssertionError as e:
        elapsed = time.time() - start
        print(f"\n{'='*60}")
        print(f"  PIPELINE FAILED at stage '{e.stage}' after {elapsed:.1f}s")
        print(f"{'='*60}")
        print(str(e))
        sys.exit(1)

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"  PIPELINE COMPLETE")
    print(f"  Stages run: {' → '.join(stages_to_run)}")
    print(f"  Time: {elapsed:.1f}s")
    print(f"  Golden output: {OUTPUT_DIR / 'players_golden.json'}")
    print(f"  Canonical (compat): {OUTPUT_DIR / 'players_canonical.json'}")
    print(f"  Supabase seed: {OUTPUT_DIR / 'supabase_seed/'}")
    print(f"{'='*60}")


if __name__ == "__main__":
    args = sys.argv[1:]

    with_enrichment = "--with-enrichment" in args or "--all" in args
    with_verify = "--with-verify" in args or "--all" in args
    strict = "--lenient" not in args

    from_stage = None
    if "--from" in args:
        idx = args.index("--from")
        if idx + 1 < len(args):
            from_stage = args[idx + 1]

    run_full_pipeline(
        with_enrichment=with_enrichment,
        with_verify=with_verify,
        from_stage=from_stage,
        strict=strict,
    )
