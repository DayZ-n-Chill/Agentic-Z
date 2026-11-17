from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import struct
from typing import BinaryIO, Iterable


_ENTRY_HEADER = struct.Struct("<5I")
_PRODUCT_VERS = 0x56657273
_STREAM_CHUNK_SIZE = 1024 * 1024
_Fingerprint = tuple[int, int, int, int]


class PboFormatError(ValueError):
    """The PBO or a requested closure input is unsafe or unsupported."""

    exit_code = 4


@dataclass(frozen=True)
class PboEntry:
    name: str
    packing: int
    original_size: int
    reserved: int
    timestamp: int
    data_size: int
    data_offset: int
    fingerprint: _Fingerprint


@dataclass(frozen=True)
class PboFinding:
    code: str
    path: str
    message: str
    source_sha256: str | None
    deployed_sha256: str | None


@dataclass(frozen=True)
class PboDigest:
    """Header properties and the SHA-256 of every entry payload, from one snapshot."""

    properties: tuple[tuple[str, str], ...]
    entries: tuple[tuple[PboEntry, str], ...]


def _read_asciiz(handle, context: str) -> str:
    value = bytearray()
    while True:
        byte = handle.read(1)
        if not byte:
            raise PboFormatError(f"truncated ASCIIZ while reading {context}")
        if byte == b"\x00":
            break
        value.extend(byte)
    try:
        return value.decode("ascii")
    except UnicodeDecodeError as error:
        raise PboFormatError(f"non-ASCII ASCIIZ while reading {context}") from error


def _read_entry_header(handle, context: str) -> tuple[int, int, int, int, int]:
    raw = handle.read(_ENTRY_HEADER.size)
    if len(raw) != _ENTRY_HEADER.size:
        raise PboFormatError(f"truncated entry header while reading {context}")
    return _ENTRY_HEADER.unpack(raw)


def _canonical_entry_name(name: str) -> tuple[str, str]:
    canonical = name.replace("/", "\\")
    if not canonical or canonical.startswith("\\"):
        raise PboFormatError(f"invalid PBO entry path: {name!r}")
    parts = canonical.split("\\")
    if any(part in ("", ".", "..") for part in parts):
        raise PboFormatError(f"invalid PBO entry path: {name!r}")
    if any(":" in part for part in parts) or any(
        ord(character) < 32 for character in canonical
    ):
        raise PboFormatError(f"invalid PBO entry path: {name!r}")
    return canonical, canonical.casefold()


def _fingerprint(stat_result: os.stat_result) -> _Fingerprint:
    return (
        stat_result.st_dev,
        stat_result.st_ino,
        stat_result.st_size,
        stat_result.st_mtime_ns,
    )


def _snapshot_fingerprint(pbo_path: Path, handle: BinaryIO) -> _Fingerprint:
    handle_fingerprint = _fingerprint(os.fstat(handle.fileno()))
    path_fingerprint = _fingerprint(pbo_path.stat())
    if path_fingerprint != handle_fingerprint:
        raise PboFormatError(f"PBO path changed while opening snapshot: {pbo_path}")
    return handle_fingerprint


def _require_unchanged_snapshot(
    pbo_path: Path, handle: BinaryIO, expected: _Fingerprint
) -> None:
    path_before = _fingerprint(pbo_path.stat())
    handle_fingerprint = _fingerprint(os.fstat(handle.fileno()))
    path_after = _fingerprint(pbo_path.stat())
    if (
        path_before != expected
        or handle_fingerprint != expected
        or path_after != expected
    ):
        raise PboFormatError(f"PBO snapshot changed while reading: {pbo_path}")


def _parse_pbo_handle(
    handle: BinaryIO,
    fingerprint: _Fingerprint,
    properties: list[tuple[str, str]] | None = None,
) -> tuple[PboEntry, ...]:
    handle.seek(0)
    raw_entries: list[tuple[str, int, int, int, int, int]] = []
    normalized_names: set[str] = set()
    while True:
        name = _read_asciiz(handle, "entry name")
        packing, original, reserved, timestamp, data_size = _read_entry_header(
            handle, name or "control entry"
        )
        if name == "":
            if packing == _PRODUCT_VERS:
                if (original, reserved, timestamp, data_size) != (0, 0, 0, 0):
                    raise PboFormatError(
                        "invalid PBO Vers control fields: "
                        f"{(original, reserved, timestamp, data_size)!r}"
                    )
                while True:
                    extension_name = _read_asciiz(
                        handle, "product extension name"
                    )
                    if extension_name == "":
                        break
                    extension_value = _read_asciiz(
                        handle, f"product extension value {extension_name!r}"
                    )
                    if properties is not None:
                        properties.append((extension_name, extension_value))
                continue
            if (packing, original, reserved, timestamp, data_size) == (
                0,
                0,
                0,
                0,
                0,
            ):
                data_start = handle.tell()
                break
            raise PboFormatError(
                "invalid empty PBO control fields: "
                f"{(packing, original, reserved, timestamp, data_size)!r}"
            )
        _, normalized = _canonical_entry_name(name)
        if normalized in normalized_names:
            raise PboFormatError(
                f"duplicate normalized PBO entry name: {name!r}"
            )
        normalized_names.add(normalized)
        raw_entries.append(
            (name, packing, original, reserved, timestamp, data_size)
        )

    entries = []
    offset = data_start
    for name, packing, original, reserved, timestamp, data_size in raw_entries:
        data_end = offset + data_size
        if data_end > fingerprint[2]:
            raise PboFormatError(
                f"PBO entry data range exceeds file size: {name!r} "
                f"[{offset}, {data_end}) > {fingerprint[2]}"
            )
        entries.append(
            PboEntry(
                name=name,
                packing=packing,
                original_size=original,
                reserved=reserved,
                timestamp=timestamp,
                data_size=data_size,
                data_offset=offset,
                fingerprint=fingerprint,
            )
        )
        offset = data_end
    return tuple(entries)


