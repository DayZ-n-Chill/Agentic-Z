# QUARANTINED 2026-08-18 - not imported by script_validator.py and not executed.
# The premise is FALSE. `DT_*` is not "only a comment in object.c": the same tree
# CALLS it, in shipped code with no #ifdef -
#   3_game/entities/entityai.c:4103
#     ProcessDirectDamage(DT_CUSTOM, transport, "", "TransportHit", "0 0 0", damage);
# and again at :4130 and :4141 inside RegisterTransportHit. The comment the
# detector cited as proof of absence is the proto documentation for the parameter
# (object.c:1126, "@param damageType DT_CLOSE_COMBAT/DT_FIRE_ARM/DT_EXPLOSION/DT_CUSTOM").
# There is no local #define that would rescue those three calls, so DT_CUSTOM
# resolves for real or EntityAI would not compile.
#
# DamageType.CUSTOM also exists (damagesystem.c:16). Both spellings being valid is
# not a defect. To re-wire: show Workbench rejecting `e.ProcessDirectDamage(DT_CUSTOM, ...)`
# with Undefined AND explain why entityai.c:4103 is not in that compilation.

import re


ES_DT_ALIAS_RULE_ID = "ES-PROCESSDIRECTDAMAGE-DT-ALIAS"


# kt_roadkill_armed_dev bug-002. The `DT_*` identifiers are NOT vanilla symbols
# in current DayZ (they appear only in a comment in object.c:1126). The real
# argument is the `DamageType` enum (damagesystem.c:10-17), e.g.
# `DamageType.FIRE_ARM`. Using `DT_FIRE_ARM` etc. compile-fails with `Undefined`.
ES_DT_ALIAS_RE = re.compile(
    r"\bDT_(?P<sym>FIRE_ARM|CLOSE_COMBAT|EXPLOSION|STUN|CUSTOM)\b"
)


# Suppression: a mod that defines its own alias (`#define DT_FIRE_ARM ...`)
# compiles fine. Detect such defines and exclude the matching symbol.
ES_DT_ALIAS_DEFINE_RE = re.compile(
    r"^\s*#\s*define\s+DT_(?P<sym>FIRE_ARM|CLOSE_COMBAT|EXPLOSION|STUN|CUSTOM)\b",
    re.MULTILINE,
)


ES_DT_ALIAS_MESSAGE = (
    "[FAIL] {rel_path} line {line}: `DT_{sym}` is not a vanilla symbol "
    "(only appears in an object.c comment). Use the enum `DamageType.{sym}` "
    "instead (damagesystem.c:10-17)."
)


def check_es_dt_alias(stripped_source, rel_path):
    errors = []

    defined = {
        match.group("sym")
        for match in ES_DT_ALIAS_DEFINE_RE.finditer(stripped_source)
    }

    for match in ES_DT_ALIAS_RE.finditer(stripped_source):
        sym = match.group("sym")
        if sym in defined:
            continue
        line_number = stripped_source.count("\n", 0, match.start()) + 1
        message = ES_DT_ALIAS_MESSAGE.format(
            rel_path=rel_path, line=line_number, sym=sym
        )
        errors.append(
            {
                "check": ES_DT_ALIAS_RULE_ID,
                "file": rel_path,
                "line": line_number,
                "message": message,
                "severity": "FAIL",
                "rule_id": ES_DT_ALIAS_RULE_ID,
            }
        )

    return errors
