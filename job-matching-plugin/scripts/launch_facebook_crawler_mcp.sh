#!/usr/bin/env sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
server="$script_dir/../mcp/facebook_crawler_server.py"

if [ -n "${JOB_MATCHING_PYTHON:-}" ]; then
  exec "$JOB_MATCHING_PYTHON" "$server"
fi
if command -v python3 >/dev/null 2>&1; then
  exec python3 "$server"
fi
if command -v python >/dev/null 2>&1; then
  exec python "$server"
fi
echo "JobMatching: no Python interpreter was found." >&2
exit 1
