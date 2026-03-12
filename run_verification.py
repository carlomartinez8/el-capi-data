#!/usr/bin/env python3
"""
El Capi — Daily Critical Fields Verification Runner

12 critical fields across Capi's 3-tier priority system.
gpt-4o (not mini), 8 threads, ~$1.90 for all 632 players, ~5-8 min.

Usage:
    python run_verification.py                          # verify all 632 players
    python run_verification.py --player "Lionel Messi"  # single player test
    python run_verification.py --batch 10               # test on 10 players
    python run_verification.py --dry-run                # preview what would happen
    python run_verification.py --apply                  # verify + auto-apply ALL changes
    python run_verification.py --apply --tier 1         # verify + auto-apply IMPERDONABLE only

After running without --apply, review the diff:
    python -m pipeline.verify.apply_updates             # preview all changes
    python -m pipeline.verify.apply_updates --tier 1    # preview imperdonable only
    python -m pipeline.verify.apply_updates --apply     # commit all changes

Then regenerate seed SQL:
    python -m pipeline.sync.to_supabase                 # regenerate SQL from updated canonical
"""

import sys
from pipeline.verify.critical_fields import run_verification
from pipeline.verify.apply_updates import run_apply


def main():
    args = sys.argv[1:]

    single = None
    batch = 0
    dry = "--dry-run" in args
    auto_apply = "--apply" in args
    retry = "--retry-failed" in args

    if "--player" in args:
        idx = args.index("--player")
        if idx + 1 < len(args):
            single = args[idx + 1]

    if "--batch" in args:
        idx = args.index("--batch")
        if idx + 1 < len(args):
            batch = int(args[idx + 1])

    tier = None
    if "--tier" in args:
        idx = args.index("--tier")
        if idx + 1 < len(args):
            tier = int(args[idx + 1])

    # Step 1: Verify
    result = run_verification(
        batch_size=batch,
        single_player=single,
        dry_run=dry,
        retry_failed=retry,
    )

    if dry or result is None:
        return

    results, diffs, log = result

    # Step 2: Auto-apply if requested
    if auto_apply and diffs:
        print("\n" + "=" * 60)
        if tier:
            print(f"  AUTO-APPLYING Tier {tier} changes only...")
        else:
            print("  AUTO-APPLYING verified changes...")
        print("=" * 60)
        run_apply(do_apply=True, tier_filter=tier)
    elif diffs:
        t1 = sum(1 for d in diffs for c in d["changes"] if c.get("tier") == 1)
        print(f"\n  💡 {len(diffs)} players have changes.")
        if t1 > 0:
            print(f"  🔴 {t1} are IMPERDONABLE (tier 1).")
        print("  Review with:  python -m pipeline.verify.apply_updates")
        print("  Apply with:   python -m pipeline.verify.apply_updates --apply")
        print("  T1 only:      python -m pipeline.verify.apply_updates --tier 1 --apply")


if __name__ == "__main__":
    main()
