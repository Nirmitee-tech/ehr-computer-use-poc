#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
docker build -f tests/Dockerfile.x11 -t openclerk-x11-test .
docker run --rm --network none -v "$PWD/docs/evidence:/evidence" openclerk-x11-test
