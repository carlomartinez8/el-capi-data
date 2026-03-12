#!/usr/bin/env bash
# Load player warehouse seed files into Supabase via psql.
# Tables must already be empty (run TRUNCATE in dashboard first if needed).
#
# Usage:
#   export SUPABASE_DATABASE_URI="postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres"
#   ./scripts/load-player-seed.sh
#
# Get the URI from: Supabase Dashboard → Settings → Database → Connection string (URI)

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SEED_DIR="$ROOT_DIR/data/output/supabase_seed"

if [[ -z "${SUPABASE_DATABASE_URI}" ]]; then
  echo "Error: SUPABASE_DATABASE_URI is not set."
  echo "Get it from: Supabase Dashboard → Settings → Database → Connection string (URI)"
  echo "Then run: export SUPABASE_DATABASE_URI=\"postgresql://...\""
  exit 1
fi

if ! command -v psql &>/dev/null; then
  echo "Error: psql not found. On Mac run: brew install libpq"
  exit 1
fi

for f in players player_career player_tournament player_aliases; do
  path="$SEED_DIR/${f}.sql"
  if [[ ! -f "$path" ]]; then
    echo "Error: $path not found"
    exit 1
  fi
  echo "Loading $f..."
  psql "$SUPABASE_DATABASE_URI" -v ON_ERROR_STOP=1 -f "$path"
  echo "Done: $f"
done

echo "All four seed files loaded."
