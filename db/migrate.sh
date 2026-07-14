#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# migrate.sh — minimal, dependency-free migration runner (psql only).
#
#   bash db/migrate.sh           apply any unapplied db/migrations/*.sql in order
#   bash db/migrate.sh --seed    apply migrations, then (re-)apply db/seed/*.sql
#
# Applied migrations are tracked in the schema_migrations table, so re-runs only
# apply new files. Seeds are written to be idempotent and are re-applied each time
# --seed is passed. Connection comes from DATABASE_URL (or POSTGRES_* parts) in .env.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MIGRATIONS_DIR="$REPO_ROOT/db/migrations"
SEED_DIR="$REPO_ROOT/db/seed"

# Load .env if present (simple KEY=VALUE lines).
if [[ -f "$REPO_ROOT/.env" ]]; then
    set -a; # shellcheck disable=SC1091
    source "$REPO_ROOT/.env"; set +a
fi

# Resolve a libpq connection string.
if [[ -n "${DATABASE_URL:-}" ]]; then
    CONN="$DATABASE_URL"
else
    CONN="postgresql://${POSTGRES_USER:-hapi}:${POSTGRES_PASSWORD:-hapi_dev_password}@${POSTGRES_HOST:-localhost}:${POSTGRES_PORT:-5432}/${POSTGRES_DB:-hapi}"
fi

PSQL=(psql "$CONN" -v ON_ERROR_STOP=1 --quiet --no-psqlrc)

SEED=false
[[ "${1:-}" == "--seed" ]] && SEED=true

# Log the target host/db only — never credentials. (CI logs on a public repo are
# world-readable, and GitHub secret-masking does not catch substrings of a secret.)
echo "▶ Connecting to: $(printf '%s' "$CONN" | sed -E 's#//[^@/]+@#//***@#; s#\?.*##')"
"${PSQL[@]}" -c "CREATE TABLE IF NOT EXISTS schema_migrations (
    filename   text PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now()
);"

# ── Migrations ────────────────────────────────────────────────────────────────
shopt -s nullglob
applied_any=false
for file in "$MIGRATIONS_DIR"/*.sql; do
    base="$(basename "$file")"
    already="$("${PSQL[@]}" -tA -c "SELECT 1 FROM schema_migrations WHERE filename = '$base';")"
    if [[ "$already" == "1" ]]; then
        echo "· skip   $base (already applied)"
        continue
    fi
    echo "✚ apply  $base"
    "${PSQL[@]}" --single-transaction -f "$file" \
        -c "INSERT INTO schema_migrations (filename) VALUES ('$base');"
    applied_any=true
done
$applied_any || echo "· migrations up to date"

# ── Seeds (idempotent; only with --seed) ──────────────────────────────────────
if $SEED; then
    for file in "$SEED_DIR"/*.sql; do
        echo "🌱 seed   $(basename "$file")"
        "${PSQL[@]}" --single-transaction -f "$file"
    done
fi

echo "✓ done"
