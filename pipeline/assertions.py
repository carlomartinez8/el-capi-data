"""
Pipeline Assertion Gates — stage contracts that block progression on failure.

Each assertion returns (passed: bool, message: str).
Gate functions collect assertions and raise PipelineAssertionError if any fail.
"""

import json
from collections import Counter
from pathlib import Path


class PipelineAssertionError(Exception):
    """Raised when a pipeline stage fails its assertion gate."""

    def __init__(self, stage: str, failures: list[str]):
        self.stage = stage
        self.failures = failures
        msg = f"\n{'='*60}\n  PIPELINE HALTED — Stage '{stage}' failed assertions\n{'='*60}\n"
        for i, f in enumerate(failures, 1):
            msg += f"  [{i}] {f}\n"
        super().__init__(msg)


# ─── Individual Assertions ───────────────────────────────────────────


def assert_wc_team_sizes(players: list[dict], min_size: int = 23, max_size: int = 30) -> tuple[bool, str]:
    """Every WC team should have 23-30 players."""
    teams = Counter(p.get("wc_team_code", "") for p in players if p.get("wc_team_code") or p.get("in_wc_squad"))
    violations = []
    for team, count in sorted(teams.items()):
        if count < min_size:
            violations.append(f"{team}: {count} players (below minimum {min_size})")
        elif count > max_size:
            violations.append(f"{team}: {count} players (above maximum {max_size})")
    if violations:
        return False, f"Team size violations: {'; '.join(violations)}"
    return True, f"All {len(teams)} teams have {min_size}-{max_size} players"


def assert_no_cross_team_duplicates(players: list[dict]) -> tuple[bool, str]:
    """No player should appear in two WC teams."""
    seen: dict[str, str] = {}  # name → team
    dupes = []
    for p in players:
        name = p.get("name", "").lower().strip()
        team = p.get("wc_team_code", "")
        if not name or not team:
            continue
        key = name
        if key in seen and seen[key] != team:
            dupes.append(f"'{p.get('name')}' in {seen[key]} AND {team}")
        seen[key] = team
    if dupes:
        return False, f"Cross-team duplicates: {'; '.join(dupes[:5])}"
    return True, "No cross-team duplicates found"


def assert_field_coverage(
    players: list[dict],
    field_path: str,
    min_pct: float = 95.0,
    label: str | None = None,
) -> tuple[bool, str]:
    """Assert that a given field has at least min_pct coverage across players."""
    label = label or field_path
    total = len(players)
    if total == 0:
        return False, f"No players to check for {label}"

    present = 0
    for p in players:
        val = p
        for key in field_path.split("."):
            if isinstance(val, dict):
                val = val.get(key)
            else:
                val = None
                break
        if val is not None and val != "" and val != "null":
            present += 1

    pct = (present / total) * 100
    if pct < min_pct:
        return False, f"{label}: {present}/{total} ({pct:.1f}%) — below threshold {min_pct}%"
    return True, f"{label}: {present}/{total} ({pct:.1f}%)"


def assert_merged_field_coverage(
    merged_players: list[dict],
    field_name: str,
    min_pct: float = 95.0,
) -> tuple[bool, str]:
    """Assert coverage for a field in the merged format ({fields: {field_name: {value, source}}})."""
    total = len(merged_players)
    if total == 0:
        return False, f"No players to check for {field_name}"

    present = 0
    for p in merged_players:
        field_data = p.get("fields", {}).get(field_name, {})
        if field_data.get("value") is not None:
            present += 1

    pct = (present / total) * 100
    if pct < min_pct:
        return False, f"merged.{field_name}: {present}/{total} ({pct:.1f}%) — below threshold {min_pct}%"
    return True, f"merged.{field_name}: {present}/{total} ({pct:.1f}%)"


def assert_canonical_ids_unique(players: list[dict]) -> tuple[bool, str]:
    """All canonical IDs must be unique and non-empty."""
    ids = [p.get("canonical_id") for p in players]
    empty = sum(1 for i in ids if not i)
    if empty:
        return False, f"{empty} players missing canonical_id"
    dupes = len(ids) - len(set(ids))
    if dupes:
        return False, f"{dupes} duplicate canonical_ids found"
    return True, f"All {len(ids)} canonical IDs are unique"


def assert_min_player_count(players: list[dict], expected: int, label: str = "players") -> tuple[bool, str]:
    """Assert minimum player count."""
    if len(players) < expected:
        return False, f"Expected at least {expected} {label}, got {len(players)}"
    return True, f"{len(players)} {label} (expected >= {expected})"


# ─── Gate Functions ──────────────────────────────────────────────────


def gate(stage: str, assertions: list[tuple[bool, str]], strict: bool = True):
    """
    Run all assertions for a stage. Print results and optionally halt on failure.

    Args:
        stage: name of the pipeline stage
        assertions: list of (passed, message) tuples
        strict: if True, raise PipelineAssertionError on any failure
    """
    print(f"\n  {'─'*50}")
    print(f"  ASSERTION GATE: {stage}")
    print(f"  {'─'*50}")

    failures = []
    for passed, msg in assertions:
        icon = "  ✓" if passed else "  ✗"
        print(f"  {icon} {msg}")
        if not passed:
            failures.append(msg)

    if failures:
        print(f"\n  ⚠️  {len(failures)} assertion(s) FAILED for stage '{stage}'")
        if strict:
            raise PipelineAssertionError(stage, failures)
        else:
            print(f"  (non-strict mode — continuing despite failures)")
    else:
        print(f"  ✓ All assertions passed for '{stage}'")

    return len(failures) == 0
