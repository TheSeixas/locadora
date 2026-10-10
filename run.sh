#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
if [ -z "${BOOTSTRAP_ADMIN_USERNAME:-}" ] || [ -z "${BOOTSTRAP_ADMIN_PASSWORD:-}" ]; then
  echo "Configure BOOTSTRAP_ADMIN_USERNAME and BOOTSTRAP_ADMIN_PASSWORD first; see README.md." >&2
  exit 1
fi
exec python3 server.py
