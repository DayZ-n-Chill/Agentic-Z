from __future__ import annotations

import ast
from pathlib import Path

import pytest

from persistence_router import route_contract


SIMULATOR_MODULES = (
    "persistence_stream",
    "persistence_cf",
    "persistence_sidecar",
)


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def test_simulators_do_not_import_each_other() -> None:
    root = Path(__file__).parent

    for module_name in SIMULATOR_MODULES:
        imported = _imported_modules(root / f"{module_name}.py")
        forbidden = set(SIMULATOR_MODULES) - {module_name}
        assert imported.isdisjoint(forbidden)


@pytest.mark.parametrize(
    ("case_input", "expected"),
    (
        (
            {
                "data_attached_to_entity": True,
                "owns_entity": True,
                "survives_uninstall": False,
                "admin_inspectable": False,
            },
            "stream_vanilla",
        ),
        (
            {
                "data_attached_to_entity": True,
                "owns_entity": False,
                "survives_uninstall": False,
                "admin_inspectable": False,
            },
            "cf_modstorage",
        ),
        (
            {
                "data_attached_to_entity": True,
                "owns_entity": True,
                "survives_uninstall": True,
                "admin_inspectable": False,
            },
            "cf_modstorage",
        ),
        (
            {
                "data_attached_to_entity": False,
                "owns_entity": None,
                "survives_uninstall": False,
                "admin_inspectable": True,
            },
            "sidecar",
        ),
    ),
)
def test_router_selects_exactly_one_contract(
    case_input: dict[str, bool | None],
    expected: str,
) -> None:
    assert route_contract(**case_input) == expected


def test_ambiguous_request_never_uses_a_default_contract() -> None:
    assert (
        route_contract(
            data_attached_to_entity=None,
            owns_entity=None,
            survives_uninstall=None,
            admin_inspectable=None,
        )
        == "needs_clarification"
    )
