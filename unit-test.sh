#!/usr/bin/env bash

change_list=$(git diff --name-only HEAD HEAD~1 | xargs dirname | grep -v '\.' | cut -d '/' -f 1 | sort | uniq | paste -sd ",")

if [[ -z $change_list ]]
then
  echo "No module changes, skip testing"
  exit 0
fi

TEST_MODULES=$change_list
if [ -z "$1" ]
  then
    TEST_TAGS=$TEST_MODULES
  else
    TEST_TAGS=$1
fi
source $(pwd)/odoo.env
addons="${ODOO_PATH}/addons"

if [[ ! -z $ENTERPRISE_ADDONS_PATH ]]
then
  addons="${addons},$ENTERPRISE_ADDONS_PATH"
fi

addons="${addons},$(pwd)"

${ODOO_VENV}/bin/python3 ${ODOO_PATH}/odoo-bin --db_host localhost -r test_user -w zxc741 --http-port 8999 --addons-path "$addons" -d "tests_12345678" --stop-after-init --init "$TEST_MODULES" -u "$TEST_MODULES" --test-enable --test-tags "$TEST_TAGS"
