# CANDIDATE-43 ES-NONEXISTENT-METHOD (curated table). Calling a method that is
# verified ABSENT from the entire vanilla script tree compile-fails with
# `Undefined function`. Same class as ES-PROCESSDIRECTDAMAGE-DT-ALIAS
# (CANDIDATE-12) and the SetObjectTextureGlobal case (CANDIDATE-31): named
# symbol, empirically verified absent.
# Suppression: a mod that DECLARES the method itself (method definition with a
# body, recognized by find_method_regions) compiles fine -- the symbol is
# excluded for that file. Known limitation: a declaration living in another
# file of the same addon is not seen (file-scope suppression only).

import re

from shared.method_recognition import find_method_regions
from shared.vanilla_reference import VANILLA_NONEXISTENT_METHODS


ES_NONEXISTENT_METHOD_RULE_ID = "ES-NONEXISTENT-METHOD"


ES_NONEXISTENT_METHOD_RE = re.compile(
    r"\b(?P<sym>"
    + "|".join(sorted(VANILLA_NONEXISTENT_METHODS))
    + r")\s*\("
)


ES_NONEXISTENT_METHOD_MESSAGE = (
    "[FAIL] {rel_path} line {line}: `{sym}` does not exist in the vanilla "
    "script tree (0 occurrences, verified 2026-06-10) -> `Undefined function` "
    "compile fail. Fix: {fix}."
)


def check_es_nonexistent_method(stripped_source, rel_path):
    errors = []

    declared = {
        method["name"]
        for method in find_method_regions(stripped_source)
        if method["name"] in VANILLA_NONEXISTENT_METHODS
    }

    for match in ES_NONEXISTENT_METHOD_RE.finditer(stripped_source):
        sym = match.group("sym")
        if sym in declared:
            continue
        line_number = stripped_source.count("\n", 0, match.start()) + 1
        message = ES_NONEXISTENT_METHOD_MESSAGE.format(
            rel_path=rel_path,
            line=line_number,
            sym=sym,
            fix=VANILLA_NONEXISTENT_METHODS[sym],
        )
        errors.append(
            {
                "check": ES_NONEXISTENT_METHOD_RULE_ID,
                "file": rel_path,
                "line": line_number,
                "message": message,
                "severity": "FAIL",
                "rule_id": ES_NONEXISTENT_METHOD_RULE_ID,
            }
        )

    return errors