def parse_pbo(path: Path) -> tuple[PboEntry, ...]:
    """Parse the PBO header without loading the archive payload into memory."""
    pbo_path = Path(path)
    try:
        with pbo_path.open("rb") as handle:
            fingerprint = _snapshot_fingerprint(pbo_path, handle)
            entries = _parse_pbo_handle(handle, fingerprint)
            _require_unchanged_snapshot(pbo_path, handle, fingerprint)
            return entries
    except PboFormatError:
        raise
    except OSError as error:
        raise PboFormatError(f"cannot read PBO {pbo_path}: {error}") from error


def _require_uncompressed(entry: PboEntry) -> None:
    if entry.packing != 0:
        raise PboFormatError(
            f"compressed PBO entry is unsupported: {entry.name!r} "
            f"(packing=0x{entry.packing:08X})"
        )


def _read_entry_handle(handle: BinaryIO, entry: PboEntry) -> bytes:
    _require_uncompressed(entry)
    handle.seek(entry.data_offset)
    remaining = entry.data_size
    data = bytearray()
    while remaining:
        chunk = handle.read(min(remaining, _STREAM_CHUNK_SIZE))
        if not chunk:
            raise PboFormatError(f"truncated PBO entry data: {entry.name!r}")
        data.extend(chunk)
        remaining -= len(chunk)
    return bytes(data)


def _sha256_entry_handle(handle: BinaryIO, entry: PboEntry) -> str:
    _require_uncompressed(entry)
    handle.seek(entry.data_offset)
    remaining = entry.data_size
    digest = hashlib.sha256()
    while remaining:
        chunk = handle.read(min(remaining, _STREAM_CHUNK_SIZE))
        if not chunk:
            raise PboFormatError(f"truncated PBO entry data: {entry.name!r}")
        digest.update(chunk)
        remaining -= len(chunk)
    return digest.hexdigest()


def read_entry(path: Path, entry: PboEntry) -> bytes:
    """Return an uncompressed entry payload; compressed entries fail closed."""
    if not isinstance(entry, PboEntry):
        raise PboFormatError("requested PBO entry has an invalid descriptor")
    pbo_path = Path(path)
    try:
        with pbo_path.open("rb") as handle:
            fingerprint = _snapshot_fingerprint(pbo_path, handle)
            if entry.fingerprint != fingerprint:
                raise PboFormatError(
                    f"requested PBO entry belongs to a stale snapshot: {entry.name!r}"
                )
            entries = _parse_pbo_handle(handle, fingerprint)
            if entry not in entries:
                raise PboFormatError(
                    f"requested PBO entry descriptor is not in header: {entry.name!r}"
                )
            _require_unchanged_snapshot(pbo_path, handle, fingerprint)
            data = _read_entry_handle(handle, entry)
            _require_unchanged_snapshot(pbo_path, handle, fingerprint)
            return data
    except PboFormatError:
        raise
    except OSError as error:
        raise PboFormatError(f"cannot read PBO {pbo_path}: {error}") from error


