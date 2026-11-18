"""Read a .pbo's header: its properties, its entry table and its checksum trailer.

A PBO is a header (one record per packed file), the files' bytes in the same
order, then a 21-byte trailer: one zero byte and the SHA-1 of everything before
it. This module reads the header and checks the trailer. It never unpacks or
decompresses an entry, so it works on any PBO, binarized or not.

Used by build.py (is the mod's source really in the PBO it just built?) and by
dayz-import-mod/pbo_inventory.py (what is in a PBO somebody else built?).
"""
from __future__ import annotations

import hashlib
import struct
from pathlib import Path
from typing import BinaryIO, NamedTuple, Optional

VERS_MAGIC = 0x56657273  # "Vers": the first record, which carries the header properties
CPRS_MAGIC = 0x43707273  # "Cprs": an entry stored compressed
TRAILER_SIZE = 21        # one zero byte + a 20-byte SHA-1
_RECORD = struct.Struct("<5I")  # packing method, original size, reserved, timestamp, data size
_MAX_NAME = 1024


class PboError(ValueError):
    """The file is not a PBO this reader understands."""


class PboEntry(NamedTuple):
    name: str           # as stored: backslash separators, relative to the prefix
    packing: int        # 0 for stored bytes, CPRS_MAGIC for a compressed entry
    original_size: int  # unpacked size of a compressed entry, else 0
    timestamp: int
    data_size: int      # bytes the entry takes in the file
    offset: int         # where those bytes start

    @property
    def compressed(self) -> bool:
        return self.packing == CPRS_MAGIC

    @property
    def key(self) -> str:
        """The name in the form used to compare entries: lower case, backslashes."""
        return self.name.replace("/", "\\").lower()


class Pbo:
    """One PBO's header: path, properties (in file order), entries, and the trailer verdict."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.properties: dict[str, str] = {}
        self.entries: list[PboEntry] = []
        # True when the last 21 bytes are a zero byte and the SHA-1 of the rest; None when not checked.
        self.trailer_ok: Optional[bool] = None

    @property
    def prefix(self) -> str:
        return self.properties.get("prefix", "")

    def names(self) -> set[str]:
        return {e.key for e in self.entries}


def _read_cstring(f: BinaryIO, what: str) -> str:
    raw = bytearray()
    while True:
        byte = f.read(1)
        if not byte:
            raise PboError(f"the file ends inside {what}")
        if byte == b"\x00":
            # Entry names from old tools can be cp1252; latin-1 decodes any byte.
            return raw.decode("latin-1")
        raw += byte
        if len(raw) > _MAX_NAME:
            raise PboError(f"{what} is longer than {_MAX_NAME} bytes, so this is not a PBO header")


def _trailer_ok(f: BinaryIO, size: int) -> bool:
    if size <= TRAILER_SIZE:
        return False
    digest = hashlib.sha1()
    f.seek(0)
    left = size - TRAILER_SIZE
    while left:
        chunk = f.read(min(left, 1 << 20))
        if not chunk:
            return False
        digest.update(chunk)
        left -= len(chunk)
    trailer = f.read(TRAILER_SIZE)
    return trailer[:1] == b"\x00" and trailer[1:] == digest.digest()


def read_pbo(path: Path, check_trailer: bool = True) -> Pbo:
    """Read the header of the PBO at path. Raises PboError when it is malformed.

    check_trailer hashes the whole file once; pass False for a quick listing of a
    very large PBO.
    """
    path = Path(path)
    size = path.stat().st_size
    pbo = Pbo(path=path)
    with path.open("rb") as f:
        first = True
        sizes: list[tuple[str, int, int, int, int]] = []
        while True:
            name = _read_cstring(f, "an entry name")
            record = f.read(_RECORD.size)
            if len(record) != _RECORD.size:
                raise PboError("the file ends inside the entry table")
            packing, original_size, _reserved, timestamp, data_size = _RECORD.unpack(record)
            if not name and packing == VERS_MAGIC:
                if not first:
                    raise PboError("a second properties record inside the entry table")
                while True:
                    key = _read_cstring(f, "a header property")
                    if not key:
                        break
                    pbo.properties[key] = _read_cstring(f, f"the value of header property {key!r}")
            elif not name:
                break  # the empty record that closes the entry table
            else:
                sizes.append((name, packing, original_size, timestamp, data_size))
            first = False
        offset = f.tell()
        for name, packing, original_size, timestamp, data_size in sizes:
            pbo.entries.append(PboEntry(name, packing, original_size, timestamp, data_size, offset))
            offset += data_size
        if offset > size:
            raise PboError(f"the entry table names {offset - size} more bytes than the file holds (truncated PBO)")
        if check_trailer:
            pbo.trailer_ok = _trailer_ok(f, size)
    return pbo


def read_entry(pbo: Pbo, entry: PboEntry) -> bytes:
    """The stored bytes of one entry (still compressed when entry.compressed)."""
    with pbo.path.open("rb") as f:
        f.seek(entry.offset)
        return f.read(entry.data_size)
