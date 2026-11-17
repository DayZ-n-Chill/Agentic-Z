# CANDIDATE-38 ES-METHOD-NAME-COLLIDES-VANILLA-CLASS (heuristic, curated table).
# Defining a method whose name is exactly a vanilla class name makes the
# compiler read call-sites `Name(args)` as a cast/constructor, not a call:
# "Too many parameters for 'Name' method" -> build broken.
# Source: origin: production mod bug ledger (BUG-003b, LogManager). Vanilla anchor
# verified: class LogManager at scripts/3_game/tools/debug.c:691.
# Heuristic: a curated table (vanilla_reference.VANILLA_GLOBAL_CLASS_NAMES)
# keeps false positives bounded; full vanilla-class coverage is out of scope.

from shared.method_recognition import find_method_regions
from shared.vanilla_reference import (
    is_vanilla_global_class_name,
    vanilla_global_class_citation,
)


ES_METHOD_NAME_COLLIDES_VANILLA_CLASS_RULE_ID = "ES-METHOD-NAME-COLLIDES-VANILLA-CLASS"


def check_es_method_name_collides_vanilla_class(stripped_source, rel_path):
    errors = []

    for method in find_method_regions(stripped_source):
        name = method["name"]
        if not is_vanilla_global_class_name(name):
            continue
        citation = vanilla_global_class_citation(name)
        message = (
            f"[FAIL] {rel_path} line {method['start_line']}: method '{name}' "
            f"collides with the vanilla class '{name}' ({citation}); the "
            f"compiler reads call-sites '{name}(...)' as a cast/constructor "
            f"-> \"Too many parameters for '{name}' method\", build broken. "
            f"Rename the method (origin: production mod bug ledger)."
        )
        errors.append(
            {
                "check": ES_METHOD_NAME_COLLIDES_VANILLA_CLASS_RULE_ID,
                "file": rel_path,
                "line": method["start_line"],
                "message": message,
                "severity": "FAIL",
                "rule_id": ES_METHOD_NAME_COLLIDES_VANILLA_CLASS_RULE_ID,
            }
        )

    return errors
