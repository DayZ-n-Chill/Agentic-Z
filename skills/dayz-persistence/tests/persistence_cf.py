from __future__ import annotations

import struct
from dataclasses import dataclass


CF_FRAMEWORK_VERSION = 5
LEGACY_GAME_VERSION_CUTOFF = 116
FRAMEWORK_HEADER_GAME_VERSION = 141
MIN_FRAMEWORK_DATA_VERSION = 2
MAGIC = b"CFMS"


@dataclass(frozen=True)
class ModData:
    storage_version: int
    payload: bytes


@dataclass(frozen=True)
class _ModRecord:
    data: ModData
    raw_block: bytes


@dataclass(frozen=True)
class CFLoadResult:
    success: bool
    storage: CFStorage | None
    bytes_consumed: int
    framework_version: int | None


class CFStorage:
    def __init__(self, installed_mods: set[str]) -> None:
        self._installed_mods = set(installed_mods)
        self._records: dict[str, _ModRecord] = {}
        self._order: list[str] = []

    @staticmethod
    def _encode_block(
        mod_id: str,
        storage_version: int,
        payload: bytes,
    ) -> bytes:
        encoded_id = mod_id.encode("utf-8")
        if len(encoded_id) > 0xFFFF:
            raise ValueError("mod id is too long")
        if isinstance(storage_version, bool) or not 0 <= storage_version <= 0xFFFFFFFF:
            raise ValueError("storage version must be an unsigned integer")
        return b"".join(
            (
                struct.pack(">H", len(encoded_id)),
                encoded_id,
                struct.pack(">I", storage_version),
                struct.pack(">I", len(payload)),
                payload,
            )
        )

    def set_mod_data(
        self,
        mod_id: str,
        *,
        storage_version: int,
        payload: bytes,
    ) -> None:
        raw_block = self._encode_block(mod_id, storage_version, payload)
        if mod_id not in self._records:
            self._order.append(mod_id)
        self._records[mod_id] = _ModRecord(
            ModData(storage_version, payload),
            raw_block,
        )

    def save(self) -> bytes:
        blocks = [self._records[mod_id].raw_block for mod_id in self._order]
        return b"".join(
            (
                MAGIC,
                struct.pack(">H", CF_FRAMEWORK_VERSION),
                struct.pack(">H", len(blocks)),
                *blocks,
            )
        )

    @classmethod
    def load(
        cls,
        payload: bytes,
        *,
        game_version: int,
        installed_mods: set[str],
    ) -> CFLoadResult:
        empty = cls(installed_mods)
        if game_version < LEGACY_GAME_VERSION_CUTOFF:
            return CFLoadResult(True, empty, 0, None)
        if game_version < FRAMEWORK_HEADER_GAME_VERSION:
            return CFLoadResult(True, empty, 0, 1)

        if len(payload) < 6 or payload[:4] != MAGIC:
            return CFLoadResult(False, None, 0, None)
        framework_version = struct.unpack(">H", payload[4:6])[0]
        position = 6
        if framework_version < MIN_FRAMEWORK_DATA_VERSION:
            return CFLoadResult(
                True,
                empty,
                position,
                framework_version,
            )
        if position + 2 > len(payload):
            return CFLoadResult(False, None, 0, framework_version)

        mod_count = struct.unpack(">H", payload[position : position + 2])[0]
        position += 2
        staged: list[tuple[str, _ModRecord]] = []
        seen: set[str] = set()
        for _ in range(mod_count):
            block_start = position
            if position + 2 > len(payload):
                return CFLoadResult(False, None, 0, framework_version)
            id_length = struct.unpack(">H", payload[position : position + 2])[0]
            position += 2
            id_end = position + id_length
            if id_end + 8 > len(payload):
                return CFLoadResult(False, None, 0, framework_version)
            try:
                mod_id = payload[position:id_end].decode("utf-8")
            except UnicodeDecodeError:
                return CFLoadResult(False, None, 0, framework_version)
            position = id_end
            storage_version = struct.unpack(">I", payload[position : position + 4])[0]
            position += 4
            data_length = struct.unpack(">I", payload[position : position + 4])[0]
            position += 4
            data_end = position + data_length
            if data_end > len(payload) or mod_id in seen:
                return CFLoadResult(False, None, 0, framework_version)
            data = payload[position:data_end]
            position = data_end
            seen.add(mod_id)
            staged.append(
                (
                    mod_id,
                    _ModRecord(
                        ModData(storage_version, data),
                        payload[block_start:position],
                    ),
                )
            )

        if position != len(payload):
            return CFLoadResult(False, None, 0, framework_version)
        storage = cls(installed_mods)
        for mod_id, record in staged:
            storage._order.append(mod_id)
            storage._records[mod_id] = record
        return CFLoadResult(
            True,
            storage,
            position,
            framework_version,
        )

    def raw_mod_block(self, mod_id: str) -> bytes:
        return self._records[mod_id].raw_block

    def set_installed_mods(self, installed_mods: set[str]) -> None:
        self._installed_mods = set(installed_mods)

    def get_mod_data(self, mod_id: str) -> ModData | None:
        if mod_id not in self._installed_mods:
            return None
        record = self._records.get(mod_id)
        return record.data if record is not None else None

    def mod_ids(self) -> tuple[str, ...]:
        return tuple(self._order)
