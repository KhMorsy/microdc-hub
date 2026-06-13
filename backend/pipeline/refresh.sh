#!/bin/sh
# scheduled refresh: re-bake nodes.geojson (re-fetches feeds whose 30-min cache has expired),
# then nudge the running backend to reload. driven by the launchd job com.microdc.refresh.
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR" || exit 1
echo "--- refresh $(date '+%Y-%m-%d %H:%M:%S') ---"
/usr/bin/python3 build_geojson.py
/usr/bin/curl -s http://localhost:8000/reload >/dev/null 2>&1 || true
