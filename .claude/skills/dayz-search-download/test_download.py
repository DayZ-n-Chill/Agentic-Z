"""Tests for dayz-search-download/download.py. No network: every GitHub call
and download is mocked, and the index root is a tmp_path."""
from __future__ import annotations

import hashlib
import importlib.util
import io
import tarfile
import urllib.error
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parent / "download.py"


@pytest.fixture
def dl(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("dayz_search_download", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "INDEX_ROOT", tmp_path / "home" / "dayz-search-index")
    return mod


def _tar_bytes(entries: list[tarfile.TarInfo], payload: bytes = b"x") -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for info in entries:
            if info.isfile():
                info.size = len(payload)
                tar.addfile(info, io.BytesIO(payload))
            else:
                tar.addfile(info)
    return buf.getvalue()


def _open(data: bytes) -> tarfile.TarFile:
    return tarfile.open(fileobj=io.BytesIO(data), mode="r:gz")


def _file(name: str) -> tarfile.TarInfo:
    return tarfile.TarInfo(name)


def _symlink(name: str, target: str) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.type = tarfile.SYMTYPE
    info.linkname = target
    return info


# --- safe_extract ---------------------------------------------------------

def test_safe_extract_extracts_normal_members(dl, tmp_path):
    dest = tmp_path / "out"
    dest.mkdir()
    with _open(_tar_bytes([_file("dayz-search-index/manifest.json")])) as tar:
        dl.safe_extract(tar, dest)
    assert (dest / "dayz-search-index" / "manifest.json").read_bytes() == b"x"


@pytest.mark.parametrize(
    "member",
    [
        _file("../escape.txt"),
        _file("dayz-search-index/../../escape.txt"),
        _symlink("dayz-search-index/link", "../../outside"),
    ],
    ids=["dotdot", "nested-dotdot", "symlink-out"],
)
def test_safe_extract_blocks_escapes(dl, tmp_path, member):
    dest = tmp_path / "out"
    dest.mkdir()
    with _open(_tar_bytes([member])) as tar:
        with pytest.raises(SystemExit) as exc:
            dl.safe_extract(tar, dest)
    assert "Unsafe entry" in str(exc.value)
    assert not (tmp_path / "escape.txt").exists()


def test_safe_extract_blocks_absolute_paths(dl, tmp_path):
    dest = tmp_path / "out"
    dest.mkdir()
    target = (tmp_path / "abs.txt").as_posix()
    with _open(_tar_bytes([_file(target)])) as tar:
        try:
            dl.safe_extract(tar, dest)
        except SystemExit:
            pass
    # Either refused outright or (data filter) re-rooted under dest; never written outside.
    assert not (tmp_path / "abs.txt").exists()


# --- installed-tag skip ---------------------------------------------------

def _release(tag="v1.0.0", digest=None):
    asset = {
        "name": f"dayz-search-index-{tag}.tar.gz",
        "browser_download_url": "https://example.invalid/a.tar.gz",
        "size": 10,
    }
    if digest:
        asset["digest"] = digest
    return {"tag_name": tag, "assets": [asset]}


def test_skips_when_installed_tag_matches(dl, monkeypatch):
    dl.INDEX_ROOT.mkdir(parents=True)
    (dl.INDEX_ROOT / dl.INSTALLED_TAG_FILE).write_text("v1.0.0\n", encoding="utf-8")
    monkeypatch.setattr(dl, "resolve_release", lambda tag: _release())

    def no_download(*a, **k):
        raise AssertionError("must not download when the tag is already installed")

    monkeypatch.setattr(dl, "download_with_progress", no_download)
    assert dl.main([]) == 0


def test_different_tag_without_force_declined_keeps_index(dl, monkeypatch):
    dl.INDEX_ROOT.mkdir(parents=True)
    (dl.INDEX_ROOT / dl.INSTALLED_TAG_FILE).write_text("v0.9.0\n", encoding="utf-8")
    monkeypatch.setattr(dl, "resolve_release", lambda tag: _release(digest="sha256:" + "a" * 64))
    monkeypatch.setattr(dl, "confirm", lambda prompt: False)
    assert dl.main([]) == 1
    assert dl.installed_tag(dl.INDEX_ROOT) == "v0.9.0"


@pytest.mark.parametrize("existing_tag, desc", [("v0.9.0", "v0.9.0"), (None, "unknown origin")])
def test_no_stdin_prompt_ends_on_fail_line_with_force_hint(dl, monkeypatch, capsys, existing_tag, desc):
    """An agent's shell has no stdin: input() raises EOFError. The run must end
    on a [FAIL] line naming both tags and the --force rerun, and keep the index."""
    dl.INDEX_ROOT.mkdir(parents=True)
    (dl.INDEX_ROOT / "old.txt").write_text("old", encoding="utf-8")
    if existing_tag:
        (dl.INDEX_ROOT / dl.INSTALLED_TAG_FILE).write_text(existing_tag + "\n", encoding="utf-8")
    monkeypatch.setattr(dl, "resolve_release", lambda tag: _release(digest="sha256:" + "a" * 64))

    def no_stdin(prompt=""):
        raise EOFError

    def no_download(*a, **k):
        raise AssertionError("must not download when the overwrite prompt is declined")

    monkeypatch.setattr("builtins.input", no_stdin)
    monkeypatch.setattr(dl, "download_with_progress", no_download)
    assert dl.main([]) == 1
    last = capsys.readouterr().out.strip().splitlines()[-1]
    assert last.startswith("[FAIL]\t")
    assert desc in last and "v1.0.0" in last and "--force" in last
    assert (dl.INDEX_ROOT / "old.txt").exists()


# --- full install path with mocked download -------------------------------

def _fake_download(data: bytes):
    def _dl(url, dest, expected):
        dest.write_bytes(data)
        return hashlib.sha256(data).hexdigest()
    return _dl


def test_force_install_replaces_index_and_records_tag(dl, monkeypatch):
    dl.INDEX_ROOT.mkdir(parents=True)
    (dl.INDEX_ROOT / "old.txt").write_text("old", encoding="utf-8")
    data = _tar_bytes([_file("dayz-search-index/manifest.json")])
    digest = "sha256:" + hashlib.sha256(data).hexdigest()
    monkeypatch.setattr(dl, "resolve_release", lambda tag: _release(digest=digest))
    monkeypatch.setattr(dl, "download_with_progress", _fake_download(data))
    assert dl.main(["--force"]) == 0
    assert not (dl.INDEX_ROOT / "old.txt").exists()
    assert (dl.INDEX_ROOT / "manifest.json").exists()
    assert dl.installed_tag(dl.INDEX_ROOT) == "v1.0.0"
    assert not dl.INDEX_ROOT.with_name(dl.INDEX_ROOT.name + ".old").exists()


def test_checksum_mismatch_keeps_old_index(dl, monkeypatch):
    dl.INDEX_ROOT.mkdir(parents=True)
    (dl.INDEX_ROOT / "old.txt").write_text("old", encoding="utf-8")
    data = _tar_bytes([_file("dayz-search-index/manifest.json")])
    monkeypatch.setattr(dl, "resolve_release", lambda tag: _release(digest="sha256:" + "0" * 64))
    monkeypatch.setattr(dl, "download_with_progress", _fake_download(data))
    with pytest.raises(SystemExit) as exc:
        dl.main(["--force"])
    assert "SHA-256 mismatch" in str(exc.value)
    assert (dl.INDEX_ROOT / "old.txt").exists()


def test_missing_checksum_refused_without_flag(dl, monkeypatch):
    monkeypatch.setattr(dl, "resolve_release", lambda tag: _release())

    def no_download(*a, **k):
        raise AssertionError("must not download an unverifiable asset")

    monkeypatch.setattr(dl, "download_with_progress", no_download)
    with pytest.raises(SystemExit) as exc:
        dl.main([])
    assert "--allow-unverified" in str(exc.value)
    assert not dl.INDEX_ROOT.exists()


def test_missing_checksum_installs_with_allow_unverified(dl, monkeypatch, capsys):
    data = _tar_bytes([_file("dayz-search-index/manifest.json")])
    monkeypatch.setattr(dl, "resolve_release", lambda tag: _release())
    monkeypatch.setattr(dl, "download_with_progress", _fake_download(data))
    assert dl.main(["--allow-unverified"]) == 0
    assert "installing unverified" in capsys.readouterr().out
    assert (dl.INDEX_ROOT / "manifest.json").exists()


def test_install_restores_old_index_when_swap_fails(dl, tmp_path, monkeypatch):
    dl.INDEX_ROOT.mkdir(parents=True)
    (dl.INDEX_ROOT / "old.txt").write_text("old", encoding="utf-8")
    extracted = tmp_path / "extracted"
    extracted.mkdir()
    (extracted / "manifest.json").write_text("{}", encoding="utf-8")

    real_rename = Path.rename

    def flaky_rename(self, target):
        if self.name.endswith(".new"):
            raise OSError("simulated failure")
        return real_rename(self, target)

    monkeypatch.setattr(Path, "rename", flaky_rename)
    with pytest.raises(SystemExit) as exc:
        dl.install(extracted, dl.INDEX_ROOT, "v1.0.0")
    msg = str(exc.value)
    assert msg.startswith("[FAIL]\tCould not move the new index into")
    assert "simulated failure" in msg
    assert "old index was restored" in msg
    assert (dl.INDEX_ROOT / "old.txt").exists()
    assert not dl.INDEX_ROOT.with_name(dl.INDEX_ROOT.name + ".new").exists()
    assert not dl.INDEX_ROOT.with_name(dl.INDEX_ROOT.name + ".old").exists()


def test_install_names_old_index_when_restore_also_fails(dl, tmp_path, monkeypatch):
    dl.INDEX_ROOT.mkdir(parents=True)
    (dl.INDEX_ROOT / "old.txt").write_text("old", encoding="utf-8")
    extracted = tmp_path / "extracted"
    extracted.mkdir()
    (extracted / "manifest.json").write_text("{}", encoding="utf-8")
    backup = dl.INDEX_ROOT.with_name(dl.INDEX_ROOT.name + ".old")

    real_rename = Path.rename

    def flaky_rename(self, target):
        if self.name.endswith((".new", ".old")):
            raise OSError("simulated failure")
        return real_rename(self, target)

    monkeypatch.setattr(Path, "rename", flaky_rename)
    with pytest.raises(SystemExit) as exc:
        dl.install(extracted, dl.INDEX_ROOT, "v1.0.0")
    msg = str(exc.value)
    assert msg.startswith("[FAIL]\t")
    assert "Restoring the old index also failed" in msg
    assert str(backup) in msg
    assert (backup / "old.txt").exists()


def test_install_staging_copy_failure_keeps_old_index(dl, tmp_path, monkeypatch):
    dl.INDEX_ROOT.mkdir(parents=True)
    (dl.INDEX_ROOT / "old.txt").write_text("old", encoding="utf-8")
    extracted = tmp_path / "extracted"
    extracted.mkdir()

    def full_disk(src, dst):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(dl.shutil, "move", full_disk)
    with pytest.raises(SystemExit) as exc:
        dl.install(extracted, dl.INDEX_ROOT, "v1.0.0")
    msg = str(exc.value)
    assert msg.startswith("[FAIL]\tCould not copy the new index")
    assert "Existing index left untouched" in msg
    assert (dl.INDEX_ROOT / "old.txt").exists()
    assert not dl.INDEX_ROOT.with_name(dl.INDEX_ROOT.name + ".new").exists()


# --- network errors and checksum parsing ----------------------------------

def test_url_error_exits_with_clear_message(dl, monkeypatch):
    def offline(*a, **k):
        raise urllib.error.URLError("getaddrinfo failed")

    monkeypatch.setattr(dl.urllib.request, "urlopen", offline)
    with pytest.raises(SystemExit) as exc:
        dl.resolve_release(None)
    assert "Could not reach" in str(exc.value)
    assert "getaddrinfo failed" in str(exc.value)


def test_download_url_error_exits(dl, tmp_path, monkeypatch):
    def offline(*a, **k):
        raise urllib.error.URLError("timed out")

    monkeypatch.setattr(dl.urllib.request, "urlopen", offline)
    with pytest.raises(SystemExit) as exc:
        dl.download_with_progress("https://example.invalid/x", tmp_path / "x", 0)
    assert "timed out" in str(exc.value)


class _BrokenStream:
    """Response that yields one chunk, then fails the way a dropped connection does."""

    def __init__(self, err):
        self._err = err
        self._sent = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, n):
        if not self._sent:
            self._sent = True
            return b"x" * 10
        raise self._err


