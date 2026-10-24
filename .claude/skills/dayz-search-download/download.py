"""Download a prebuilt dayz-rag vector index from GitHub releases.

Fetches the release asset (tarball), verifies the SHA-256 GitHub publishes for
the asset, and installs it to ~/.claude/dayz-search-index/. An asset with no
published digest is refused unless --allow-unverified is passed. The
existing index is kept until the new one is fully extracted and swapped in.
Stdlib only.

Usage:
    python download.py                    # latest release
    python download.py --tag 1.2.1        # specific tag
    python download.py --force            # overwrite existing index, even the same tag
    python download.py --allow-unverified # accept an asset with no published SHA-256
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = "DayZ-n-Chill/Agentic-Z"
# Releases have shipped the index under two names: dayz-rag-index-v0.1.0.tar.gz
# (v0.1.0 through 1.1.0, and 1.4.0) and dayz-search-index-<ver>.tar.gz (1.2.0,
# 1.2.1). The tarball's top folder may carry either name too (dayz-rag-index/ is
# what the original downloader expected). Any combination installs to INDEX_ROOT.
ASSET_PREFIXES = ("dayz-search-index-", "dayz-rag-index-")
ASSET_SUFFIX = ".tar.gz"
INDEX_ROOT = Path.home() / ".claude" / "dayz-search-index"
INDEX_DIR_NAMES = ("dayz-search-index", "dayz-rag-index")
INSTALLED_TAG_FILE = "release-tag.txt"


def log(level: str, msg: str) -> None:
    print(f"[{level}]\t{msg}", flush=True)


def _reason(err: OSError) -> str:
    """Short reason for a failed request. URLError covers connect-time failures
    (DNS, refused, HTTP status); a plain OSError is what a read raises
    mid-transfer (timeout, connection reset or aborted)."""
    if isinstance(err, urllib.error.HTTPError):
        return f"HTTP {err.code}"
    if isinstance(err, urllib.error.URLError):
        return str(err.reason)
    return str(err) or type(err).__name__


def _network_error(url: str, err: OSError) -> SystemExit:
    return SystemExit(
        f"[ERR]\tCould not reach {url}: {_reason(err)}\n"
        "\tCheck your internet connection (or proxy) and try again."
    )


def _rate_limit_error(url: str, err: urllib.error.HTTPError) -> SystemExit | None:
    """GitHub answers an exhausted API quota (60 requests an hour without a
    token) with 403 or 429 and X-RateLimit-Remaining: 0. Name it as such, with
    the reset time, rather than blaming the connection."""
    if err.code not in (403, 429) or err.headers is None:
        return None
    if err.headers.get("X-RateLimit-Remaining") != "0":
        return None
    reset = err.headers.get("X-RateLimit-Reset", "")
    when = (
        "at " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(reset)))
        if reset.isdigit()
        else "within an hour"
    )
    hint = (
        "\tThe GITHUB_TOKEN in your environment has used its quota too."
        if os.environ.get("GITHUB_TOKEN")
        else "\tSet GITHUB_TOKEN to a GitHub token to raise the limit to 5,000 an hour."
    )
    return SystemExit(
        f"[ERR]\tGitHub API rate limit reached for {url} (HTTP {err.code}).\n"
        f"\tThe limit resets {when}. Try again then.\n{hint}"
    )


def fetch_json(url: str) -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
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
        raise _rate_limit_error(url, e) or _network_error(url, e)
    except OSError as e:  # URLError, plus timeouts and resets while reading
        raise _network_error(url, e)


def find_asset(release: dict) -> dict:
    for asset in release.get("assets", []):
        name = asset.get("name", "")
        if name.startswith(ASSET_PREFIXES) and name.endswith(ASSET_SUFFIX):
            return asset
    patterns = " or ".join(f"{p}*{ASSET_SUFFIX}" for p in ASSET_PREFIXES)
    raise SystemExit(
        f"[ERR]\tNo asset matching {patterns} on release "
        f"{release.get('tag_name')}.\n"
        f"\tThe maintainer may not have uploaded the index for this version."
    )


def expected_sha256(asset: dict) -> str | None:
    """SHA-256 GitHub publishes for the asset ("digest": "sha256:<hex>"), if any."""
    digest = asset.get("digest") or ""
    algo, _, value = digest.partition(":")
    return value.lower() if algo == "sha256" and value else None


def installed_tag(index_root: Path) -> str | None:
    f = index_root / INSTALLED_TAG_FILE
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


def download_with_progress(url: str, dest: Path, expected_bytes: int) -> str:
    """Stream url to dest and return the SHA-256 hex digest of what was written."""
    chunk = 1 << 16  # 64K
    written = 0
    sha = hashlib.sha256()
    mb_total = expected_bytes / (1024 * 1024) if expected_bytes else 0
    try:
        with urllib.request.urlopen(url, timeout=60) as resp, dest.open("wb") as out:
            while True:
                buf = resp.read(chunk)
                if not buf:
                    break
                out.write(buf)
                sha.update(buf)
                written += len(buf)
                if expected_bytes:
                    mb = written / (1024 * 1024)
                    pct = (written / expected_bytes) * 100
                    print(
                        f"\r[INFO]\tDownloading... {mb:.1f}/{mb_total:.1f} MB ({pct:.0f}%)",
                        end="",
                        flush=True,
                    )
    except OSError as e:  # URLError, plus timeouts and resets mid-download
        print()
        raise SystemExit(
            f"[ERR]\tDownload from {url} failed after {written:,} bytes: {_reason(e)}\n"
            "\tCheck your internet connection (or proxy) and try again. "
            "Existing index left untouched."
        )
    print()
    return sha.hexdigest()


def safe_extract(tar: tarfile.TarFile, dest: Path) -> None:
    """Extract tar into dest, refusing any member that would land outside dest."""
    if hasattr(tarfile, "data_filter"):
        # Python 3.12+ and security backports: rejects absolute paths, ".."
        # traversal, and links that point outside dest.
        try:
            tar.extractall(dest, filter="data")
        except tarfile.FilterError as e:
            raise SystemExit(f"[ERR]\tUnsafe entry in tarball: {e}")
        return
    dest_resolved = dest.resolve()
    for member in tar.getmembers():
        member_path = (dest / member.name).resolve()
        inside = member_path == dest_resolved or dest_resolved in member_path.parents
        if not inside or member.issym() or member.islnk():
            raise SystemExit(f"[ERR]\tUnsafe entry in tarball: {member.name}")
    tar.extractall(dest)


def install(extracted: Path, index_root: Path, tag: str) -> None:
    """Swap extracted into index_root. The old index is removed only after the
    new one is in place, and is restored if the swap fails."""
    index_root.parent.mkdir(parents=True, exist_ok=True)
    staging = index_root.with_name(index_root.name + ".new")
    backup = index_root.with_name(index_root.name + ".old")
    for leftover in (staging, backup):
        if leftover.exists():
            shutil.rmtree(leftover)

    # The temp dir may be on another drive, so copy into a sibling first and
    # keep the final step a same-volume rename.
    shutil.move(str(extracted), str(staging))
    (staging / INSTALLED_TAG_FILE).write_text(tag + "\n", encoding="utf-8")

    had_old = index_root.exists()
    if had_old:
        try:
            index_root.rename(backup)
        except OSError as e:
            # On Windows a running dayz-rag MCP server holds the LanceDB files
            # open, so the folder cannot be moved aside.
            shutil.rmtree(staging, ignore_errors=True)
            raise SystemExit(
                f"[ERR]\tCould not move the existing index at {index_root} aside: {e}\n"
                "\tIt is probably in use by the dayz-rag MCP server. Close Claude Code "
                "(or disconnect dayz-rag with /mcp) and rerun. Existing index left untouched."
            )
    try:
        staging.rename(index_root)
    except OSError:
        if had_old:
            backup.rename(index_root)
        raise
    if had_old:
        shutil.rmtree(backup, ignore_errors=True)


def report_installed(index_root: Path) -> None:
    manifest = index_root / "manifest.json"
    config = index_root / "config.json"
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download prebuilt dayz-rag vector index.")
    parser.add_argument("--tag", help="Release tag (default: latest)")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing index without the prompt; reinstalls even when the tag already matches")
    parser.add_argument(
        "--allow-unverified",
        action="store_true",
        help="Install an asset even when the release publishes no SHA-256 digest for it",
    )
    args = parser.parse_args(argv)

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

    existing_tag = installed_tag(INDEX_ROOT)
    has_index = INDEX_ROOT.exists() and any(INDEX_ROOT.iterdir())
    if has_index and existing_tag == tag and not args.force:
        log("OK", f"Index for {tag} already installed. Nothing to do.")
        return 0

    want_sha = expected_sha256(asset)
    if want_sha is None and not args.allow_unverified:
        raise SystemExit(
            f"[ERR]\tRelease {tag} publishes no SHA-256 digest for {asset['name']}, "
            "so the download cannot be verified.\n"
            "\tRe-run with --allow-unverified to install it anyway."
        )

    if has_index and not args.force:
        installed_desc = f"({existing_tag})" if existing_tag else "(unknown origin)"
        if not confirm(f"Existing index found {installed_desc}. Overwrite with {tag}?"):
            log("INFO", "Aborted.")
            return 1

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        archive = tmp_path / asset["name"]
        actual_sha = download_with_progress(asset_url, archive, asset_size)
        log("OK", f"Downloaded {archive.stat().st_size / (1024 * 1024):.0f} MB")

        if want_sha is None:
            log("WARN", "No SHA-256 published for this asset; installing unverified (--allow-unverified).")
        elif actual_sha != want_sha:
            raise SystemExit(
                f"[ERR]\tSHA-256 mismatch for {asset['name']}.\n"
                f"\tExpected {want_sha}\n\tGot      {actual_sha}\n"
                "\tThe download is corrupt or was tampered with. Existing index left untouched."
            )
        else:
            log("OK", "SHA-256 verified.")

        log("INFO", "Extracting...")
        out_dir = tmp_path / "extract"
        out_dir.mkdir()
        with tarfile.open(archive, "r:gz") as tar:
            safe_extract(tar, out_dir)

        extracted = next((out_dir / n for n in INDEX_DIR_NAMES if (out_dir / n).is_dir()), None)
        if extracted is None:
            expected = " or ".join(f"'{n}/'" for n in INDEX_DIR_NAMES)
            raise SystemExit(
                f"[ERR]\tArchive did not contain an expected {expected} directory. "
                "Existing index left untouched."
            )
        install(extracted, INDEX_ROOT, tag)

    report_installed(INDEX_ROOT)
    log("OK", "Done. Restart Claude Code to reconnect the dayz-rag MCP server.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
