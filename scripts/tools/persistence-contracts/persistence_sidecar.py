from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass


RECORD_MAGIC = b"SCAR"
RECORD_HEADER_SIZE = 12
READ_LIMIT = 100_000_000


@dataclass
class _OpenHandle:
    path: str
    mode: str
    position: int = 0


class MemoryFileSystem:
    def __init__(self, initial: dict[str, bytes] | None = None) -> None:
        self._files = dict(initial or {})
        self._directories: set[str] = set()
        self._handles: dict[int, _OpenHandle] = {}
        self._next_handle = 1
        self._truncate_next_copy = False

    def file_exist(self, path: str) -> bool:
        return path in self._files

    def open_file(self, path: str, mode: str) -> int:
        if mode == "r" and path not in self._files:
            return 0
        if mode not in {"r", "w"}:
            return 0
        if mode == "w":
            self._files[path] = b""
        handle = self._next_handle
        self._next_handle += 1
        self._handles[handle] = _OpenHandle(path, mode)
        return handle

    def read_file(self, handle: int, length: int) -> tuple[bool, bytes]:
        opened = self._handles.get(handle)
        if opened is None or opened.mode != "r" or length < 0:
            return False, b""
        payload = self._files.get(opened.path)
        if payload is None:
            return False, b""
        end = min(opened.position + length, len(payload))
        chunk = payload[opened.position:end]
        opened.position = end
        return True, chunk

    def close_file(self, handle: int) -> bool:
        return self._handles.pop(handle, None) is not None

    def fprint(self, handle: int, value: bytes | str) -> bool:
        opened = self._handles.get(handle)
        if opened is None or opened.mode != "w":
            return False
        encoded = value.encode("utf-8") if isinstance(value, str) else value
        current = self._files.get(opened.path, b"")
        prefix = current[: opened.position]
        suffix_start = opened.position + len(encoded)
        suffix = current[suffix_start:] if suffix_start < len(current) else b""
        self._files[opened.path] = prefix + encoded + suffix
        opened.position += len(encoded)
        return True

    def fgets(self, handle: int) -> tuple[bool, str]:
        opened = self._handles.get(handle)
        if opened is None or opened.mode != "r":
            return False, ""
        payload = self._files.get(opened.path)
        if payload is None:
            return False, ""
        newline = payload.find(b"\n", opened.position)
        end = len(payload) if newline < 0 else newline + 1
        chunk = payload[opened.position:end]
        opened.position = end
        try:
            return True, chunk.decode("utf-8")
        except UnicodeDecodeError:
            return False, ""

    def make_directory(self, path: str) -> bool:
        self._directories.add(path)
        return True

    def delete_file(self, path: str) -> bool:
        return self._files.pop(path, None) is not None

    def copy_file(self, source: str, destination: str) -> bool:
        payload = self._files.get(source)
        if payload is None:
            return False
        if self._truncate_next_copy:
            payload = payload[:-1]
            self._truncate_next_copy = False
        self._files[destination] = bytes(payload)
        return True


@dataclass(frozen=True)
class MigrationResult:
    verdict: str
    bytes_consumed: int
    state_preserved: str
    action: str
    applied_state: dict[str, str] | None
    version_read: int | None
    version_expected: int


