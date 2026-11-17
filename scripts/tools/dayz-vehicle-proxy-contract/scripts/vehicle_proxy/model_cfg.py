from __future__ import annotations

from pathlib import Path
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET


class ModelCfgError(ValueError):
    """CfgConvert could not produce trustworthy model.cfg evidence."""


def parse_animation_xml_text(text: str) -> dict[str, tuple[str, ...]]:
    if type(text) is not str:
        raise ModelCfgError("CfgConvert XML must be text")
    without_declaration = re.sub(
        r"^\s*<\?xml[^>]*\?>", "", text, count=1, flags=re.IGNORECASE
    )
    try:
        root = ET.fromstring(f"<root>{without_declaration}</root>")
    except ET.ParseError as error:
        raise ModelCfgError(f"invalid CfgConvert XML: {error}") from error
    children = list(root)
    if not children:
        raise ModelCfgError("invalid CfgConvert XML: no root elements")
    if root.text is not None and root.text.strip():
        raise ModelCfgError("invalid CfgConvert XML: text outside root elements")
    if any(child.tail is not None and child.tail.strip() for child in children):
        raise ModelCfgError("invalid CfgConvert XML: text outside root elements")
    top_level_tags = [child.tag for child in children]
    allowed_top_level_tags = {"CfgSkeletons", "CfgModels"}
    if any(tag not in allowed_top_level_tags for tag in top_level_tags):
        raise ModelCfgError("invalid CfgConvert XML: unexpected top-level element")
    if "CfgModels" not in top_level_tags:
        raise ModelCfgError("invalid CfgConvert XML: missing CfgModels")

    animations_by_selection: dict[str, list[str]] = {}
    for animations in root.iter("Animations"):
        for animation in list(animations):
            selection = animation.findtext("selection")
            if selection is None or not selection.strip():
                continue
            normalized = selection.strip().lower()
            animations_by_selection.setdefault(normalized, []).append(animation.tag)
    return {
        selection: tuple(animation_classes)
        for selection, animation_classes in animations_by_selection.items()
    }


def _command_evidence(
    command: list[str], completed: subprocess.CompletedProcess[str]
) -> str:
    return (
        f"command={command!r}; exit={completed.returncode}; "
        f"stdout={completed.stdout!r}; stderr={completed.stderr!r}"
    )


def convert_model_cfg(
    model_cfg: Path, cfgconvert: Path
) -> dict[str, tuple[str, ...]]:
    model_cfg = Path(model_cfg)
    cfgconvert = Path(cfgconvert)
    if not model_cfg.is_file():
        raise ModelCfgError(f"model.cfg does not exist: {model_cfg}")
    if not cfgconvert.is_file():
        raise ModelCfgError(f"CfgConvert executable does not exist: {cfgconvert}")

    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary) / "model.xml"
        command = [
            str(cfgconvert),
            "-xml",
            "-dst",
            str(output),
            str(model_cfg),
        ]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                errors="replace",
                check=False,
            )
        except OSError as error:
            raise ModelCfgError(
                f"CfgConvert could not start; command={command!r}: {error}"
            ) from error
        evidence = _command_evidence(command, completed)
        if completed.returncode != 0:
            raise ModelCfgError(
                f"CfgConvert failed with exit {completed.returncode}; {evidence}"
            )
        if not output.is_file():
            raise ModelCfgError(f"CfgConvert did not create output; {evidence}")
        try:
            xml_text = output.read_text(encoding="iso-8859-1")
        except OSError as error:
            raise ModelCfgError(
                f"CfgConvert output could not be read; {evidence}"
            ) from error
        try:
            return parse_animation_xml_text(xml_text)
        except ModelCfgError as error:
            raise ModelCfgError(
                f"CfgConvert output was invalid; {evidence}; {error}"
            ) from error
