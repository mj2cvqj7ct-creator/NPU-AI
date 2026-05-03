#!/usr/bin/env bash
# Download the latest successful "Windows EXE (PyInstaller)" artifact and
# extract to Cursor cloud desktop: $HOME/Desktop/NPU_Audio_Enhancer/
#
# Requires: gh (GitHub CLI), authenticated (gh auth login)
# Usage: ./scripts/fetch_windows_exe_desktop.sh [branch]
# Default branch: main

set -euo pipefail

# Optional: restrict to a branch (e.g. main). Default: latest success on any branch.
BRANCH_FILTER="${1:-}"
REPO="${GITHUB_REPOSITORY:-mj2cvqj7ct-creator/NPU-AI}"
DESK="${HOME}/Desktop"
WORKFLOW="Windows EXE (PyInstaller)"
ARTIFACT="NPU_Audio_Enhancer_windows"
ZIP_NAME="NPU_Audio_Enhancer_windows.zip"

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: gh (GitHub CLI) is required." >&2
  exit 1
fi

echo "Looking for latest successful run: repo=$REPO workflow=$WORKFLOW${BRANCH_FILTER:+ branch=$BRANCH_FILTER}"
if [[ -n "$BRANCH_FILTER" ]]; then
  RUN_ID="$(gh run list --repo "$REPO" --workflow "$WORKFLOW" --branch "$BRANCH_FILTER" --status success -L 1 --json databaseId -q '.[0].databaseId')"
else
  RUN_ID="$(gh run list --repo "$REPO" --workflow "$WORKFLOW" --status success -L 1 --json databaseId -q '.[0].databaseId')"
fi
if [[ -z "$RUN_ID" || "$RUN_ID" == "null" ]]; then
  echo "ERROR: No successful Windows EXE workflow run found." >&2
  exit 1
fi

echo "Downloading run $RUN_ID ($ARTIFACT)..."
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
gh run download "$RUN_ID" --repo "$REPO" -n "$ARTIFACT" -D "$TMP"

ZIP_PATH="$TMP/$ZIP_NAME"
if [[ ! -f "$ZIP_PATH" ]]; then
  echo "ERROR: Expected $ZIP_PATH after download" >&2
  ls -la "$TMP" >&2 || true
  exit 1
fi

mkdir -p "$DESK"
rm -rf "$DESK/NPU_Audio_Enhancer"
echo "Extracting to $DESK ..."
unzip -q -o "$ZIP_PATH" -d "$DESK"
cp -f "$ZIP_PATH" "$DESK/$ZIP_NAME"

echo "OK: $DESK/NPU_Audio_Enhancer/NPU_Audio_Enhancer.exe"
ls -la "$DESK/NPU_Audio_Enhancer/NPU_Audio_Enhancer.exe" "$DESK/$ZIP_NAME"
