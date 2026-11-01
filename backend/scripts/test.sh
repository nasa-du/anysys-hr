#!/usr/bin/env bash

set -e
set -x

bash scripts/create-test-db.sh
FASTAPI_ENV=development coverage run -m pytest tests/
coverage report
coverage html --title "${@-coverage}"
