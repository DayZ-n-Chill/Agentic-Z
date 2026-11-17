# QUARANTINED 2026-08-18 - not imported by script_validator.py and not executed.
# The premise is FALSE. `delete` is real Enforce API and vanilla uses it in code
# that ships: 125 findings over the 2805-file vanilla tree, every one a false
# positive by construction. Bohemia's own proto DEMANDS it:
#   1_core/proto/envisual.c:47
#     //! WARNING: Non-managed, needs manual delete call, should not be ref'd
# and the tree does exactly that -
#   4_world/classes/camerashake.c:44      delete this;
#   2_gamelib/entities/rendertarget.c:46  delete m_RenderWidget;   (~RenderTarget)
#   4_world/entities/manbase/playerbase.c:2512  delete m_HologramServer;
# For a non-managed widget or BoneMask, `obj = null` is not a substitute: it
# hides the symptom and keeps the leak.
#
# The real hazard, if there is one, is `delete` on a Managed/ref TYPE - not the
# keyword. To re-wire: produce a segfault repro for one concrete Managed type and
# write a detector that matches type x delete, not the word. A regex over the
# keyword cannot separate the illegal case from the 125 legal ones.

import re


ES_NO_DELETE_RULE_ID = "ES-NO-DELETE"


ES_NO_DELETE_RE = re.compile(r"\bdelete\s+\w")


ES_NO_DELETE_MESSAGE = (
    "[FAIL] {rel_path} line {line}: 'delete' keyword used. Enforce Script uses "
    "ARC garbage collection; 'delete' on live object causes segfault (SKILL.md "
    "rule 14, memory-management.md:82). Replace with 'obj = null;'."
)


def check_es_no_delete(stripped_source, rel_path):
    errors = []

    for match in ES_NO_DELETE_RE.finditer(stripped_source):
        line_number = stripped_source.count("\n", 0, match.start()) + 1
        message = ES_NO_DELETE_MESSAGE.format(rel_path=rel_path, line=line_number)
        errors.append(
            {
                "check": ES_NO_DELETE_RULE_ID,
                "file": rel_path,
                "line": line_number,
                "message": message,
                "severity": "FAIL",
                "rule_id": ES_NO_DELETE_RULE_ID,
            }
        )

    return errors