@pytest.mark.parametrize(
    "err, reason",
    [
        (TimeoutError("The read operation timed out"), "The read operation timed out"),
        (ConnectionResetError(10054, "An existing connection was forcibly closed"), "forcibly closed"),
    ],
)
def test_download_error_mid_read_exits_with_url_and_reason(dl, tmp_path, monkeypatch, err, reason):
    monkeypatch.setattr(dl.urllib.request, "urlopen", lambda *a, **k: _BrokenStream(err))
    url = "https://example.invalid/index.tar.gz"
    with pytest.raises(SystemExit) as exc:
        dl.download_with_progress(url, tmp_path / "x", 100)
    msg = str(exc.value)
    assert url in msg
    assert reason in msg
    assert "after 10 bytes" in msg


def test_resolve_release_read_timeout_exits(dl, monkeypatch):
    def slow(*a, **k):
        raise TimeoutError("The read operation timed out")

    monkeypatch.setattr(dl, "fetch_json", slow)
    with pytest.raises(SystemExit) as exc:
        dl.resolve_release("1.2.1")
    assert "Could not reach https://api.github.com/" in str(exc.value)
    assert "timed out" in str(exc.value)


@pytest.mark.parametrize(
    "asset, expected",
    [
        ({"digest": "sha256:ABCDEF"}, "abcdef"),
        ({"digest": None}, None),
        ({}, None),
        ({"digest": "md5:abc"}, None),
    ],
)
def test_expected_sha256(dl, asset, expected):
    assert dl.expected_sha256(asset) == expected


