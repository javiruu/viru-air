#!/bin/sh
set -e

mkdir -p /app/.next
if [ ! -f /app/.next/fallback-build-manifest.json ]; then
  printf '{"pages":{},"app":{},"rootMainFiles":[]}' > /app/.next/fallback-build-manifest.json
fi

exec npm run start
