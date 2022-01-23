#!/bin/sh
rm -rf dev.db migrations
touch dev.db
docker-compose run --rm manage db init
docker-compose run --rm manage db migrate
docker-compose run --rm manage db upgrade
cp ../../Chicago/street_rename/chs_withdrawn_xrefs.csv ../../Chicago/street_rename/current_street_update.csv ../../Chicago/street_rename/chs_withdrawn_streets.csv .
python3 shell_scripts/populate_db.py