def test_force_reinstalls_same_tag(dl, monkeypatch):
    dl.INDEX_ROOT.mkdir(parents=True)
    (dl.INDEX_ROOT / dl.INSTALLED_TAG_FILE).write_text("v1.0.0\n", encoding="utf-8")
    (dl.INDEX_ROOT / "old.txt").write_text("old", encoding="utf-8")
    data = _tar_bytes([_file("dayz-search-index/manifest.json")])
    digest = "sha256:" + hashlib.sha256(data).hexdigest()
    monkeypatch.setattr(dl, "resolve_release", lambda tag: _release(digest=digest))
    monkeypatch.setattr(dl, "download_with_progress", _fake_download(data))
    assert dl.main(["--force"]) == 0
    assert not (dl.INDEX_ROOT / "old.txt").exists()
    assert dl.installed_tag(dl.INDEX_ROOT) == "v1.0.0"


# --- real release asset names (from the GitHub releases API) --------------

# Asset names as published on DayZ-n-Chill/Agentic-Z releases.
REAL_ASSETS = [
    ("1.4.0", "dayz-rag-index-v0.1.0.tar.gz"),
    ("1.2.1", "dayz-search-index-1.2.1.tar.gz"),
    ("1.2.0", "dayz-search-index-1.2.0.tar.gz"),
    ("v0.1.0", "dayz-rag-index-v0.1.0.tar.gz"),
]


