#!/usr/bin/env python3
"""Download the Windows EXE bundle from GitHub Releases into the repo workspace.

Fetches the asset ``NPU_Audio_Enhancer_windows.zip`` from the rolling release tag
``windows-exe`` (same as CI). Intended for Cursor / local workspace use.

Usage (from repository root)::

    python scripts/fetch_windows_release_zip.py
    python scripts/fetch_windows_release_zip.py --extract

Environment (optional)::

    GITHUB_TOKEN   Bearer token for private repositories or higher rate limits.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

DEFAULT_TAG = "windows-exe"
DEFAULT_ASSET = "NPU_Audio_Enhancer_windows.zip"
DEFAULT_EXTRACT_DIR = "Windows_EXE_Release"


def _repo_slug_from_git(remote: str | None = None) -> tuple[str, str]:
    if remote is None:
        r = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            check=False,
        )
        remote = (r.stdout or "").strip()
    if not remote:
        return "mj2cvqj7ct-creator", "NPU-AI"
    # https://github.com/owner/repo.git or git@github.com:owner/repo.git
    m = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", remote)
    if m:
        return m.group(1), m.group(2).removesuffix(".git")
    return "mj2cvqj7ct-creator", "NPU-AI"


def _release_api_url(owner: str, repo: str, tag: str) -> str:
    return f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}"


def _download(url: str, dest: Path, token: str | None) -> None:
    req = urllib.request.Request(url, headers={"Accept": "application/octet-stream"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310
        dest.write_bytes(resp.read())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tag",
        default=os.environ.get("NPU_RELEASE_TAG", DEFAULT_TAG),
        help=f"Release tag (default: {DEFAULT_TAG})",
    )
    parser.add_argument(
        "--asset",
        default=os.environ.get("NPU_RELEASE_ASSET", DEFAULT_ASSET),
        help=f"Asset filename (default: {DEFAULT_ASSET})",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path(DEFAULT_ASSET),
        help=f"Zip path (default: ./{DEFAULT_ASSET})",
    )
    parser.add_argument(
        "--extract",
        action="store_true",
        help=f"Extract zip into ./{DEFAULT_EXTRACT_DIR}/ (removes old folder first)",
    )
    parser.add_argument(
        "--extract-dir",
        type=Path,
        default=Path(DEFAULT_EXTRACT_DIR),
        help=f"Extraction directory (default: {DEFAULT_EXTRACT_DIR})",
    )
    args = parser.parse_args()

    owner, repo = _repo_slug_from_git()
    api_url = _release_api_url(owner, repo, args.tag)
    token = os.environ.get("GITHUB_TOKEN")

    req = urllib.request.Request(api_url, headers={"Accept": "application/vnd.github+json"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(
                f"Release tag '{args.tag}' not found for {owner}/{repo}.\n"
                "Wait for CI on main or run Actions → Windows EXE (PyInstaller).",
                file=sys.stderr,
            )
            return 2
        print(f"GitHub API error: {e}", file=sys.stderr)
        return 1

    assets = data.get("assets") or []
    download_url: str | None = None
    for a in assets:
        if a.get("name") == args.asset:
            download_url = a.get("browser_download_url")
            break
    if not download_url:
        names = [a.get("name") for a in assets]
        print(
            f"Asset {args.asset!r} not found. Available: {names}",
            file=sys.stderr,
        )
        return 3

    out_zip = args.output.resolve()
    print(f"Downloading {args.asset} → {out_zip}")
    _download(download_url, out_zip, token)
    print(f"OK ({out_zip.stat().st_size:,} bytes)")

    if args.extract:
        target = args.extract_dir.resolve()
        if target.exists():
            import shutil

            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out_zip, "r") as zf:
            zf.extractall(target)
        print(f"Extracted to {target}")
        exe = target / "NPU_Audio_Enhancer" / "NPU_Audio_Enhancer.exe"
        if exe.is_file():
            print(f"Run: {exe}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
