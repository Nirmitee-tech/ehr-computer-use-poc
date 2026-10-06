#!/bin/sh
set -eu
Xvfb :99 -screen 0 1280x900x24 -nolisten tcp > /tmp/xvfb.log 2>&1 &
XVFB_PID=$!
trap 'kill "$XVFB_PID"' EXIT
sleep 1
openbox > /tmp/openbox.log 2>&1 &
sleep 1
python3 scripts/verify.py --x11 --output /evidence/validation-linux.json
