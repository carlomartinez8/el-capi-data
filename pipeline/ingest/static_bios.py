"""
Parse hand-curated player-bios.ts and bios/*.ts files from la-copa-mundo.

Extracts height, foot, intlCaps, intlGoals, marketValue, birthDate,
birthPlace, previousClubs, achievements — keyed by player slug.
"""

import re
from pathlib import Path
from pipeline.config import STATIC_BIOS_PATH, BIOS_DIR


def _parse_value(raw: str) -> str | int | float | bool | list | None:
    """Convert a TS literal to a Python value."""
    raw = raw.strip().rstrip(",")
    if raw in ("true", "True"):
        return True
    if raw in ("false", "False"):
        return False
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1]
    if raw.startswith("'") and raw.endswith("'"):
        return raw[1:-1]
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


def _parse_array(text: str) -> list[str]:
    """Parse a TS array literal like ["a", "b"]."""
    items = re.findall(r'"([^"]*)"', text)
    return items


def _parse_bio_object(block: str) -> dict:
    """Extract key-value pairs from a single bio object block."""
    result: dict = {}

    for key in ("height", "foot", "birthDate", "birthPlace", "marketValue",
                 "bio_en", "bio_es"):
        m = re.search(rf'{key}\s*:\s*"((?:[^"\\]|\\.)*)"', block)
        if m:
            result[key] = m.group(1)

    for key in ("intlCaps", "intlGoals"):
        m = re.search(rf'{key}\s*:\s*(\d+)', block)
        if m:
            result[key] = int(m.group(1))

    for key in ("previousClubs", "achievements"):
        m = re.search(rf'{key}\s*:\s*\[(.*?)\]', block, re.DOTALL)
        if m:
            result[key] = _parse_array(m.group(1))

    return result


def _parse_ts_file(path: Path) -> dict[str, dict]:
    """Parse a TS file and return {slug: bio_dict} pairs."""
    if not path.exists():
        print(f"  WARNING: {path} not found, skipping")
        return {}

    content = path.read_text(encoding="utf-8")
    content = re.sub(r'//[^\n]*', '', content)

    entries: dict[str, dict] = {}

    pattern = re.compile(r'"([\w-]+)"\s*:\s*\{', re.MULTILINE)
    for m in pattern.finditer(content):
        slug = m.group(1)
        start = m.end()

        depth = 1
        i = start
        while i < len(content) and depth > 0:
            if content[i] == '{':
                depth += 1
            elif content[i] == '}':
                depth -= 1
            i += 1

        block = content[start:i - 1]
        bio = _parse_bio_object(block)
        if bio:
            entries[slug] = bio

    return entries


def load_static_bios() -> dict[str, dict]:
    """
    Load all static bios (notable + group files).

    Returns a dict keyed by player slug with fields:
      height, foot, intlCaps, intlGoals, marketValue,
      birthDate, birthPlace, previousClubs, achievements,
      bio_en, bio_es
    """
    all_bios: dict[str, dict] = {}

    if BIOS_DIR.exists():
        for ts_file in sorted(BIOS_DIR.glob("*.ts")):
            parsed = _parse_ts_file(ts_file)
            all_bios.update(parsed)
            print(f"  {ts_file.name}: {len(parsed)} bios")
    else:
        print(f"  WARNING: bios directory {BIOS_DIR} not found")

    notable = _parse_ts_file(STATIC_BIOS_PATH)
    print(f"  player-bios.ts (notable): {len(notable)} bios")
    all_bios.update(notable)

    print(f"  Total static bios loaded: {len(all_bios)}")
    return all_bios


if __name__ == "__main__":
    bios = load_static_bios()
    for slug, bio in list(bios.items())[:5]:
        print(f"\n{slug}:")
        for k, v in bio.items():
            if isinstance(v, str) and len(v) > 80:
                print(f"  {k}: {v[:80]}...")
            else:
                print(f"  {k}: {v}")
