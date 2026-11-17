# CANDIDATE-41 ES-RESPAWN-EQUIP-IN-ONCLIENTRESPAWNEVENT (heuristic).
# `OnClientRespawnEvent(PlayerIdentity identity, PlayerBase player)` delivers
# the PRE-respawn character: vanilla only uses it to kill the unconscious or
# restrained player (missionserver.c:598-609, SetHealth("","",0.0) at :608).
# The NEW character is created later in OnClientNewEvent -> CreateCharacter
# (missionserver.c:536/:560/:576). Equipment/loadout logic wired here mutates
# the dying character: silent no-op or corruption, no error, no log.
# Source: origin: production mod bug ledger (GG-01, corruption Alta; LL-131 --
# eight auditors verified the event SIGNATURE, none verified the parameter
# SEMANTICS). Correct prior art: HM_Starter_Kit equips in OnClientNewEvent.
# Heuristic scope: only item-CREATION calls inside the method body are
# flagged (curated set below). Killing/logging the old character is the
# legitimate vanilla pattern and does not match.

import re

from shared.method_recognition import find_method_regions


ES_RESPAWN_EQUIP_RULE_ID = "ES-RESPAWN-EQUIP-IN-ONCLIENTRESPAWNEVENT"


ES_RESPAWN_EQUIP_METHOD_NAME = "OnClientRespawnEvent"

ES_RESPAWN_EQUIP_CALL_RE = re.compile(
    r"\b(?P<call>CreateInInventory|CreateAttachment|SpawnEntity)\s*\("
)


ES_RESPAWN_EQUIP_MESSAGE = (
    "[WARN] {rel_path} line {line}: `{call}` inside `OnClientRespawnEvent` -- "
    "this event delivers the PRE-respawn character (vanilla only kills the "
    "unconscious there, missionserver.c:598-609); the NEW character is "
    "created in `OnClientNewEvent` (missionserver.c:536). Equipment created "
    "here lands on the dying character: silent no-op/corruption (origin: production mod bug ledger). Move loadout logic to OnClientNewEvent."
)


def check_es_respawn_equip_onclientrespawn(stripped_source, rel_path):
    warnings = []
    lines = stripped_source.split("\n")

    for method in find_method_regions(stripped_source):
        if method["name"] != ES_RESPAWN_EQUIP_METHOD_NAME:
            continue
        body_start_index = method["brace_line"] - 1
        body_end_index = min(method["end_line"], len(lines))
        for index in range(body_start_index, body_end_index):
            for match in ES_RESPAWN_EQUIP_CALL_RE.finditer(lines[index]):
                line_number = index + 1
                message = ES_RESPAWN_EQUIP_MESSAGE.format(
                    rel_path=rel_path,
                    line=line_number,
                    call=match.group("call"),
                )
                warnings.append(
                    {
                        "check": ES_RESPAWN_EQUIP_RULE_ID,
                        "file": rel_path,
                        "line": line_number,
                        "message": message,
                        "severity": "WARN",
                        "rule_id": ES_RESPAWN_EQUIP_RULE_ID,
                    }
                )

    return warnings
