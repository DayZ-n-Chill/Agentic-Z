from __future__ import annotations

import pytest

from persistence_stream import (
    EntityState,
    StreamReader,
    StreamWriter,
    load_entity,
    save_entity,
)


BUILD_VERSION = 1290163451
ENERGY_FIELDS = (1, 2, 3, 4, 5, 6, 7, 8)


def test_typed_stream_is_sequential_and_failed_reads_do_not_advance() -> None:
    writer = StreamWriter(version=BUILD_VERSION)
    writer.write_int(17)
    writer.write_bool(True)
    writer.write_float(1.25)
    writer.write_string("state")
    reader = StreamReader(writer.to_bytes())

    before = reader.position
    wrong_type_ok, wrong_type_value = reader.read_bool()

    assert wrong_type_ok is False
    assert wrong_type_value is None
    assert reader.position == before
    assert reader.version == BUILD_VERSION
    assert reader.read_int() == (True, 17)
    assert reader.read_bool() == (True, True)
    float_ok, float_value = reader.read_float()
    assert float_ok is True
    assert float_value == pytest.approx(1.25)
    assert reader.read_string() == (True, "state")
    assert reader.at_end is True


def test_fixed_super_width_misaligns_when_optional_component_is_absent() -> None:
    present_payload = save_entity(
        version=BUILD_VERSION,
        energy_fields=ENERGY_FIELDS,
        child_value=73,
    )
    present_target = EntityState(energy_fields=None, child_value=-1)

    present_result = load_entity(
        present_payload,
        component_present=True,
        target=present_target,
        assume_fixed_super_width=True,
    )

    assert present_result.success is True
    assert present_target.child_value == 73

    absent_payload = save_entity(
        version=BUILD_VERSION,
        energy_fields=None,
        child_value=73,
    )
    absent_target = EntityState(energy_fields=ENERGY_FIELDS, child_value=-1)

    absent_result = load_entity(
        absent_payload,
        component_present=False,
        target=absent_target,
        assume_fixed_super_width=True,
    )

    assert absent_result.success is False
    assert absent_result.bytes_consumed == len(absent_payload)
    assert absent_target == EntityState(
        energy_fields=ENERGY_FIELDS,
        child_value=-1,
    )


@pytest.mark.parametrize(
    "energy_fields",
    (ENERGY_FIELDS, None),
)
def test_sequential_load_tracks_the_runtime_super_width(
    energy_fields: tuple[int, ...] | None,
) -> None:
    payload = save_entity(
        version=BUILD_VERSION,
        energy_fields=energy_fields,
        child_value=41,
    )
    target = EntityState(energy_fields=ENERGY_FIELDS, child_value=-1)

    result = load_entity(
        payload,
        component_present=energy_fields is not None,
        target=target,
        assume_fixed_super_width=False,
    )

    assert result.success is True
    assert result.version == BUILD_VERSION
    assert result.bytes_consumed == len(payload)
    assert target == EntityState(
        energy_fields=energy_fields,
        child_value=41,
    )


def test_failed_typed_read_discards_every_staged_field() -> None:
    payload = save_entity(
        version=BUILD_VERSION,
        energy_fields=ENERGY_FIELDS,
        child_value=99,
    )
    truncated = payload[:-2]
    initial = EntityState(energy_fields=None, child_value=7)

    result = load_entity(
        truncated,
        component_present=True,
        target=initial,
        assume_fixed_super_width=False,
    )

    assert result.success is False
    assert initial == EntityState(energy_fields=None, child_value=7)