def digest_pbo(path: Path) -> PboDigest:
    """Return the header properties and every entry's payload SHA-256.

    One snapshot: the header is parsed and each payload streamed from the same
    open handle, which must still match the path afterwards. After the last
    entry (or after the header when there are no entries) the file may end, or
    hold exactly 21 bytes starting with 0x00 (the SHA-1 trailer, not checked);
    any other leftover is refused. Properties keep their file order. A
    compressed entry fails closed, as in read_entry.
    """
    pbo_path = Path(path)
    properties: list[tuple[str, str]] = []
    try:
        with pbo_path.open("rb") as handle:
            fingerprint = _snapshot_fingerprint(pbo_path, handle)
            entries = _parse_pbo_handle(handle, fingerprint, properties)
            payload_end = (
                entries[-1].data_offset + entries[-1].data_size
                if entries
                else handle.tell()
            )
            leftover = fingerprint[2] - payload_end
            if leftover == 21:
                handle.seek(payload_end)
                first = handle.read(1)
                if first != b"\x00":
                    raise PboFormatError(
                        "PBO has 21 leftover bytes after the last entry "
                        "that do not start with 0x00"
                    )
            elif leftover != 0:
                raise PboFormatError(
                    f"PBO has {leftover} leftover bytes after the last entry "
                    "(accept none, or a 21-byte SHA-1 trailer starting with 0x00)"
                )
            _require_unchanged_snapshot(pbo_path, handle, fingerprint)
            hashed = tuple(
                (entry, _sha256_entry_handle(handle, entry)) for entry in entries
            )
            _require_unchanged_snapshot(pbo_path, handle, fingerprint)
            return PboDigest(properties=tuple(properties), entries=hashed)
    except PboFormatError:
        raise
    except OSError as error:
        raise PboFormatError(f"cannot read PBO {pbo_path}: {error}") from error


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(_STREAM_CHUNK_SIZE):
                digest.update(chunk)
    except OSError as error:
        raise PboFormatError(f"cannot hash source path {path}: {error}") from error
    return digest.hexdigest()


def _requested_sources(
    addon_root: Path, paths: Iterable[Path]
) -> list[tuple[str, str, Path]]:
    root = Path(addon_root)
    try:
        resolved_root = root.resolve(strict=True)
    except OSError as error:
        raise PboFormatError(f"addon_root is not accessible: {root}") from error
    if not resolved_root.is_dir():
        raise PboFormatError(f"addon_root is not a directory: {root}")

    requested: dict[str, tuple[str, str, Path]] = {}
    for raw_path in paths:
        source = Path(raw_path)
        if not source.is_file():
            raise PboFormatError(f"source path is not a file: {source}")
        try:
            resolved = source.resolve(strict=True)
            relative = resolved.relative_to(resolved_root)
        except (OSError, ValueError) as error:
            raise PboFormatError(
                f"source path escapes addon_root: {source}"
            ) from error
        canonical, normalized = _canonical_entry_name(str(relative))
        existing = requested.get(normalized)
        if existing is not None and existing[2] != resolved:
            raise PboFormatError(
                f"duplicate normalized source path: {canonical!r}"
            )
        requested[normalized] = (normalized, canonical, resolved)
    return [requested[key] for key in sorted(requested)]


def verify_paths_against_pbo(
    pbo: Path, addon_root: Path, paths: Iterable[Path]
) -> list[PboFinding]:
    """Compare exact source bytes with matching uncompressed PBO entries."""
    pbo_path = Path(pbo)
    findings = []
    try:
        with pbo_path.open("rb") as handle:
            fingerprint = _snapshot_fingerprint(pbo_path, handle)
            entries = _parse_pbo_handle(handle, fingerprint)
            by_name = {
                _canonical_entry_name(entry.name)[1]: entry for entry in entries
            }
            requested = _requested_sources(addon_root, paths)
            _require_unchanged_snapshot(pbo_path, handle, fingerprint)
            for normalized, canonical, source in requested:
                source_sha256 = _sha256_file(source)
                entry = by_name.get(normalized)
                if entry is None:
                    findings.append(
                        PboFinding(
                            code="PBO-ENTRY-MISSING",
                            path=canonical,
                            message=(
                                "required deployed PBO entry is missing: "
                                f"{canonical}"
                            ),
                            source_sha256=source_sha256,
                            deployed_sha256=None,
                        )
                    )
                    continue
                deployed_sha256 = _sha256_entry_handle(handle, entry)
                if deployed_sha256 != source_sha256:
                    findings.append(
                        PboFinding(
                            code="PBO-HASH-MISMATCH",
                            path=canonical,
                            message=(
                                "deployed PBO entry differs from source: "
                                f"{canonical}"
                            ),
                            source_sha256=source_sha256,
                            deployed_sha256=deployed_sha256,
                        )
                    )
            _require_unchanged_snapshot(pbo_path, handle, fingerprint)
    except PboFormatError:
        raise
    except OSError as error:
        raise PboFormatError(f"cannot read PBO {pbo_path}: {error}") from error
    return findings


def verify_deployed_closure(manifest, nodes: Iterable[object]) -> list[PboFinding]:
    """Verify the host and every reachable proxy against the deployed PBO."""
    paths = [Path(manifest.host_p3d)]
    paths.extend(Path(node.proxy_path) for node in nodes)
    return verify_paths_against_pbo(
        Path(manifest.deployed_pbo), Path(manifest.addon_root), paths
    )
