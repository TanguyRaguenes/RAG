#!/bin/sh
set -eu

curl -fsS -X POST http://localhost:8001/delete_collection
printf '\n'

curl -fsS -X POST http://localhost:8002/ingest/bulk
