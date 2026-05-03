#!/usr/bin/env bash
# Download Windows release zip into the repository root (Cursor workspace).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required" >&2
  exit 1
fi
python3 "$ROOT/scripts/fetch_windows_release_zip.py" --extract "$@"
