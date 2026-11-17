from __future__ import annotations

import struct
from dataclasses import dataclass


MAGIC = b"VSTR"
HEADER_SIZE = 8
ENERGY_FIELD_COUNT = 8


@dataclass
class EntityState:
    energy_fields: tuple[int, ...] | None
    child_value: int


@dataclass(frozen=True)
class LoadResult:
    success: bool
    bytes_consumed: int
    version: int | None


class StreamWriter:
    def __init__(self, version: int) -> None:
        if isinstance(version, bool) or not 0 <= version <= 0xFFFFFFFF:
            raise ValueError("version must be an unsigned build integer")
        self.version = version
        self._buffer = bytearray(MAGIC + struct.pack(">I", version))

    def write_int(self, value: int) -> None:
        self._buffer.extend(b"i" + struct.pack(">q", value))

    def write_bool(self, value: bool) -> None:
        self._buffer.extend(b"b" + (b"\x01" if value else b"\x00"))

    def write_float(self, value: float) -> None:
        self._buffer.extend(b"f" + struct.pack(">d", value))

    def write_string(self, value: str) -> None:
        encoded = value.encode("utf-8")
        self._buffer.extend(b"s" + struct.pack(">I", len(encoded)) + encoded)

    def to_bytes(self) -> bytes:
        return bytes(self._buffer)


class StreamReader:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload
        self._valid = len(payload) >= HEADER_SIZE and payload[:4] == MAGIC
        self.version = (
            struct.unpack(">I", payload[4:HEADER_SIZE])[0]
            if self._valid
            else None
        )
        self.position = HEADER_SIZE if self._valid else 0

    @property
    def at_end(self) -> bool:
        return self._valid and self.position == len(self._payload)

    def _read_fixed(
        self,
        expected_tag: bytes,
        size: int,
        format_code: str,
    ) -> tuple[bool, object | None]:
        start = self.position
        end = start + 1 + size
        if (
            not self._valid
            or end > len(self._payload)
            or self._payload[start : start + 1] != expected_tag
        ):
            return False, None
        value = struct.unpack(
            format_code,
            self._payload[start + 1 : end],
        )[0]
        self.position = end
        return True, value

    def read_int(self) -> tuple[bool, int | None]:
        ok, value = self._read_fixed(b"i", 8, ">q")
        return ok, value if isinstance(value, int) else None

    def read_bool(self) -> tuple[bool, bool | None]:
        start = self.position
        ok, value = self._read_fixed(b"b", 1, ">B")
        if not ok or value not in (0, 1):
            self.position = start
            return False, None
        return True, value == 1

    def read_float(self) -> tuple[bool, float | None]:
        ok, value = self._read_fixed(b"f", 8, ">d")
        return ok, value if isinstance(value, float) else None

    def read_string(self) -> tuple[bool, str | None]:
        start = self.position
        if (
            not self._valid
            or start + 5 > len(self._payload)
            or self._payload[start : start + 1] != b"s"
        ):
            return False, None
        length = struct.unpack(">I", self._payload[start + 1 : start + 5])[0]
        end = start + 5 + length
        if end > len(self._payload):
            return False, None
        try:
            value = self._payload[start + 5 : end].decode("utf-8")
        except UnicodeDecodeError:
            return False, None
        self.position = end
        return True, value


def save_entity(
    *,
    version: int,
    energy_fields: tuple[int, ...] | None,
    child_value: int,
) -> bytes:
    if energy_fields is not None and len(energy_fields) != ENERGY_FIELD_COUNT:
        raise ValueError("the optional component writes exactly eight fields")
    writer = StreamWriter(version)
    if energy_fields is not None:
        for value in energy_fields:
            writer.write_int(value)
    writer.write_int(child_value)
    return writer.to_bytes()


def load_entity(
    payload: bytes,
    *,
    component_present: bool,
    target: EntityState,
    assume_fixed_super_width: bool,
) -> LoadResult:
    reader = StreamReader(payload)
    if reader.version is None:
        return LoadResult(False, reader.position, None)

    energy_count = (
        ENERGY_FIELD_COUNT
        if component_present or assume_fixed_super_width
        else 0
    )
    staged_energy: list[int] = []
    for _ in range(energy_count):
        ok, value = reader.read_int()
        if not ok or value is None:
            return LoadResult(False, reader.position, reader.version)
        staged_energy.append(value)

    child_ok, child_value = reader.read_int()
    if not child_ok or child_value is None or not reader.at_end:
        return LoadResult(False, reader.position, reader.version)

    target.energy_fields = (
        tuple(staged_energy) if component_present else None
    )
    target.child_value = child_value
    return LoadResult(True, reader.position, reader.version)
