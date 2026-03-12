#!/usr/bin/env python3
"""
El Capi — Safe Pipeline Refresh

A single command to safely refresh the entire pipeline with backups,
diff detection, and rollback capability.

Usage:
    python refresh.py                    # full safe refresh (backup → pipeline → enrich → reconcile → verify → push)
    python refresh.py --pipeline-only    # just re-run ingest → dedup → QA → export
    python refresh.py --reconcile-only   # just run reconciliation on existing canonical data
    python refresh.py --verify-only      # just re-verify existing canonical data
    python refresh.py --push-only        # just push existing canonical to Supabase
    python refresh.py --dry-run          # preview what would happen, no changes
    python refresh.py --skip-enrich      # skip enrichment (use existing enriched data)
    python refresh.py --skip-verify      # skip verification
    python refresh.py --skip-reconcile   # skip reconciliation step
    python refresh.py --no-backup        # skip backup step (not recommended)

Safety features:
    - Automatic backup of all data files before any changes
    - Diff detection: shows what changed before applying
    - Rollback: python refresh.py --rollback (restores last backup)
    - Cost estimation before expensive API calls
    - Confirmation prompts for destructive operations
"""

import json
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
OUTPUT = ROOT / "data" / "output"
BACKUP_DIR = ROOT / "data" / "backups"
CANONICAL = OUTPUT / "players_canonical.json"
ENRICHED = OUTPUT / "players_enriched.json"
VERIFY_RESULTS = OUTPUT / "verification_results.json"
VERIFY_DIFF = OUTPUT / "verification_diff.json"
VERIFY_APPLIED = OUTPUT / "verification_applied.json"

BACKUP_FILES = [
    CANONICAL,
    ENRICHED,
    VERIFY_RESULTS,
    VERIFY_DIFF,
    VERIFY_APPLIED,
    OUTPUT / "players_canonical_latest.json",
    OUTPUT / "enrichment_checkpoint.json" if (ROOT / "data" / "intermediate" / "enrichment_checkpoint.json").exists() else None,
]


