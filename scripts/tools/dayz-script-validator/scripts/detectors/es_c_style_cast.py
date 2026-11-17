# QUARANTINED 2026-08-18 - not imported by script_validator.py and not executed.
# The premise is FALSE. C-style casts DO exist in Enforce Script and vanilla uses
# them in code that ships and compiles:
#   1_core/proto/proto.c:312    a = (int)h << 24;        (h is float, set at :310)
#   1_core/proto/enmath.c:110   (float)random_int / (float)max_range
#   3_game/entities/entityai.c:3207   ctx.Write((int)GetIsFrozen());
# Running this detector over the whole vanilla tree (2805 .c files) produced
# 73 findings, every one of them a false positive by construction. That breaks
# the project invariant: partial coverage may cost false negatives, never false
# positives.
#
# The claim came from a third-party tool's guide (ZeripeDaniel/Lake-Dayz-MCP,
# GPLv3 - knowledge only, no code or text adopted) and was adopted here without
# being checked against the vanilla tree. Do NOT re-wire it. `Math.Floor` returns
# float (enmath.c:427) and `.ToInt()` is string->int (enstring.c:20); neither is
# "the" conversion idiom, and the cast is not an error.
# Fixtures tests/fixtures/es/*c_style_cast* are kept as the record of what this
# used to assert.

import re


ES_C_STYLE_CAST_RULE_ID = "ES-C-STYLE-CAST"


# Enforce Script has no C-style cast. Forms `(int)x`, `(float)y`, `(bool)z`
# and `(string)w` do not compile. Conversion is `Math.Floor` / `Math.Round` /
# `.ToInt()` or string concatenation (`"" + n`).
#
# Runs on source that already had comments and string literals stripped, so a
# cast mentioned inside a literal or comment is not flagged.
#
# Parameter lists such as `void Foo(int x)` are not casts: the closing `)`
# must sit immediately after the type token, and the next token must be an
# identifier or an opening parenthesis. That rejects `(int x)` while still
# matching `(int)x` and `(int)(expr)`.
ES_C_STYLE_CAST_RE = re.compile(
    r"\(\s*(?P<type>int|float|bool|string)\s*\)\s*(?:[A-Za-z_]\w*|\()"
)


ES_C_STYLE_CAST_MESSAGE = (
    "[FAIL] {rel_path} line {line}: C-style cast `({type})`. Enforce Script "
    "has no C-style casts; the construct does not compile. Convert with "
    "Math.Floor / Math.Round / .ToInt() or string concatenation (`\"\" + n`)."
)


def check_es_c_style_cast(stripped_source, rel_path):
    errors = []

    for match in ES_C_STYLE_CAST_RE.finditer(stripped_source):
        line_number = stripped_source.count("\n", 0, match.start()) + 1
        message = ES_C_STYLE_CAST_MESSAGE.format(
            rel_path=rel_path,
            line=line_number,
            type=match.group("type"),
        )
        errors.append(
            {
                "check": ES_C_STYLE_CAST_RULE_ID,
                "file": rel_path,
                "line": line_number,
                "message": message,
                "severity": "FAIL",
                "rule_id": ES_C_STYLE_CAST_RULE_ID,
            }
        )

    return errors
