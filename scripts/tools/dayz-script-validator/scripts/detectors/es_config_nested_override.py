import re


ES_CONFIG_NESTED_OVERRIDE_RULE_ID = "ES-CONFIG-NESTED-OVERRIDE-NO-FORWARDREF"


# kt_roadkill_armed_dev bug-003. Overriding a nested vehicle class with explicit
# inheritance (`class SimulationModule: SimulationModule`) without forward-
# declaring the base (`class SimulationModule;`) in the config's own
# CfgVehicles root -> CfgConvert aborts with `Undefined base class 'X'`. Each
# config.cpp is parsed in its own scope and does not inherit forward-refs from
# the parent PBO.
NESTED_VEHICLE_CLASSES = {
    "SimulationModule", "Axles", "Front", "Rear", "Left", "Right", "Wheels",
    "DamageZones", "DamageSystem", "GlobalHealth", "Health", "Doors", "Window",
    "AnimationSources",
}

# Forward declaration: `class X;`
_FORWARD_RE = re.compile(r"^\s*class\s+(\w+)\s*;", re.MULTILINE)
# Root/plain definition WITHOUT inheritance: `class X {` (no `: base`).
_DEFINE_NO_INHERIT_RE = re.compile(r"^\s*class\s+(\w+)\s*\{", re.MULTILINE)
# Any inheritance use: `class X: Y`
_INHERIT_RE = re.compile(r"\bclass\s+(\w+)\s*:\s*(\w+)")


ES_CONFIG_NESTED_OVERRIDE_MESSAGE = (
    "[FAIL] {rel_path} line {line}: nested vehicle class '{name}' inherits from "
    "'{base}' but '{base}' is not forward-declared in this config. CfgConvert "
    "aborts with `Undefined base class '{base}'`. Add `class {base};` to the "
    "CfgVehicles root of this config."
)


def check_es_config_nested_override(config_source, rel_path):
    declared = set(_FORWARD_RE.findall(config_source))
    declared |= set(_DEFINE_NO_INHERIT_RE.findall(config_source))

    errors = []
    for match in _INHERIT_RE.finditer(config_source):
        name, base = match.group(1), match.group(2)
        if base in NESTED_VEHICLE_CLASSES and base not in declared:
            line_number = config_source.count("\n", 0, match.start()) + 1
            errors.append(
                {
                    "check": ES_CONFIG_NESTED_OVERRIDE_RULE_ID,
                    "file": rel_path,
                    "line": line_number,
                    "message": ES_CONFIG_NESTED_OVERRIDE_MESSAGE.format(
                        rel_path=rel_path, line=line_number, name=name, base=base
                    ),
                    "severity": "FAIL",
                    "rule_id": ES_CONFIG_NESTED_OVERRIDE_RULE_ID,
                }
            )
    return errors
