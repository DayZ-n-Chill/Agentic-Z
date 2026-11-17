import re


ES_REGISTERRECIPES_TYPO_RULE_ID = "ES-REGISTERRECIPES-TYPO"


# CANDIDATE-42. The real recipe-registration hook carries an official typo:
# `RegisterRecipies()` (double i) -- declared at pluginrecipesmanagerbase.c:14,
# invoked at pluginrecipesmanager.c:655. The correctly-spelled form
# `RegisterRecipes` has 0 occurrences in the vanilla tree (verified 2026-06-10,
# host-side grep). Consequences of writing the correct spelling:
#   (a) `override ... RegisterRecipes(` -> compile fail (no base method).
#   (b) plain definition or call -> legal dead method the engine never invokes;
#       the mod's recipes are silently not registered.
# `RegisterRecipies` (double i) never matches these patterns: the substring
# after `RegisterRecip` differs (`es(` vs `ies(`).
ES_REGISTERRECIPES_RE = re.compile(r"\bRegisterRecipes\s*\(")

ES_REGISTERRECIPES_OVERRIDE_RE = re.compile(
    r"\boverride\s+[\w\s]*?\bRegisterRecipes\s*\("
)


ES_REGISTERRECIPES_FAIL_MESSAGE = (
    "[FAIL] {rel_path} line {line}: `override RegisterRecipes` -- the vanilla "
    "hook is `RegisterRecipies()` (official typo, double i; "
    "pluginrecipesmanagerbase.c:14). `RegisterRecipes` does not exist in the "
    "base class, so this override does not compile."
)

ES_REGISTERRECIPES_WARN_MESSAGE = (
    "[WARN] {rel_path} line {line}: `RegisterRecipes` -- the vanilla hook is "
    "`RegisterRecipies()` (official typo, double i; "
    "pluginrecipesmanagerbase.c:14, called at pluginrecipesmanager.c:655). A "
    "correctly-spelled `RegisterRecipes` is a dead method the engine never "
    "calls: the mod's recipes are silently not registered."
)


def check_es_registerrecipes_typo(stripped_source, rel_path):
    errors = []
    warnings = []

    override_spans = [
        (match.start(), match.end())
        for match in ES_REGISTERRECIPES_OVERRIDE_RE.finditer(stripped_source)
    ]

    for match in ES_REGISTERRECIPES_RE.finditer(stripped_source):
        line_number = stripped_source.count("\n", 0, match.start()) + 1
        is_override = any(
            start <= match.start() < end for start, end in override_spans
        )
        if is_override:
            message = ES_REGISTERRECIPES_FAIL_MESSAGE.format(
                rel_path=rel_path, line=line_number
            )
            errors.append(
                {
                    "check": ES_REGISTERRECIPES_TYPO_RULE_ID,
                    "file": rel_path,
                    "line": line_number,
                    "message": message,
                    "severity": "FAIL",
                    "rule_id": ES_REGISTERRECIPES_TYPO_RULE_ID,
                }
            )
        else:
            message = ES_REGISTERRECIPES_WARN_MESSAGE.format(
                rel_path=rel_path, line=line_number
            )
            warnings.append(
                {
                    "check": ES_REGISTERRECIPES_TYPO_RULE_ID,
                    "file": rel_path,
                    "line": line_number,
                    "message": message,
                    "severity": "WARN",
                    "rule_id": ES_REGISTERRECIPES_TYPO_RULE_ID,
                }
            )

    return errors, warnings
