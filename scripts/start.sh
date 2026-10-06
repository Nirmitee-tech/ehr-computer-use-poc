#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if [ "$(uname -s)" = "Darwin" ]; then
  if [ ! -x build/desktop-bridge ]; then ./scripts/build-native.sh; fi
  open build/OpenClerkClinic.app
else
  python3 -m openclerk.cli demo &
fi
exec python3 -m openclerk.cli serve "$@"