@pytest.mark.parametrize("tag, name", REAL_ASSETS)
def test_find_asset_matches_real_release_names(dl, tag, name):
    release = {"tag_name": tag, "assets": [{"name": "notes.txt"}, {"name": name}]}
    assert dl.find_asset(release)["name"] == name


def test_find_asset_refuses_release_without_index(dl):
    with pytest.raises(SystemExit) as exc:
        dl.find_asset({"tag_name": "1.2.2", "assets": []})
    assert "dayz-rag-index-*.tar.gz" in str(exc.value)
    assert "dayz-search-index-*.tar.gz" in str(exc.value)


@pytest.mark.parametrize("top", ["dayz-rag-index", "dayz-search-index"])
def test_installs_either_top_folder_to_current_index_path(dl, monkeypatch, top):
    data = _tar_bytes([_file(f"{top}/manifest.json")])
    digest = "sha256:" + hashlib.sha256(data).hexdigest()
    release = {
        "tag_name": "1.4.0",
        "assets": [{
            "name": "dayz-rag-index-v0.1.0.tar.gz",
            "browser_download_url": "https://example.invalid/a.tar.gz",
            "size": len(data),
            "digest": digest,
        }],
    }
    monkeypatch.setattr(dl, "resolve_release", lambda tag: release)
    monkeypatch.setattr(dl, "download_with_progress", _fake_download(data))
    assert dl.main([]) == 0
    assert dl.INDEX_ROOT.name == "dayz-search-index"
    assert (dl.INDEX_ROOT / "manifest.json").exists()
    assert dl.installed_tag(dl.INDEX_ROOT) == "1.4.0"


