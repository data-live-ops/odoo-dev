#!/bin/bash

source odoo.env

change_list=$(git diff --name-only HEAD HEAD~1 | xargs dirname | grep -v '\.' | cut -d '/' -f 1 | sort | uniq)

if [[ -z $change_list ]]
then
  echo "No module changes, skip deploying"
  exit 0
fi

cd $CUSTOM_ADDONS_PATH

git pull

if [[ $? -eq 0 ]]
then
    echo "Restarting . . ."
    sudo /usr/bin/systemctl restart $ODOO_SERVICE
    sleep 5
    sudo /usr/bin/systemctl status $ODOO_SERVICE
    
    ## Upgrade Module
    # ${ODOO_VENV}/bin/python3 ${ODOO_PATH}/odoo-bin -c /opt/odoo/config/odoo-server.conf -d "database_name" --stop-after-init -u "$change_list"
fi
