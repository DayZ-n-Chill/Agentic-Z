"""Download a prebuilt dayz-rag vector index from GitHub releases.

Fetches the release asset (tarball), extracts to ~/.claude/dayz-rag-index/.
Stdlib only — urllib + tarfile + json.

Usage:
    python download.py                    # latest release
    python download.py --tag v0.1.0       # specific tag
    python download.py --force            # overwrite existing index
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

REPO = "DayZ-n-Chill/Agentic-Z"
ASSET_PREFIX = "dayz-rag-index-"
ASSET_SUFFIX = ".tar.gz"
INDEX_ROOT = Path.home() / ".claude" / "dayz-rag-index"
INDEX_DIR_NAME = "dayz-rag-index"
INSTALLED_TAG_FILE = "release-tag.txt"


def log(level: str, msg: str) -> None:
    print(f"[{level}]\t{msg}", flush=True)


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def resolve_release(tag: str | None) -> dict:
    if tag:
        url = f"https://api.github.com/repos/{REPO}/releases/tags/{tag}"
    else:
        url = f"https://api.github.com/repos/{REPO}/releases/latest"
    try:
        return fetch_json(url)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise SystemExit(
                f"[ERR]\tRelease not found: {tag or 'latest'}.\n"
                f"\tCheck https://github.com/{REPO}/releases."
            )
        raise


def find_asset(release: dict) -> dict:
    for asset in release.get("assets", []):
        name = asset.get("name", "")
        if name.startswith(ASSET_PREFIX) and name.endswith(ASSET_SUFFIX):
            return asset
    raise SystemExit(
        f"[ERR]\tNo asset matching {ASSET_PREFIX}*{ASSET_SUFFIX} on release "
        f"{release.get('tag_name')}.\n"
        f"\tThe maintainer may not have uploaded the index for this version."
    )


def installed_tag() -> str | None:
    f = INDEX_ROOT / INSTALLED_TAG_FILE
    if not f.exists():
        return None
    try:
        return f.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def confirm(prompt: str) -> bool:
    try:
        ans = input(f"{prompt} [y/N]: ").strip().lower()
    except EOFError:
        return False
    return ans in ("y", "yes")


def download_with_progress(url: str, dest: Path, expected_bytes: int) -> None:
    chunk = 1 << 16  # 64K
    written = 0
    mb_total = expected_bytes / (1024 * 1024) if expected_bytes else 0
    with urllib.request.urlopen(url, timeout=60) as resp, dest.open("wb") as out:
        while True:
            buf = resp.read(chunk)
            if not buf:
                break
            out.write(buf)
            written += len(buf)
            if expected_bytes:
                mb = written / (1024 * 1024)
                pct = (written / expected_bytes) * 100
                print(
                    f"\r[INFO]\tDownloading... {mb:.1f}/{mb_total:.1f} MB ({pct:.0f}%)",
                    end="",
                    flush=True,
                )
    print()


def safe_extract(tar: tarfile.TarFile, dest: Path) -> None:
    dest_resolved = dest.resolve()
    for member in tar.getmembers():
        member_path = (dest / member.name).resolve()
        if not str(member_path).startswith(str(dest_resolved)):
            raise SystemExit(f"[ERR]\tBlocked path traversal in tarball: {member.name}")
    tar.extractall(dest)


def main() -> int:
    parser = argparse.ArgumentParser(description="Download prebuilt dayz-rag vector index.")
    parser.add_argument("--tag", help="Release tag (default: latest)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing index without prompt")
    args = parser.parse_args()

    print("DayZ RAG index downloader\n")
    log("INFO", f"Repo: {REPO}")
    log("INFO", f"Resolving {'tag ' + args.tag if args.tag else 'latest release'}...")

    release = resolve_release(args.tag)
    tag = release.get("tag_name", "?")
    log("OK", f"Release: {tag}")

    asset = find_asset(release)
    asset_url = asset["browser_download_url"]
    asset_size = asset.get("size", 0)
    log("INFO", f"Asset: {asset['name']} ({asset_size / (1024 * 1024):.0f} MB)")
    log("INFO", f"Target: {INDEX_ROOT}")

    existing_tag = installed_tag()
    if INDEX_ROOT.exists() and any(INDEX_ROOT.iterdir()):
        if existing_tag == tag and not args.force:
            log("OK", f"Index for {tag} already installed. Nothing to do.")
            return 0
        if not args.force:
            installed_desc = f"({existing_tag})" if existing_tag else "(unknown origin)"
            if not confirm(f"Existing index found {installed_desc}. Overwrite with {tag}?"):
                log("INFO", "Aborted.")
                return 1

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        archive = tmp_path / asset["name"]
        download_with_progress(asset_url, archive, asset_size)
        log("OK", f"Downloaded {archive.stat().st_size / (1024 * 1024):.0f} MB")

        log("INFO", "Extracting...")
        with tarfile.open(archive, "r:gz") as tar:
            safe_extract(tar, tmp_path)

        extracted = tmp_path / INDEX_DIR_NAME
        if not extracted.is_dir():
            raise SystemExit(
                f"[ERR]\tArchive did not contain expected '{INDEX_DIR_NAME}/' directory."
            )

        if INDEX_ROOT.exists():
            shutil.rmtree(INDEX_ROOT)
        INDEX_ROOT.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(extracted), str(INDEX_ROOT))

    (INDEX_ROOT / INSTALLED_TAG_FILE).write_text(tag + "\n", encoding="utf-8")

    manifest = INDEX_ROOT / "manifest.json"
    config = INDEX_ROOT / "config.json"
    if manifest.exists():
        try:
            m = json.loads(manifest.read_text(encoding="utf-8"))
            chunks = sum(
                ext.get("chunks", 0) if isinstance(ext, dict) else 0
                for folder in m.get("counts_by_folder", {}).values()
                if isinstance(folder, dict)
                for ext in folder.values()
            )
            if chunks:
                log("OK", f"Indexed source chunks: {chunks}")
        except (json.JSONDecodeError, OSError):
            pass
    if config.exists():
        try:
            c = json.loads(config.read_text(encoding="utf-8"))
            log("OK", f"Embed model: {c.get('embed_model', '?')}")
        except (json.JSONDecodeError, OSError):
            pass

    log("OK", "Done. Restart Claude Code to reconnect the dayz-rag MCP server.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
