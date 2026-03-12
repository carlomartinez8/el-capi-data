#!/usr/bin/env python3
"""
El Capi Data Pipeline — Main Orchestrator

Ingests player data from all sources, deduplicates, runs QA,
and exports a clean canonical player list.

Usage:
    python run_pipeline.py              # full pipeline
    python run_pipeline.py --ingest     # ingest only (no dedup/QA)
    python run_pipeline.py --dedup      # dedup + QA on previously ingested data
"""

import sys
import time
from pipeline.ingest.transfermarkt import load_players as load_tm_players
from pipeline.ingest.static_squads import load_static_squads
from pipeline.dedup.resolver import deduplicate
from pipeline.qa.checks import run_checks
from pipeline.export.local import (
    export_canonical,
    export_review,
    export_qa_report,
    export_summary,
)


def run_full_pipeline():
    start = time.time()

    print("=" * 60)
    print("  EL CAPI DATA PIPELINE")
    print("=" * 60)

    # ── Step 1: Ingest ──
    print("\n── STEP 1: INGEST ──")

    print("\n[Transfermarkt]")
    tm_df = load_tm_players()

    print("\n[Static WC Squads]")
    static_df = load_static_squads()

    # ── Step 2: Deduplicate ──
    print("\n── STEP 2: DEDUPLICATE ──")
    canonical_df, review_df = deduplicate(tm_df, static_df)

    # ── Step 3: QA ──
    print("\n── STEP 3: QA ──")
    qa_df = run_checks(canonical_df)

    # ── Step 4: Export ──
    print("\n── STEP 4: EXPORT ──")
    export_canonical(canonical_df)
    export_review(review_df)
    export_qa_report(qa_df)
    export_summary(canonical_df, review_df, qa_df)

    elapsed = time.time() - start
    print(f"\nPipeline completed in {elapsed:.1f}s")


def run_ingest_only():
    print("=" * 60)
    print("  EL CAPI DATA PIPELINE — Ingest Only")
    print("=" * 60)

    print("\n[Transfermarkt]")
    tm_df = load_tm_players()
    tm_df.to_csv("data/intermediate/tm_ingested.csv", index=False)
    print(f"  Saved {len(tm_df):,} TM players to data/intermediate/tm_ingested.csv")

    print("\n[Static WC Squads]")
    static_df = load_static_squads()
    static_df.to_csv("data/intermediate/static_ingested.csv", index=False)
    print(f"  Saved {len(static_df)} static squad players to data/intermediate/static_ingested.csv")


if __name__ == "__main__":
    if "--ingest" in sys.argv:
        run_ingest_only()
    elif "--dedup" in sys.argv:
        import pandas as pd
        print("Loading previously ingested data...")
        tm_df = pd.read_csv("data/intermediate/tm_ingested.csv")
        static_df = pd.read_csv("data/intermediate/static_ingested.csv")
        canonical_df, review_df = deduplicate(tm_df, static_df)
        qa_df = run_checks(canonical_df)
        export_canonical(canonical_df)
        export_review(review_df)
        export_qa_report(qa_df)
        export_summary(canonical_df, review_df, qa_df)
    else:
        run_full_pipeline()
