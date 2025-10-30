#!/bin/bash
set -e

# Railway PostgreSQL environment variables
# Railway provides: PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE
# Or can use DATABASE_URL

# Parse DATABASE_URL if provided (format: postgresql://user:pass@host:port/dbname)
if [ -n "$DATABASE_URL" ]; then
    # Extract components from DATABASE_URL
    DB_USER=$(echo $DATABASE_URL | sed -n 's/.*:\/\/\([^:]*\):.*/\1/p')
    DB_PASSWORD=$(echo $DATABASE_URL | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p')
    DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
    DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    DB_NAME=$(echo $DATABASE_URL | sed -n 's/.*\/\([^?]*\).*/\1/p')
else
    # Use individual environment variables
    DB_USER="${PGUSER:-odoo}"
    DB_PASSWORD="${PGPASSWORD:-odoo}"
    DB_HOST="${PGHOST:-db}"
    DB_PORT="${PGPORT:-5432}"
    DB_NAME="${PGDATABASE:-postgres}"
fi

# Odoo configuration
ODOO_DB_NAME="${DB_NAME:-odoo_production}"
ADMIN_PASSWORD="${ADMIN_PASSWD:-admin}"
HTTP_PORT="${HTTP_PORT:-8069}"
LONGPOLLING_PORT="${LONGPOLLING_PORT:-8072}"
WORKERS="${WORKERS:-2}"
MAX_CRON_THREADS="${MAX_CRON_THREADS:-2}"
LIMIT_TIME_CPU="${LIMIT_TIME_CPU:-600}"
LIMIT_TIME_REAL="${LIMIT_TIME_REAL:-1200}"

# Addons path - custom modules only (no enterprise in Railway)
ADDONS_PATH="/usr/lib/python3/dist-packages/odoo/addons,/mnt/custom-addons"

echo "🚀 Starting Odoo on Railway..."
echo "📊 Database: ${DB_HOST}:${DB_PORT}/${ODOO_DB_NAME}"
echo "📦 Custom Addons Path: /mnt/custom-addons"

# Start Odoo with environment-based configuration
exec odoo \
    --addons-path="${ADDONS_PATH}" \
    --db_host="${DB_HOST}" \
    --db_port="${DB_PORT}" \
    --db_user="${DB_USER}" \
    --db_password="${DB_PASSWORD}" \
    --database="${ODOO_DB_NAME}" \
    --db-filter="^${ODOO_DB_NAME}\$" \
    --http-port="${HTTP_PORT}" \
    --longpolling-port="${LONGPOLLING_PORT}" \
    --proxy-mode \
    --workers="${WORKERS}" \
    --max-cron-threads="${MAX_CRON_THREADS}" \
    --limit-time-cpu="${LIMIT_TIME_CPU}" \
    --limit-time-real="${LIMIT_TIME_REAL}" \
    --without-demo=all \
    --log-level=info \
    --admin-passwd="${ADMIN_PASSWORD}" \
    --server-wide-modules=base,web,queue_job \
    "$@"
