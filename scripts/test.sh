#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
python3 -m unittest tests.test_unit tests.test_planner_unit tests.test_platform_unit tests.test_driver_unit -v
python3 -m unittest tests.test_integration -v
if [ "${OPENCLERK_NATIVE_TESTS:-0}" = "1" ]; then
  python3 -m unittest tests.test_native_integration -v
fi
