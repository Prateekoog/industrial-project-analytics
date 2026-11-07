#!/usr/bin/env bash
# Build the PostgreSQL database end to end and save the output of every analysis query.
# Run from the project root:  bash database/build_database.sh
# Requires: PostgreSQL running locally, and the processed CSVs (python run_pipeline.py).
set -euo pipefail
DB="${PGDATABASE_NAME:-projectco_analytics}"

psql -d postgres -tc "SELECT 1 FROM pg_database WHERE datname = '$DB'" | grep -q 1 || createdb "$DB"
psql -v ON_ERROR_STOP=1 -q -d "$DB" -f database/schema.sql
psql -v ON_ERROR_STOP=1 -q -d "$DB" -f database/load_data.sql
psql -v ON_ERROR_STOP=1 -q -d "$DB" -f sql/00_views.sql

mkdir -p sql/results
psql -v ON_ERROR_STOP=1 -d "$DB" -f database/validation.sql | tee sql/results/validation.txt
for f in sql/0[1-8]_*.sql; do
  name=$(basename "$f" .sql)
  psql -v ON_ERROR_STOP=1 -d "$DB" -e -f "$f" > "sql/results/${name}.txt"
  echo "ran $f -> sql/results/${name}.txt"
done
if grep -q "FAIL" sql/results/validation.txt; then echo "VALIDATION FAILED"; exit 1; fi
echo "Database built and all SQL validation checks passed."
