"""
Export the canonical player list and QA reports to local files.
"""

import json
from datetime import datetime
import pandas as pd
from pipeline.config import OUTPUT_DIR, INTERMEDIATE_DIR


def export_canonical(df: pd.DataFrame, tag: str = "") -> str:
    """Export the canonical player list as JSON and CSV."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = f"_{tag}" if tag else ""

    json_path = OUTPUT_DIR / f"players_canonical{suffix}_{ts}.json"
    csv_path = OUTPUT_DIR / f"players_canonical{suffix}_{ts}.csv"

    latest_json = OUTPUT_DIR / "players_canonical_latest.json"
    latest_csv = OUTPUT_DIR / "players_canonical_latest.csv"

    records = df.where(df.notna(), None).to_dict(orient="records")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2, default=str)
    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2, default=str)

    df.to_csv(csv_path, index=False)
    df.to_csv(latest_csv, index=False)

    print(f"  Exported {len(df):,} players to:")
    print(f"    {json_path}")
    print(f"    {csv_path}")
    return str(json_path)


def export_review(df: pd.DataFrame) -> str | None:
    """Export the dedup review candidates for human QA."""
    if df.empty:
        print("  No review candidates to export.")
        return None

    path = INTERMEDIATE_DIR / "dedup_review.csv"
    df.to_csv(path, index=False)
    print(f"  Exported {len(df)} dedup review candidates to {path}")
    return str(path)


def export_qa_report(df: pd.DataFrame) -> str | None:
    """Export QA issues report."""
    if df.empty:
        print("  No QA issues — clean dataset!")
        return None

    path = INTERMEDIATE_DIR / "qa_report.csv"
    df.to_csv(path, index=False)
    print(f"  Exported {len(df)} QA issues to {path}")
    return str(path)


def export_summary(canonical_df: pd.DataFrame, review_df: pd.DataFrame, qa_df: pd.DataFrame) -> str:
    """Generate a human-readable summary of the pipeline run."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    total = len(canonical_df)
    wc_count = canonical_df["in_wc_squad"].sum() if "in_wc_squad" in canonical_df.columns else 0
    sources = canonical_df["source"].value_counts().to_dict() if "source" in canonical_df.columns else {}

    lines = [
        f"El Capi Data Pipeline — Run Summary",
        f"{'=' * 50}",
        f"Timestamp: {ts}",
        f"",
        f"PLAYERS",
        f"  Total canonical: {total:,}",
        f"  In WC 2026 squad: {int(wc_count)}",
        f"  By source: {sources}",
        f"",
        f"DEDUP",
        f"  Review candidates: {len(review_df)}",
        f"",
        f"QA",
    ]

    if not qa_df.empty:
        severity_counts = qa_df["severity"].value_counts().to_dict()
        for sev, count in severity_counts.items():
            lines.append(f"  {sev}: {count}")
    else:
        lines.append("  No issues found.")

    lines.append("")
    lines.append("FILES")
    lines.append(f"  Canonical: data/output/players_canonical_latest.json")
    lines.append(f"  QA Report: data/intermediate/qa_report.csv")
    lines.append(f"  Dedup Review: data/intermediate/dedup_review.csv")

    summary = "\n".join(lines)

    path = OUTPUT_DIR / "run_summary.txt"
    with open(path, "w") as f:
        f.write(summary)

    print(f"\n{'=' * 50}")
    print(summary)
    return str(path)
