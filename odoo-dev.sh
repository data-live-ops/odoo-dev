#!/bin/bash
# Odoo Development Wrapper Script
# Usage: ./odoo-dev.sh [odoo-command-options]

# Configuration
ODOO_PATH="$HOME/Documents/engineering/odoo-18.0+e.20251009"
CUSTOM_ADDONS="$HOME/Documents/engineering/colearn-dev"
DB_NAME="${ODOO_DB:-testdb}"

# Addons path (include both Odoo addons and custom modules)
ADDONS_PATH="${ODOO_PATH}/odoo/addons,${CUSTOM_ADDONS}"

# Run Odoo
echo "🚀 Starting Odoo Development Environment..."
echo "📁 Odoo Path: ${ODOO_PATH}"
echo "📦 Custom Addons: ${CUSTOM_ADDONS}"
echo "💾 Database: ${DB_NAME}"
echo ""

cd "${ODOO_PATH}" || exit 1

python3 -m odoo \
  --addons-path="${ADDONS_PATH}" \
  --database="${DB_NAME}" \
  --dev=all \
  --geoip-db='' \
  "$@"
