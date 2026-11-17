import re

from shared.dead_branches import dead_lines


ES_MODDED_ENGINE_CLASS_RULE_ID = "ES-MODDED-ENGINE-CLASS"


# claim: CLAIM-ENFORCE-MODDED-ENGINE-CLASS
# Some classes are declared by the engine and refuse `modded class`, and the
# whole script module stops compiling. Pipeline inbox fb-20261005-233046-89d1
# (SimpleGroup): `modded class Transport` in scripts/3_Game, DayZDiag
# 1.29.163709:
#
#   Can't compile "Game" script module!
#   .../lfpg_moddedtransport.c(9): Engine class 'Transport' cannot be modded.
#
# DayZDiag 1.30.164200 (StorageLogger, 2026-10-24), scripts/4_World, the
# server script log of two boots:
#
#   storagelogger.c,315: Engine class 'DayZPlayerInventory' cannot be modded.
#   storagelogger.c,432: Engine class 'Magazine' cannot be modded.
#   Can't compile "World" script module!
#
# Only classes measured in the engine are listed. Another engine class goes in
# only after a compile refuses it. To change a vehicle, mod the script bases in
# 4_World instead: CarScript (4_world/entities/vehicles/carscript.c:94 in 1.30;
# :170 was the 1.29 citation) or BoatScript (boatscript.c:41); for ammo piles,
# Ammunition_Base
# (4_world/entities/itembase/magazine/ammunitionpiles.c:2), which compiled
# modded in the same 1.30 build. DayZPlayerInventory has no script subclass:
# hook the item side (ItemBase.EEItemLocationChanged) instead.
#
# The refusal holds wherever the line compiles, so code under another mod's
# #ifdef is judged too; what never compiles (shared/dead_branches.py) is not.
ENGINE_CLASSES = ("Transport", "DayZPlayerInventory", "Magazine")

_MODDED_RE = re.compile(r"\bmodded\s+class\s+(?P<name>[A-Za-z_]\w*)")

ES_MODDED_ENGINE_CLASS_MESSAGE = (
    "[FAIL] {rel_path} line {line}: 'modded class {name}': {name} is an "
    "engine class and cannot be modded (\"Engine class '{name}' cannot be "
    "modded.\"); the script module does not compile. Mod a script class "
    "that derives from it instead (for vehicles, CarScript or BoatScript in "
    "4_World; for ammo piles, Ammunition_Base; for inventory moves, "
    "ItemBase.EEItemLocationChanged)."
)


def check_es_modded_engine_class(stripped_source, rel_path):
    errors = []
    dead = None
    for match in _MODDED_RE.finditer(stripped_source):
        name = match.group("name")
        if name not in ENGINE_CLASSES:
            continue
        line = stripped_source.count("\n", 0, match.start()) + 1
        if dead is None:
            dead = dead_lines(stripped_source)
        if line in dead:
            continue
        errors.append(
            {
                "check": ES_MODDED_ENGINE_CLASS_RULE_ID,
                "file": rel_path,
                "line": line,
                "message": ES_MODDED_ENGINE_CLASS_MESSAGE.format(
                    rel_path=rel_path, line=line, name=name
                ),
                "severity": "FAIL",
                "rule_id": ES_MODDED_ENGINE_CLASS_RULE_ID,
            }
        )
    return errors
