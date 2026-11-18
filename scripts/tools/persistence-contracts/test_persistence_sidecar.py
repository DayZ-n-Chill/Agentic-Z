from __future__ import annotations

from persistence_sidecar import MemoryFileSystem, SidecarStore


DESTINATION = "profile/state.dat"
TEMP = f"{DESTINATION}.tmp"
BACKUP = f"{DESTINATION}.bak"
HASH_SIDECAR = f"{DESTINATION}.sha256"
ORIGINAL = b"SCAR\x02\x01\x00\x00\x00\x81\x00\x03old"
REPLACEMENT = b"SCAR\x02\x01\x00\x00\x00\x81\x00\x03new"


def _read_bytes(fs: MemoryFileSystem, path: str) -> bytes | None:
    if not fs.file_exist(path):
        return None
    handle = fs.open_file(path, "r")
    assert handle != 0
    ok, payload = fs.read_file(handle, 1_000_000)
    assert ok is True
    assert fs.close_file(handle) is True
    return payload


def _assert_original_or_recovery_evidence(fs: MemoryFileSystem) -> None:
    if _read_bytes(fs, DESTINATION) == ORIGINAL:
        return
    assert _read_bytes(fs, TEMP) == REPLACEMENT
    assert _read_bytes(fs, BACKUP) == ORIGINAL


def test_memory_fs_exposes_only_dayz_file_primitives() -> None:
    public_methods = {
        name
        for name in dir(MemoryFileSystem)
        if not name.startswith("_")
        and callable(getattr(MemoryFileSystem, name))
    }

    assert public_methods == {
        "file_exist",
        "open_file",
        "read_file",
        "close_file",
        "fprint",
        "fgets",
        "make_directory",
        "delete_file",
        "copy_file",
    }
    assert "rename" not in public_methods
    assert "move" not in public_methods


def test_open_failure_keeps_the_original_intact() -> None:
    fs = MemoryFileSystem({DESTINATION: ORIGINAL})

    result = SidecarStore(fs, fault="open").load(DESTINATION)

    assert result.success is False
    assert result.action == "open_failed"
    assert result.applied_state is None
    assert result.evidence == (DESTINATION,)
    _assert_original_or_recovery_evidence(fs)


def test_read_failure_never_applies_partial_state() -> None:
    fs = MemoryFileSystem({DESTINATION: ORIGINAL})

    result = SidecarStore(fs, fault="read").load(DESTINATION)

    assert result.success is False
    assert result.action == "read_failed"
    assert result.applied_state is None
    assert result.evidence == (DESTINATION,)
    _assert_original_or_recovery_evidence(fs)


def test_parse_failure_preserves_the_original_as_evidence() -> None:
    fs = MemoryFileSystem({DESTINATION: ORIGINAL})

    result = SidecarStore(fs, fault="parse").load(DESTINATION)

    assert result.success is False
    assert result.action == "parse_failed"
    assert result.applied_state is None
    assert result.evidence == (DESTINATION,)
    _assert_original_or_recovery_evidence(fs)


def test_backup_failure_stops_before_replace() -> None:
    fs = MemoryFileSystem({DESTINATION: ORIGINAL})

    result = SidecarStore(fs, fault="backup").save(
        DESTINATION,
        REPLACEMENT,
    )

    assert result.success is False
    assert result.action == "backup_failed"
    assert result.evidence == (DESTINATION, TEMP)
    _assert_original_or_recovery_evidence(fs)


def test_temp_write_failure_leaves_the_original_intact() -> None:
    fs = MemoryFileSystem({DESTINATION: ORIGINAL})

    result = SidecarStore(fs, fault="temp-write").save(
        DESTINATION,
        REPLACEMENT,
    )

    assert result.success is False
    assert result.action == "temp_write_failed"
    assert result.evidence == (DESTINATION,)
    _assert_original_or_recovery_evidence(fs)


def test_temp_verify_failure_conserves_tmp_evidence() -> None:
    fs = MemoryFileSystem({DESTINATION: ORIGINAL})

    result = SidecarStore(fs, fault="temp-verify").save(
        DESTINATION,
        REPLACEMENT,
    )

    assert result.success is False
    assert result.action == "temp_verify_failed"
    assert result.evidence == (DESTINATION, TEMP)
    assert _read_bytes(fs, TEMP) == REPLACEMENT
    _assert_original_or_recovery_evidence(fs)


def test_replace_window_keeps_tmp_and_backup_recoverable() -> None:
    fs = MemoryFileSystem({DESTINATION: ORIGINAL})

    result = SidecarStore(fs, fault="replace").save(
        DESTINATION,
        REPLACEMENT,
    )

    assert result.success is False
    assert result.action == "replace_failed"
    assert _read_bytes(fs, DESTINATION) is None
    assert result.evidence == (TEMP, BACKUP)
    _assert_original_or_recovery_evidence(fs)


def test_post_copy_verify_detects_truncation_and_keeps_tmp() -> None:
    fs = MemoryFileSystem({DESTINATION: ORIGINAL})

    result = SidecarStore(fs, fault="post-copy-verify").save(
        DESTINATION,
        REPLACEMENT,
    )

    assert result.success is False
    assert result.action == "post_copy_verify_failed"
    assert _read_bytes(fs, DESTINATION) is None
    assert _read_bytes(fs, TEMP) == REPLACEMENT
    assert result.evidence == (TEMP, BACKUP)
    _assert_original_or_recovery_evidence(fs)


def test_orphan_tmp_policy_promotes_only_verified_content_without_mtime() -> None:
    valid_fs = MemoryFileSystem({TEMP: REPLACEMENT})

    valid = SidecarStore(valid_fs).recover_orphan(DESTINATION)

    assert valid.success is True
    assert valid.action == "promoted_valid_tmp"
    assert _read_bytes(valid_fs, DESTINATION) == REPLACEMENT
    assert _read_bytes(valid_fs, TEMP) is None
    assert _read_bytes(valid_fs, HASH_SIDECAR) is not None

    truncated_fs = MemoryFileSystem({TEMP: REPLACEMENT[:-1]})

    truncated = SidecarStore(truncated_fs).recover_orphan(DESTINATION)

    assert truncated.success is False
    assert truncated.action == "preserved_truncated_tmp"
    assert _read_bytes(truncated_fs, DESTINATION) is None
    assert _read_bytes(truncated_fs, TEMP) == REPLACEMENT[:-1]
    assert truncated.evidence == (TEMP,)


def test_orphan_verify_failure_removes_destination_and_keeps_evidence() -> None:
    fs = MemoryFileSystem(
        {
            DESTINATION: ORIGINAL,
            TEMP: REPLACEMENT,
        }
    )

    result = SidecarStore(fs, fault="post-copy-verify").recover_orphan(
        DESTINATION
    )

    assert result.success is False
    assert result.action == "orphan_verify_failed"
    assert _read_bytes(fs, DESTINATION) is None
    assert _read_bytes(fs, TEMP) == REPLACEMENT
    assert _read_bytes(fs, BACKUP) == ORIGINAL
    _assert_original_or_recovery_evidence(fs)
