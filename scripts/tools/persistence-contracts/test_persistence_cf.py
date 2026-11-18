from __future__ import annotations

from persistence_cf import (
    CF_FRAMEWORK_VERSION,
    CFStorage,
    FRAMEWORK_HEADER_GAME_VERSION,
    LEGACY_GAME_VERSION_CUTOFF,
    MIN_FRAMEWORK_DATA_VERSION,
    ModData,
)


MODS = {"alpha", "beta", "gamma"}


def _three_mod_storage() -> CFStorage:
    storage = CFStorage(installed_mods=MODS)
    storage.set_mod_data("alpha", storage_version=2, payload=b"alpha-data")
    storage.set_mod_data("beta", storage_version=7, payload=b"beta-data\x00\xff")
    storage.set_mod_data("gamma", storage_version=1, payload=b"gamma-data")
    return storage


def test_uninstalled_mod_block_is_reemitted_byte_for_byte() -> None:
    first_frame = _three_mod_storage().save()
    first_load = CFStorage.load(
        first_frame,
        game_version=FRAMEWORK_HEADER_GAME_VERSION,
        installed_mods=MODS,
    )
    assert first_load.success is True
    assert first_load.storage is not None

    storage = first_load.storage
    unloaded_block = storage.raw_mod_block("beta")
    storage.set_installed_mods({"alpha", "gamma"})
    second_frame = storage.save()

    second_load = CFStorage.load(
        second_frame,
        game_version=FRAMEWORK_HEADER_GAME_VERSION,
        installed_mods={"alpha", "gamma"},
    )
    assert second_load.success is True
    assert second_load.storage is not None
    assert second_load.storage.raw_mod_block("beta") == unloaded_block
    assert second_load.storage.get_mod_data("beta") is None

    reinstall = CFStorage.load(
        second_frame,
        game_version=FRAMEWORK_HEADER_GAME_VERSION,
        installed_mods=MODS,
    )
    assert reinstall.success is True
    assert reinstall.storage is not None
    assert reinstall.storage.get_mod_data("beta") == ModData(
        storage_version=7,
        payload=b"beta-data\x00\xff",
    )


def test_game_version_below_116_has_no_cf_payload() -> None:
    result = CFStorage.load(
        b"bytes are outside the old contract",
        game_version=LEGACY_GAME_VERSION_CUTOFF - 1,
        installed_mods=MODS,
    )

    assert result.success is True
    assert result.bytes_consumed == 0
    assert result.framework_version is None
    assert result.storage is not None
    assert result.storage.mod_ids() == ()


def test_game_version_141_or_newer_reads_the_framework_header() -> None:
    frame = _three_mod_storage().save()

    result = CFStorage.load(
        frame,
        game_version=FRAMEWORK_HEADER_GAME_VERSION,
        installed_mods=MODS,
    )

    assert result.success is True
    assert result.framework_version == CF_FRAMEWORK_VERSION
    assert result.bytes_consumed == len(frame)
    assert result.storage is not None
    assert result.storage.get_mod_data("alpha") == ModData(
        storage_version=2,
        payload=b"alpha-data",
    )


def test_framework_version_below_2_short_circuits_before_mod_count() -> None:
    legacy_header_only = b"CFMS\x00\x01"

    result = CFStorage.load(
        legacy_header_only,
        game_version=FRAMEWORK_HEADER_GAME_VERSION,
        installed_mods=MODS,
    )

    assert result.success is True
    assert result.framework_version == MIN_FRAMEWORK_DATA_VERSION - 1
    assert result.bytes_consumed == len(legacy_header_only)
    assert result.storage is not None
    assert result.storage.mod_ids() == ()