class MigrationReader:
    def __init__(
        self,
        *,
        current_version: int,
        initial_state: dict[str, str] | None = None,
    ) -> None:
        self.current_version = current_version
        self.logs: list[str] = []
        self.state = dict(initial_state or {})
        self._logged_windows: set[tuple[str, str]] = set()

    def _log_future_once(self, window: str) -> None:
        key = (window, "future-version")
        if key not in self._logged_windows:
            self._logged_windows.add(key)
            self.logs.append("degradation: future mod version rejected")

    def _result(
        self,
        verdict: str,
        bytes_consumed: int,
        state_preserved: str,
        action: str,
        *,
        applied_state: dict[str, str] | None = None,
        version_read: int | None = None,
    ) -> MigrationResult:
        return MigrationResult(
            verdict,
            bytes_consumed,
            state_preserved,
            action,
            applied_state,
            version_read,
            self.current_version,
        )

    def read(self, payload: bytes, *, window: str) -> MigrationResult:
        if payload == b"FRESH":
            return self._result(
                "ok",
                0,
                "defaults",
                "write current header",
            )
        if payload.startswith(b"LEGACY:") and len(payload) > 7:
            value = payload[7:].decode("utf-8", errors="strict")
            applied = {"value": value}
            self.state = dict(applied)
            return self._result(
                "ok_legacy",
                len(payload),
                "fully migrated",
                "read legacy, write new after backup",
                applied_state=applied,
            )
        if not payload.startswith(RECORD_MAGIC):
            return self._result(
                "reject_invalid",
                0,
                "intact",
                "preserve evidence",
            )
        if len(payload) < RECORD_HEADER_SIZE:
            return self._result(
                "reject",
                0,
                "intact",
                "discard partial; preserve evidence",
            )

        version, minimum_reader, _game_build, data_length = struct.unpack(
            ">BBIH",
            payload[4:RECORD_HEADER_SIZE],
        )
        if len(payload) != RECORD_HEADER_SIZE + data_length:
            return self._result(
                "reject",
                0,
                "intact",
                "discard partial; preserve evidence",
                version_read=version,
            )
        if minimum_reader > self.current_version:
            return self._result(
                "reject_forward",
                0,
                "intact",
                "old reader rejects; do not delete",
                version_read=version,
            )
        if version > self.current_version:
            self._log_future_once(window)
            return self._result(
                "reject",
                0,
                "intact",
                "do not write; log rate-limited",
                version_read=version,
            )

        try:
            value = payload[RECORD_HEADER_SIZE:].decode("utf-8")
        except UnicodeDecodeError:
            return self._result(
                "reject_invalid",
                0,
                "intact",
                "preserve evidence",
                version_read=version,
            )
        applied = {"value": value}
        self.state = dict(applied)
        if version < self.current_version:
            return self._result(
                "ok_migrate",
                len(payload),
                "migrated",
                "migrate by mod version, not game build",
                applied_state=applied,
                version_read=version,
            )
        return self._result(
            "ok",
            len(payload),
            "complete",
            "none",
            applied_state=applied,
            version_read=version,
        )


@dataclass(frozen=True)
class IOResult:
    success: bool
    action: str
    evidence: tuple[str, ...]
    applied_state: bytes | None


