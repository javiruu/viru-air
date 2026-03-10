#!/bin/sh
set -e

mkdir -p /app/.next
if [ ! -f /app/.next/fallback-build-manifest.json ]; then
  printf '{"pages":{},"app":{},"rootMainFiles":[]}' > /app/.next/fallback-build-manifest.json
fi

# Temporary stable runtime: use Next dev server to avoid production manifest/runtime mismatch
exec npm run dev -- --hostname 0.0.0.0 --port 3000