def test_archive_without_known_top_folder_is_refused(dl, monkeypatch):
    data = _tar_bytes([_file("something-else/manifest.json")])
    digest = "sha256:" + hashlib.sha256(data).hexdigest()
    monkeypatch.setattr(dl, "resolve_release", lambda tag: _release(digest=digest))
    monkeypatch.setattr(dl, "download_with_progress", _fake_download(data))
    with pytest.raises(SystemExit) as exc:
        dl.main([])
    assert "'dayz-rag-index/'" in str(exc.value)
    assert not dl.INDEX_ROOT.exists()


# --- GitHub API rate limit ------------------------------------------------

def _http_error(code, headers):
    import email.message

    msg = email.message.Message()
    for k, v in headers.items():
        msg[k] = v
    return urllib.error.HTTPError("https://api.github.com/x", code, "Forbidden", msg, None)


@pytest.mark.parametrize("code", [403, 429])
def test_rate_limit_reported_as_rate_limit_with_reset(dl, monkeypatch, code):
    reset = 1893456000  # 2030-01-01 UTC

    def limited(*a, **k):
        raise _http_error(code, {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(reset)})

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(dl, "fetch_json", limited)
    with pytest.raises(SystemExit) as exc:
        dl.resolve_release(None)
    msg = str(exc.value)
    assert "rate limit" in msg
    assert f"HTTP {code}" in msg
    assert dl.time.strftime("%Y-%m-%d %H:%M:%S", dl.time.localtime(reset)) in msg
    assert "GITHUB_TOKEN" in msg
    assert "internet connection" not in msg


def test_plain_403_still_reported_as_network_error(dl, monkeypatch):
    def forbidden(*a, **k):
        raise _http_error(403, {"X-RateLimit-Remaining": "42"})

    monkeypatch.setattr(dl, "fetch_json", forbidden)
    with pytest.raises(SystemExit) as exc:
        dl.resolve_release(None)
    assert "Could not reach" in str(exc.value)
    assert "HTTP 403" in str(exc.value)
    assert "rate limit" not in str(exc.value)


class _JsonResponse:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return b'{"tag_name": "v1"}'


def test_fetch_json_sends_github_token_when_set(dl, monkeypatch):
    seen = {}

    def capture(req, timeout=None):
        seen["auth"] = req.get_header("Authorization")
        return _JsonResponse()

    monkeypatch.setattr(dl.urllib.request, "urlopen", capture)
    monkeypatch.setenv("GITHUB_TOKEN", "abc123")
    assert dl.fetch_json("https://api.github.com/x") == {"tag_name": "v1"}
    assert seen["auth"] == "Bearer abc123"

    monkeypatch.delenv("GITHUB_TOKEN")
    dl.fetch_json("https://api.github.com/x")
    assert seen["auth"] is None


