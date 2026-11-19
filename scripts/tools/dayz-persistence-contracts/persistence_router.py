from __future__ import annotations


CONTRACTS = {
    "stream_vanilla",
    "cf_modstorage",
    "sidecar",
}


def route_contract(
    *,
    data_attached_to_entity: bool | None,
    owns_entity: bool | None,
    survives_uninstall: bool | None,
    admin_inspectable: bool | None,
) -> str:
    candidates: set[str] = set()

    if data_attached_to_entity is False or admin_inspectable is True:
        candidates.add("sidecar")
    if owns_entity is False or survives_uninstall is True:
        candidates.add("cf_modstorage")
    if (
        data_attached_to_entity is True
        and owns_entity is True
        and survives_uninstall is False
        and admin_inspectable is False
    ):
        candidates.add("stream_vanilla")

    if len(candidates) != 1:
        return "needs_clarification"
    return candidates.pop()