class SidecarStore:
    _FAULTS = {
        "open",
        "read",
        "parse",
        "backup",
        "temp-write",
        "temp-verify",
        "replace",
        "post-copy-verify",
    }

    def __init__(
        self,
        fs: MemoryFileSystem,
        fault: str | None = None,
    ) -> None:
        if fault is not None and fault not in self._FAULTS:
            raise ValueError("unknown fault boundary")
        self._fs = fs
        self._fault = fault

    @staticmethod
    def _record_valid(payload: bytes) -> bool:
        if len(payload) < RECORD_HEADER_SIZE or payload[:4] != RECORD_MAGIC:
            return False
        data_length = struct.unpack(">H", payload[10:12])[0]
        return len(payload) == RECORD_HEADER_SIZE + data_length

    @staticmethod
    def _temp_path(destination: str) -> str:
        return f"{destination}.tmp"

    @staticmethod
    def _backup_path(destination: str) -> str:
        return f"{destination}.bak"

    @staticmethod
    def _hash_path(destination: str) -> str:
        return f"{destination}.sha256"

    def _read_all(self, path: str) -> tuple[bool, bytes]:
        handle = self._fs.open_file(path, "r")
        if handle == 0:
            return False, b""
        ok, payload = self._fs.read_file(handle, READ_LIMIT)
        closed = self._fs.close_file(handle)
        return ok and closed, payload

    def _write_all(self, path: str, payload: bytes) -> bool:
        handle = self._fs.open_file(path, "w")
        if handle == 0:
            return False
        written = self._fs.fprint(handle, payload)
        closed = self._fs.close_file(handle)
        return written and closed

    def _evidence(self, *paths: str) -> tuple[str, ...]:
        return tuple(path for path in paths if self._fs.file_exist(path))

    def _write_hash_sidecar(self, destination: str, payload: bytes) -> bool:
        digest = hashlib.sha256(payload).hexdigest().encode("ascii") + b"\n"
        return self._write_all(self._hash_path(destination), digest)

    def load(self, destination: str) -> IOResult:
        evidence = self._evidence(destination)
        handle = (
            0
            if self._fault == "open"
            else self._fs.open_file(destination, "r")
        )
        if handle == 0:
            return IOResult(False, "open_failed", evidence, None)

        ok, payload = self._fs.read_file(handle, READ_LIMIT)
        closed = self._fs.close_file(handle)
        if self._fault == "read":
            payload = payload[: len(payload) // 2]
            ok = False
        if not ok or not closed:
            return IOResult(False, "read_failed", evidence, None)
        if self._fault == "parse" or not self._record_valid(payload):
            return IOResult(False, "parse_failed", evidence, None)
        return IOResult(True, "loaded", evidence, payload)

    def save(self, destination: str, payload: bytes) -> IOResult:
        temp = self._temp_path(destination)
        backup = self._backup_path(destination)

        if self._fault == "temp-write":
            self._write_all(temp, payload[: len(payload) // 2])
            self._fs.delete_file(temp)
            return IOResult(
                False,
                "temp_write_failed",
                self._evidence(destination),
                None,
            )
        if not self._write_all(temp, payload):
            return IOResult(
                False,
                "temp_write_failed",
                self._evidence(destination, temp),
                None,
            )

        temp_ok, temp_payload = self._read_all(temp)
        if (
            self._fault == "temp-verify"
            or not temp_ok
            or temp_payload != payload
            or not self._record_valid(temp_payload)
        ):
            return IOResult(
                False,
                "temp_verify_failed",
                self._evidence(destination, temp),
                None,
            )

        if self._fs.file_exist(destination):
            if self._fault == "backup" or not self._fs.copy_file(
                destination,
                backup,
            ):
                return IOResult(
                    False,
                    "backup_failed",
                    self._evidence(destination, temp),
                    None,
                )
            if not self._fs.delete_file(destination):
                return IOResult(
                    False,
                    "replace_failed",
                    self._evidence(destination, temp, backup),
                    None,
                )

        if self._fault == "replace":
            return IOResult(
                False,
                "replace_failed",
                self._evidence(temp, backup),
                None,
            )
        if self._fault == "post-copy-verify":
            self._fs._truncate_next_copy = True
        if not self._fs.copy_file(temp, destination):
            return IOResult(
                False,
                "replace_failed",
                self._evidence(temp, backup),
                None,
            )

        copied_ok, copied_payload = self._read_all(destination)
        if (
            not copied_ok
            or copied_payload != payload
            or not self._record_valid(copied_payload)
        ):
            self._fs.delete_file(destination)
            return IOResult(
                False,
                "post_copy_verify_failed",
                self._evidence(destination, temp, backup),
                None,
            )
        if not self._write_hash_sidecar(destination, payload):
            return IOResult(
                False,
                "sidecar_write_failed",
                self._evidence(destination, temp, backup),
                None,
            )
        if not self._fs.delete_file(temp):
            return IOResult(
                False,
                "temp_cleanup_failed",
                self._evidence(destination, temp, backup),
                None,
            )
        return IOResult(
            True,
            "saved",
            self._evidence(
                destination,
                self._hash_path(destination),
                backup,
            ),
            payload,
        )

    def recover_orphan(self, destination: str) -> IOResult:
        temp = self._temp_path(destination)
        backup = self._backup_path(destination)
        temp_ok, payload = self._read_all(temp)
        if not temp_ok or not self._record_valid(payload):
            return IOResult(
                False,
                "preserved_truncated_tmp",
                self._evidence(temp),
                None,
            )

        if self._fs.file_exist(destination):
            if not self._fs.copy_file(destination, backup):
                return IOResult(
                    False,
                    "orphan_backup_failed",
                    self._evidence(destination, temp),
                    None,
                )
            if not self._fs.delete_file(destination):
                return IOResult(
                    False,
                    "orphan_replace_failed",
                    self._evidence(destination, temp, backup),
                    None,
                )
        if self._fault == "post-copy-verify":
            self._fs._truncate_next_copy = True
        if not self._fs.copy_file(temp, destination):
            return IOResult(
                False,
                "orphan_replace_failed",
                self._evidence(temp, backup),
                None,
            )
        copied_ok, copied_payload = self._read_all(destination)
        if (
            not copied_ok
            or copied_payload != payload
            or not self._record_valid(copied_payload)
        ):
            self._fs.delete_file(destination)
            return IOResult(
                False,
                "orphan_verify_failed",
                self._evidence(destination, temp, backup),
                None,
            )
        if not self._write_hash_sidecar(destination, payload):
            return IOResult(
                False,
                "sidecar_write_failed",
                self._evidence(destination, temp, backup),
                None,
            )
        if not self._fs.delete_file(temp):
            return IOResult(
                False,
                "temp_cleanup_failed",
                self._evidence(destination, temp, backup),
                None,
            )
        return IOResult(
            True,
            "promoted_valid_tmp",
            self._evidence(
                destination,
                self._hash_path(destination),
                backup,
            ),
            payload,
        )
