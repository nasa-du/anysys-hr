#!/usr/bin/env bash

set -e
set -x

bash scripts/create-test-db.sh
# Performance smoke runs without coverage instrumentation in its own CI job,
# where the five-second budget is meaningful.
FASTAPI_ENV=development coverage run -m pytest tests/ -m "not performance"
coverage report
coverage html --title "${@-coverage}"