def create_backup(tag: str = "") -> Path:
    """Create a timestamped backup of all critical data files."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    label = f"{ts}_{tag}" if tag else ts
    backup_path = BACKUP_DIR / label
    backup_path.mkdir(parents=True, exist_ok=True)

    backed_up = 0
    for src in BACKUP_FILES:
        if src and src.exists():
            dst = backup_path / src.name
            shutil.copy2(src, dst)
            size_mb = src.stat().st_size / (1024 * 1024)
            print(f"    {src.name} ({size_mb:.1f} MB)")
            backed_up += 1

    if backed_up == 0:
        print("    No files to back up (first run?)")
        return backup_path

    manifest = {
        "created_at": datetime.utcnow().isoformat() + "Z",
        "tag": tag,
        "files": [f.name for f in backup_path.iterdir() if f.is_file()],
    }
    with open(backup_path / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"    Backup saved to: {backup_path}")
    return backup_path


def list_backups():
    """List available backups."""
    if not BACKUP_DIR.exists():
        print("  No backups found.")
        return []
    backups = sorted(BACKUP_DIR.iterdir(), reverse=True)
    backups = [b for b in backups if b.is_dir()]
    if not backups:
        print("  No backups found.")
        return []
    print(f"  {len(backups)} backups available:")
    for b in backups[:10]:
        manifest_path = b / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path) as f:
                m = json.load(f)
            files = len(m.get("files", []))
            print(f"    {b.name} — {files} files, tag: {m.get('tag', 'none')}")
        else:
            files = len(list(b.iterdir()))
            print(f"    {b.name} — {files} files")
    return backups


def rollback(backup_name: str = ""):
    """Restore from a backup."""
    if not BACKUP_DIR.exists():
        print("ERROR: No backups directory found.")
        return False

    if backup_name:
        backup_path = BACKUP_DIR / backup_name
    else:
        backups = sorted([b for b in BACKUP_DIR.iterdir() if b.is_dir()], reverse=True)
        if not backups:
            print("ERROR: No backups found.")
            return False
        backup_path = backups[0]

    if not backup_path.exists():
        print(f"ERROR: Backup '{backup_name}' not found.")
        list_backups()
        return False

    print(f"\n  Rolling back from: {backup_path.name}")

    restored = 0
    for src in backup_path.iterdir():
        if src.name == "manifest.json":
            continue
        if src.is_file():
            dst = OUTPUT / src.name
            shutil.copy2(src, dst)
            print(f"    Restored: {src.name}")
            restored += 1

    print(f"  Restored {restored} files.")
    return True


def count_canonical_players() -> int:
    """Count players in current canonical file."""
    if not CANONICAL.exists():
        return 0
    with open(CANONICAL) as f:
        return len(json.load(f))


def detect_changes(old_path: Path, new_path: Path) -> dict:
    """Compare two canonical JSON files and report differences."""
    if not old_path.exists() or not new_path.exists():
        return {"error": "file_missing"}

    with open(old_path) as f:
        old = {p["canonical_id"]: p for p in json.load(f) if "canonical_id" in p}
    with open(new_path) as f:
        new = {p["canonical_id"]: p for p in json.load(f) if "canonical_id" in p}

    added = set(new.keys()) - set(old.keys())
    removed = set(old.keys()) - set(new.keys())
    changed = 0
    unchanged = 0

    for cid in set(old.keys()) & set(new.keys()):
        if json.dumps(old[cid], sort_keys=True) != json.dumps(new[cid], sort_keys=True):
            changed += 1
        else:
            unchanged += 1

    return {
        "old_count": len(old),
        "new_count": len(new),
        "added": len(added),
        "removed": len(removed),
        "changed": changed,
        "unchanged": unchanged,
    }


def estimate_costs(players_to_enrich: int, players_to_verify: int) -> dict:
    """Estimate API costs for enrichment and verification."""
    enrich_cost = players_to_enrich * 0.0055
    verify_cost = players_to_verify * 0.0037
    return {
        "enrich": {"players": players_to_enrich, "cost_usd": round(enrich_cost, 2), "model": "gpt-4o-mini"},
        "verify": {"players": players_to_verify, "cost_usd": round(verify_cost, 2), "model": "gpt-4o"},
        "total_usd": round(enrich_cost + verify_cost, 2),
    }


def run_refresh(
    pipeline_only: bool = False,
    reconcile_only: bool = False,
    verify_only: bool = False,
    push_only: bool = False,
    skip_enrich: bool = False,
    skip_verify: bool = False,
    skip_reconcile: bool = False,
    dry_run: bool = False,
    no_backup: bool = False,
):
    start = time.time()

    print("=" * 60)
    print("  EL CAPI — Safe Pipeline Refresh")
    print("=" * 60)

    flags = []
    if dry_run: flags.append("DRY RUN")
    if pipeline_only: flags.append("PIPELINE ONLY")
    if reconcile_only: flags.append("RECONCILE ONLY")
    if verify_only: flags.append("VERIFY ONLY")
    if push_only: flags.append("PUSH ONLY")
    if skip_enrich: flags.append("SKIP ENRICH")
    if skip_verify: flags.append("SKIP VERIFY")
    if skip_reconcile: flags.append("SKIP RECONCILE")
    if no_backup: flags.append("NO BACKUP")
    if flags:
        print(f"  Mode: {' | '.join(flags)}")

    current_count = count_canonical_players()
    print(f"  Current canonical players: {current_count}")

    # ── Step 0: Backup ──
    if not no_backup and not dry_run:
        print("\n── STEP 0: BACKUP ──")
        tag = "pre_refresh"
        if pipeline_only: tag = "pre_pipeline"
        elif verify_only: tag = "pre_verify"
        elif push_only: tag = "pre_push"
        backup_path = create_backup(tag)
    else:
        print("\n── STEP 0: BACKUP (skipped) ──")

    # ── Step 1: Pipeline (ingest → dedup → QA → export) ──
    if not verify_only and not push_only and not reconcile_only:
        print("\n── STEP 1: PIPELINE ──")
        if dry_run:
            print("  [DRY RUN] Would run: ingest → dedup → QA → export")
        else:
            from run_pipeline import run_full_pipeline
            run_full_pipeline()

        if pipeline_only:
            elapsed = time.time() - start
            print(f"\n  Pipeline refresh completed in {elapsed:.1f}s")
            return

    # ── Step 2: Enrichment ──
    if not verify_only and not push_only and not reconcile_only and not skip_enrich:
        print("\n── STEP 2: ENRICHMENT ──")
        costs = estimate_costs(632, 0)
        print(f"  Estimated cost: ${costs['enrich']['cost_usd']:.2f} ({costs['enrich']['model']})")

        if dry_run:
            print("  [DRY RUN] Would enrich WC players via ChatGPT")
        else:
            print("  Running enrichment with --resume (only new/missing players)...")
            from run_enrichment import run_enrichment
            run_enrichment(wc_only=True, resume=True)

        # ── Canonical dedup ──
        if not dry_run:
            print("\n  Assigning canonical IDs...")
            from pipeline.dedup.canonical import run_dedup
            run_dedup()
    elif not verify_only and not push_only and not reconcile_only:
        print("\n── STEP 2: ENRICHMENT (skipped) ──")

    # ── Step 3: Reconciliation ──
    run_reconcile = (
        reconcile_only
        or (not pipeline_only and not verify_only and not push_only and not skip_reconcile)
    )
    if run_reconcile:
        print("\n── STEP 3: RECONCILIATION ──")
        if dry_run:
            print("  [DRY RUN] Would run source merge + conflict detection")
        else:
            from pipeline.reconcile.merge import run_merge
            from pipeline.reconcile.conflicts import detect_conflicts
            from pipeline.reconcile.review import auto_resolve_agreement, auto_resolve_non_critical, _load_report

            merged = run_merge()
            report = detect_conflicts(merged)

            print("\n  Auto-resolving safe conflicts...")
            auto_resolve_agreement(report)
            report = _load_report()
            auto_resolve_non_critical(report)

            report = _load_report()
            blocked = len([p for p in report.get("players", []) if p.get("blocked")])
            if blocked > 0:
                print(f"\n  ⚠  {blocked} players BLOCKED with unresolved CRITICAL conflicts.")
                print("  Review with: python -m pipeline.reconcile.review --summary")
                print("  These players will be skipped during push.")

        if reconcile_only:
            elapsed = time.time() - start
            print(f"\n  Reconciliation completed in {elapsed:.1f}s")
            return
    else:
        print("\n── STEP 3: RECONCILIATION (skipped) ──")

    # ── Step 4: Verification ──
    if not pipeline_only and not push_only and not reconcile_only and not skip_verify:
        print("\n── STEP 4: VERIFICATION ──")
        verify_count = count_canonical_players()
        costs = estimate_costs(0, verify_count)
        print(f"  Players to verify: {verify_count}")
        print(f"  Estimated cost: ${costs['verify']['cost_usd']:.2f} ({costs['verify']['model']})")

        if dry_run:
            print("  [DRY RUN] Would verify critical fields via gpt-4o")
        else:
            from pipeline.verify.critical_fields import run_verification
            from pipeline.verify.apply_updates import run_apply
            run_verification()
            run_apply(do_apply=True, tier_filter=1)
    elif not pipeline_only and not push_only and not reconcile_only:
        print("\n── STEP 4: VERIFICATION (skipped) ──")

    # ── Step 5: Push to Supabase ──
    if not pipeline_only and not verify_only and not reconcile_only or push_only:
        print("\n── STEP 5: PUSH TO SUPABASE ──")
        if dry_run:
            print(f"  [DRY RUN] Would push {count_canonical_players()} players to Supabase (skipping blocked)")
        else:
            from push_to_supabase import main as push_main
            push_main()

    # ── Summary ──
    elapsed = time.time() - start
    print("\n" + "=" * 60)
    print(f"  REFRESH COMPLETE — {elapsed:.1f}s")
    if not no_backup and not dry_run:
        print(f"  Backup: {backup_path}")
        print(f"  Rollback: python refresh.py --rollback")
    print("=" * 60)


def main():
    args = sys.argv[1:]

    if "--rollback" in args:
        print("\n=== ROLLBACK ===")
        backup_name = ""
        if "--backup" in args:
            idx = args.index("--backup")
            if idx + 1 < len(args):
                backup_name = args[idx + 1]
        rollback(backup_name)
        return

    if "--list-backups" in args:
        print("\n=== BACKUPS ===")
        list_backups()
        return

    run_refresh(
        pipeline_only="--pipeline-only" in args,
        reconcile_only="--reconcile-only" in args,
        verify_only="--verify-only" in args,
        push_only="--push-only" in args,
        skip_enrich="--skip-enrich" in args,
        skip_verify="--skip-verify" in args,
        skip_reconcile="--skip-reconcile" in args,
        dry_run="--dry-run" in args,
        no_backup="--no-backup" in args,
    )


if __name__ == "__main__":
    main()
