#!/bin/sh
rm -rf dev.db migrations
touch dev.db
docker-compose run --rm manage db init
docker-compose run --rm manage db migrate
docker-compose run --rm manage db upgrade
#python3 shell_scripts/populate_db.py