# --- index locked by the running MCP server -------------------------------

def test_install_locked_index_exits_with_clear_message(dl, tmp_path, monkeypatch):
    dl.INDEX_ROOT.mkdir(parents=True)
    (dl.INDEX_ROOT / "old.txt").write_text("old", encoding="utf-8")
    extracted = tmp_path / "extracted"
    extracted.mkdir()
    (extracted / "manifest.json").write_text("{}", encoding="utf-8")

    real_rename = Path.rename

    def locked_rename(self, target):
        if self == dl.INDEX_ROOT:
            raise PermissionError(13, "Access is denied", str(self))
        return real_rename(self, target)

    monkeypatch.setattr(Path, "rename", locked_rename)
    with pytest.raises(SystemExit) as exc:
        dl.install(extracted, dl.INDEX_ROOT, "v1.0.0")
    msg = str(exc.value)
    assert "Close Claude Code" in msg
    assert "disconnect dayz-rag" in msg
    assert "rerun" in msg
    assert (dl.INDEX_ROOT / "old.txt").exists()
    assert not dl.INDEX_ROOT.with_name(dl.INDEX_ROOT.name + ".new").exists()


# --- latest release without an index asset --------------------------------

def _no_list(*a, **k):
    raise AssertionError("must not list releases")


def test_latest_without_asset_falls_back_to_newest_release_with_one(dl, monkeypatch, capsys):
    data = _tar_bytes([_file("dayz-rag-index/manifest.json")])
    digest = "sha256:" + hashlib.sha256(data).hexdigest()
    latest = {"tag_name": "1.5.0", "assets": [{"name": "notes.txt"}]}
    older = _release(tag="1.4.0", digest=digest)
    monkeypatch.setattr(dl, "resolve_release", lambda tag: latest)
    monkeypatch.setattr(
        dl,
        "list_releases",
        lambda: [
            latest,
            {**_release(tag="1.6.0-rc1", digest=digest), "prerelease": True},
            {**_release(tag="1.5.1", digest=digest), "draft": True},
            older,
        ],
    )
    monkeypatch.setattr(dl, "download_with_progress", _fake_download(data))
    assert dl.main([]) == 0
    out = capsys.readouterr().out
    assert "[WARN]\tLatest release 1.5.0 has no index asset; using 1.4.0" in out
    assert "[OK]\tRelease: 1.4.0" in out
    assert dl.installed_tag(dl.INDEX_ROOT) == "1.4.0"


def test_explicit_tag_without_asset_does_not_fall_back(dl, monkeypatch):
    monkeypatch.setattr(dl, "resolve_release", lambda tag: {"tag_name": tag, "assets": []})
    monkeypatch.setattr(dl, "list_releases", _no_list)
    with pytest.raises(SystemExit) as exc:
        dl.main(["--tag", "1.2.2"])
    assert str(exc.value).startswith("[FAIL]\tNo asset matching")
    assert "1.2.2" in str(exc.value)


def test_latest_with_asset_does_not_list_releases(dl, monkeypatch):
    monkeypatch.setattr(dl, "resolve_release", lambda tag: _release(tag="1.4.0"))
    monkeypatch.setattr(dl, "list_releases", _no_list)
    release, asset = dl.resolve_release_and_asset(None)
    assert release["tag_name"] == "1.4.0"
    assert asset["name"] == "dayz-search-index-1.4.0.tar.gz"


def test_no_release_with_asset_fails_clearly(dl, monkeypatch):
    latest = {"tag_name": "1.5.0", "assets": []}
    monkeypatch.setattr(dl, "resolve_release", lambda tag: latest)
    monkeypatch.setattr(dl, "list_releases", lambda: [latest, {"tag_name": "1.0.0", "assets": []}])
    with pytest.raises(SystemExit) as exc:
        dl.main([])
    msg = str(exc.value)
    assert msg.startswith("[FAIL]\tNo published release has an asset matching")
    assert "latest is 1.5.0" in msg
    assert "/dayz-search-index" in msg
    assert not dl.INDEX_ROOT.exists()


