#!/usr/bin/env python3

import json
import logging
from glob import glob

_logger = logging.getLogger(__name__)

quality_report_files = glob('custom/addons/*/ql.json')
existing_results = []
_logger.info(quality_report_files)

for file in quality_report_files:
    _logger.info('Processing %s', file)
    with open(file, encoding="utf-8") as f:
        data = json.load(f)
    folder = file.split("/")[1]
    for record in data:
        record["location"]["path"] = f'{folder}/{record["location"]["path"]}'

    existing_results += data

with open('./codeclimate.json', 'w', encoding="utf-8") as json_file:
    json.dump(existing_results, json_file)
