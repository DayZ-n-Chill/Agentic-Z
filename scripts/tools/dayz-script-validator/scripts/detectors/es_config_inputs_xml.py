import pathlib
import re


ES_INPUTS_XML_NOT_REGISTERED_RULE_ID = "CONFIG-INPUTS-XML-NOT-REGISTERED"


# kt_roadkill_armed bug-008/009. If an addon ships an inputs.xml (root
# <modded_inputs>), its `class CfgMods/<mod>` MUST declare
# `inputs = "<dir>\\inputs.xml";`. Without it the engine never loads the custom
# inputs and every UAxxx action of the mod is dead at runtime (latent: compiles
# and loads fine). Verified pattern: SimpleGroup/config.cpp:338,
# LBGroups_GPS/config.cpp:51.
_CFGMODS_RE = re.compile(r"^\s*class\s+CfgMods\b", re.MULTILINE)
_INPUTS_PROP_RE = re.compile(r"\binputs\s*=")


ES_INPUTS_XML_NOT_REGISTERED_MESSAGE = (
    "[FAIL] {rel_path} line {line}: addon ships an inputs.xml but `class "
    "CfgMods` does not declare an `inputs = \"<dir>/inputs.xml\";` property. "
    "Without it the engine never loads the custom inputs and all UAxxx actions "
    "are dead at runtime (latent bug)."
)


def detect_inputs_xml(addon_root):
    root = pathlib.Path(addon_root)
    base = root if root.is_dir() else root.parent
    try:
        for path in base.rglob("*.xml"):
            if not path.is_file():
                continue
            if path.name.lower() == "inputs.xml":
                return True
            try:
                if "<modded_inputs" in path.read_text(
                    encoding="utf-8", errors="ignore"
                ):
                    return True
            except OSError:
                continue
    except OSError:
        pass
    return False


def check_es_inputs_xml_registered(config_source, rel_path, inputs_xml_present):
    if not inputs_xml_present:
        return []

    cfgmods = _CFGMODS_RE.search(config_source)
    if not cfgmods:
        return []
    if _INPUTS_PROP_RE.search(config_source):
        return []

    line_number = config_source.count("\n", 0, cfgmods.start()) + 1
    return [
        {
            "check": ES_INPUTS_XML_NOT_REGISTERED_RULE_ID,
            "file": rel_path,
            "line": line_number,
            "message": ES_INPUTS_XML_NOT_REGISTERED_MESSAGE.format(
                rel_path=rel_path, line=line_number
            ),
            "severity": "FAIL",
            "rule_id": ES_INPUTS_XML_NOT_REGISTERED_RULE_ID,
        }
    ]


ES_INPUTS_XML_WRONG_ROOT_RULE_ID = "CONFIG-INPUTS-XML-WRONG-ROOT"


# First real XML element name. Skips the <?xml ...?> declaration ('?' is not in
# the leading char class) and <!-- comments --> ('!' likewise).
_XML_ROOT_ELEMENT_RE = re.compile(r"<\s*([A-Za-z_][\w.\-]*)")


ES_INPUTS_XML_WRONG_ROOT_MESSAGE = (
    "[FAIL] {rel_path} line {line}: inputs.xml root element is '<{root}>' but "
    "must be '<modded_inputs>'. With the wrong root the engine never loads the "
    "custom inputs and all UAxxx actions are dead at runtime (latent: no "
    "compile/load error)."
)


def check_es_inputs_xml_root(addon_root):
    root_path = pathlib.Path(addon_root)
    base = root_path if root_path.is_dir() else root_path.parent
    findings = []
    try:
        candidates = sorted(base.rglob("*.xml"))
    except OSError:
        return findings
    for path in candidates:
        if not path.is_file():
            continue
        if path.name.lower() != "inputs.xml":
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        match = _XML_ROOT_ELEMENT_RE.search(text)
        if not match:
            continue
        root_name = match.group(1)
        if root_name.lower() == "modded_inputs":
            continue
        line_number = text.count("\n", 0, match.start()) + 1
        try:
            rel = str(path.relative_to(base))
        except ValueError:
            rel = path.name
        findings.append(
            {
                "check": ES_INPUTS_XML_WRONG_ROOT_RULE_ID,
                "file": rel,
                "line": line_number,
                "message": ES_INPUTS_XML_WRONG_ROOT_MESSAGE.format(
                    rel_path=rel, root=root_name, line=line_number
                ),
                "severity": "FAIL",
                "rule_id": ES_INPUTS_XML_WRONG_ROOT_RULE_ID,
            }
        )
    return findings