def test_list_releases_rate_limit_is_reported(dl, monkeypatch):
    def limited(*a, **k):
        raise _http_error(403, {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1893456000"})

    monkeypatch.setattr(dl, "fetch_json", limited)
    with pytest.raises(SystemExit) as exc:
        dl.list_releases()
    assert "rate limit" in str(exc.value)
    assert "/releases?per_page=100" in str(exc.value)


def test_errors_use_the_repo_fail_tag(dl):
    source = _SCRIPT.read_text(encoding="utf-8")
    assert "[ERR]" not in source
    with pytest.raises(SystemExit) as exc:
        dl.find_asset({"tag_name": "1.2.2", "assets": []})
    assert str(exc.value).startswith("[FAIL]\t")


# --- corrupt archives and short downloads ---------------------------------

def _good_archive() -> bytes:
    return _tar_bytes([_file("dayz-search-index/manifest.json")], payload=b"x" * 4096)


@pytest.mark.parametrize(
    "data",
    [
        _good_archive()[:-40],  # truncated gzip: EOFError while reading
        _good_archive()[:30],  # truncated inside the tar header
        b"this is not a gzip file at all",  # tarfile.ReadError
    ],
    ids=["truncated-tail", "truncated-head", "not-gzip"],
)
def test_corrupt_archive_under_allow_unverified_fails_cleanly(dl, monkeypatch, data):
    dl.INDEX_ROOT.mkdir(parents=True)
    (dl.INDEX_ROOT / "old.txt").write_text("old", encoding="utf-8")
    monkeypatch.setattr(dl, "resolve_release", lambda tag: _release())
    monkeypatch.setattr(dl, "download_with_progress", _fake_download(data))
    with pytest.raises(SystemExit) as exc:
        dl.main(["--allow-unverified", "--force"])
    msg = str(exc.value)
    assert msg.startswith("[FAIL]\tArchive ")
    assert "corrupt or truncated" in msg
    assert "Existing index left untouched" in msg
    assert (dl.INDEX_ROOT / "old.txt").exists()
    assert dl.installed_tag(dl.INDEX_ROOT) is None


class _Stream:
    def __init__(self, data: bytes):
        self._buf = io.BytesIO(data)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, n):
        return self._buf.read(n)


def test_short_download_is_refused(dl, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(dl.urllib.request, "urlopen", lambda *a, **k: _Stream(b"x" * 5))
    url = "https://example.invalid/index.tar.gz"
    with pytest.raises(SystemExit) as exc:
        dl.download_with_progress(url, tmp_path / "x", 10)
    msg = str(exc.value)
    assert msg.startswith("[FAIL]\tDownload from " + url + " is incomplete")
    assert "got 5 of 10 bytes" in msg


def test_full_download_returns_its_sha256(dl, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(dl.urllib.request, "urlopen", lambda *a, **k: _Stream(b"x" * 10))
    digest = dl.download_with_progress("https://example.invalid/x", tmp_path / "x", 10)
    assert digest == hashlib.sha256(b"x" * 10).hexdigest()
    assert (tmp_path / "x").read_bytes() == b"x" * 10


# --- leftover backup and odd index paths ----------------------------------

def test_leftover_backup_is_restored_when_index_missing(dl, monkeypatch, capsys):
    backup = dl.INDEX_ROOT.with_name(dl.INDEX_ROOT.name + ".old")
    backup.mkdir(parents=True)
    (backup / dl.INSTALLED_TAG_FILE).write_text("v1.0.0\n", encoding="utf-8")
    (backup / "old.txt").write_text("old", encoding="utf-8")
    monkeypatch.setattr(dl, "resolve_release", lambda tag: _release())
    assert dl.main([]) == 0  # restored index already holds v1.0.0
    assert "Restored the previous index" in capsys.readouterr().out
    assert (dl.INDEX_ROOT / "old.txt").exists()
    assert not backup.exists()


def test_leftover_backup_beside_index_is_never_deleted(dl, monkeypatch):
    dl.INDEX_ROOT.mkdir(parents=True)
    (dl.INDEX_ROOT / "current.txt").write_text("new", encoding="utf-8")
    backup = dl.INDEX_ROOT.with_name(dl.INDEX_ROOT.name + ".old")
    backup.mkdir()
    (backup / "old.txt").write_text("old", encoding="utf-8")
    monkeypatch.setattr(dl, "resolve_release", lambda tag: _release(digest="sha256:" + "a" * 64))

    def no_download(*a, **k):
        raise AssertionError("must not download while a backup is pending")

    monkeypatch.setattr(dl, "download_with_progress", no_download)
    with pytest.raises(SystemExit) as exc:
        dl.main(["--force"])
    msg = str(exc.value)
    assert msg.startswith("[FAIL]\tA previous index")
    assert str(backup) in msg
    assert (backup / "old.txt").exists()
    assert (dl.INDEX_ROOT / "current.txt").exists()


def test_install_never_deletes_leftover_backup(dl, tmp_path):
    dl.INDEX_ROOT.mkdir(parents=True)
    backup = dl.INDEX_ROOT.with_name(dl.INDEX_ROOT.name + ".old")
    backup.mkdir()
    (backup / "old.txt").write_text("old", encoding="utf-8")
    extracted = tmp_path / "extracted"
    extracted.mkdir()
    with pytest.raises(SystemExit):
        dl.install(extracted, dl.INDEX_ROOT, "v1.0.0")
    assert (backup / "old.txt").exists()


def test_install_keeps_local_usage_log_and_checkpoint(dl, tmp_path):
    """The token ledger must survive a download, or the free-tier check under-counts."""
    dl.INDEX_ROOT.mkdir(parents=True)
    (dl.INDEX_ROOT / "usage.log").write_text('{"tokens": 123}\n', encoding="utf-8")
    (dl.INDEX_ROOT / "embed-checkpoint.bin").write_bytes(b"\x01\x02")
    (dl.INDEX_ROOT / "old.txt").write_text("old", encoding="utf-8")
    extracted = tmp_path / "extracted"
    extracted.mkdir()
    (extracted / "manifest.json").write_text("{}", encoding="utf-8")
    (extracted / "usage.log").write_text('{"tokens": 999}\n', encoding="utf-8")
    dl.install(extracted, dl.INDEX_ROOT, "v1.0.0")
    assert (dl.INDEX_ROOT / "usage.log").read_text(encoding="utf-8") == '{"tokens": 123}\n'
    assert (dl.INDEX_ROOT / "embed-checkpoint.bin").read_bytes() == b"\x01\x02"
    assert not (dl.INDEX_ROOT / "old.txt").exists()
    assert not dl.INDEX_ROOT.with_name(dl.INDEX_ROOT.name + ".old").exists()


def test_leftover_staging_folder_is_replaced(dl, tmp_path):
    staging = dl.INDEX_ROOT.with_name(dl.INDEX_ROOT.name + ".new")
    staging.mkdir(parents=True)
    (staging / "stale.txt").write_text("stale", encoding="utf-8")
    extracted = tmp_path / "extracted"
    extracted.mkdir()
    (extracted / "manifest.json").write_text("{}", encoding="utf-8")
    dl.install(extracted, dl.INDEX_ROOT, "v1.0.0")
    assert (dl.INDEX_ROOT / "manifest.json").exists()
    assert not (dl.INDEX_ROOT / "stale.txt").exists()
    assert not staging.exists()


def test_index_path_that_is_a_file_fails_clearly(dl, monkeypatch):
    dl.INDEX_ROOT.parent.mkdir(parents=True)
    dl.INDEX_ROOT.write_text("not a folder", encoding="utf-8")
    monkeypatch.setattr(dl, "resolve_release", lambda tag: _release())
    with pytest.raises(SystemExit) as exc:
        dl.main([])
    msg = str(exc.value)
    assert msg.startswith("[FAIL]\t")
    assert "is a file, not a folder" in msg
    assert dl.INDEX_ROOT.read_text(encoding="utf-8") == "not a folder"
