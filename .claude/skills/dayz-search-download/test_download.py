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
    with pytest.raises(OSError):
        dl.install(extracted, dl.INDEX_ROOT, "v1.0.0")
    assert (dl.INDEX_ROOT / "old.txt").exists()


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
