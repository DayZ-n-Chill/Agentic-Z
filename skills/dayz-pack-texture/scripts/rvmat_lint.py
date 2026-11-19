#!/usr/bin/env python3
"""Lightweight DayZ .rvmat linter.

The linter is intentionally conservative: it reports common mistakes without
pretending that every vanilla divergence is invalid.

Pure offline script: it reads the .rvmat files it is given (and a companion .emat
next to one) and prints findings. It does not run /dayz-preflight. With
--pdrive-root it also checks that each texture path exists under that folder, and
says so itself when the folder is missing (for example P: not mounted).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path


BAD_TEXTURE_EXTS = {".png", ".tga", ".jpg", ".jpeg", ".dds", ".psd"}

# Shader IDs known to legitimately ship with zero Stage blocks for reasons unrelated to
# MatPBR (e.g. "Normal" is the flat vertex-lit shader). Excluded from the MatPBR-companion
# stub heuristic so linting a normal vanilla-pattern material stays quiet.
NO_STAGE_LEGITIMATE_SHADERS = {"normal"}
MATPBR_REQUIRED_MAPS = ("AlbedoMap", "NormalMap", "RoughnessMap", "MetalnessMap", "AOMap")
RESOURCE_ID_RE = re.compile(r'^\s*\{[0-9A-Fa-f]{6,}\}')


@dataclass
class Finding:
    file: str
    line: int
    severity: str
    code: str
    message: str


def line_at(text: str, offset: int) -> int:
    return text.count("\n", 0, max(0, offset)) + 1


def find_class_blocks(text: str, prefixes: tuple[str, ...]) -> dict[str, dict[str, object]]:
    blocks: dict[str, dict[str, object]] = {}
    for match in re.finditer(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)\b", text):
        name = match.group(1)
        if not name.startswith(prefixes):
            continue
        open_index = text.find("{", match.end())
        if open_index == -1:
            continue
        depth = 0
        close_index = None
        for index in range(open_index, len(text)):
            char = text[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    close_index = index
                    break
        if close_index is None:
            continue
        blocks[name] = {
            "body": text[open_index + 1 : close_index],
            "line": line_at(text, match.start()),
            "offset": match.start(),
            "body_offset": open_index + 1,
        }
    return blocks


def string_value(text: str, name: str) -> str | None:
    match = re.search(rf'\b{name}\s*=\s*"([^"]*)"\s*;', text, re.IGNORECASE)
    return match.group(1) if match else None


def top_string_value(text: str, name: str) -> str | None:
    match = re.search(rf"^\s*{name}\s*=\s*\"([^\"]*)\"\s*;", text, re.IGNORECASE | re.MULTILINE)
    return match.group(1) if match else None


def resolve_packed_path(texture: str, pdrive_root: Path | None) -> Path | None:
    if not pdrive_root or texture.startswith("#"):
        return None
    normalized = texture.replace("/", "\\").lstrip("\\")
    if ":" in normalized or normalized.startswith("\\\\"):
        return None
    parts = [part for part in normalized.split("\\") if part]
    if not parts:
        return None
    root_parts = [part for part in pdrive_root.parts if part not in ("\\", "/")]
    if root_parts and parts and root_parts[-1].rstrip("\\").lower() == parts[0].lower():
        parts = parts[1:]
    candidate = pdrive_root
    for part in parts:
        candidate = candidate / part
    return candidate


def add(
    findings: list[Finding],
    file_path: str,
    line: int,
    severity: str,
    code: str,
    message: str,
) -> None:
    findings.append(Finding(file_path, line, severity, code, message))


def lint_text(text: str, file_path: str, pdrive_root: Path | None = None) -> list[Finding]:
    findings: list[Finding] = []
    pixel = top_string_value(text, "PixelShaderID")
    vertex = top_string_value(text, "VertexShaderID")
    surface_info = top_string_value(text, "surfaceInfo")

    if not pixel:
        add(findings, file_path, 1, "ERROR", "MISSING_PIXEL_SHADER", "Missing PixelShaderID.")
    if not vertex:
        add(findings, file_path, 1, "ERROR", "MISSING_VERTEX_SHADER", "Missing VertexShaderID.")

    if surface_info and not surface_info.lower().endswith(".bisurf"):
        add(findings, file_path, 1, "WARN", "SURFACEINFO_NOT_BISURF", "surfaceInfo should normally point to a .bisurf file.")

    stage_blocks = find_class_blocks(text, ("Stage",))
    texgen_blocks = find_class_blocks(text, ("TexGen",))

    stages: dict[int, dict[str, object]] = {}
    for name, block in stage_blocks.items():
        number_match = re.match(r"Stage(\d+)$", name)
        if not number_match:
            continue
        number = int(number_match.group(1))
        body = str(block["body"])
        texture_match = re.search(r'texture\s*=\s*"([^"]*)"\s*;', body, re.IGNORECASE)
        stages[number] = {
            "name": name,
            "body": body,
            "line": int(block["line"]),
            "texture": texture_match.group(1) if texture_match else None,
            "texture_line": line_at(text, int(block["body_offset"]) + texture_match.start()) if texture_match else int(block["line"]),
            "uvSource": string_value(body, "uvSource"),
            "texGen": string_value(body, "texGen"),
        }

    texgens: dict[str, dict[str, object]] = {}
    for name, block in texgen_blocks.items():
        body = str(block["body"])
        texgens[name.replace("TexGen", "")] = {
            "body": body,
            "line": int(block["line"]),
            "uvSource": string_value(body, "uvSource"),
        }

    for stage_num, stage in sorted(stages.items()):
        texture = stage.get("texture")
        if not texture:
            add(findings, file_path, int(stage["line"]), "WARN", "STAGE_WITHOUT_TEXTURE", f"Stage{stage_num} has no texture field.")
            continue
        texture_str = str(texture)
        texture_line = int(stage["texture_line"])
        if ":" in texture_str or texture_str.startswith("\\\\"):
            add(findings, file_path, texture_line, "ERROR", "ABSOLUTE_TEXTURE_PATH", "Texture path must be a packed game path, not an absolute/local path.")
        if "/" in texture_str and not texture_str.startswith("#"):
            add(findings, file_path, texture_line, "WARN", "FORWARD_SLASH_PATH", "Use packed backslash paths in rvmat texture references.")
        suffix = Path(texture_str.replace("\\", "/")).suffix.lower()
        if suffix in BAD_TEXTURE_EXTS:
            add(findings, file_path, texture_line, "ERROR", "SOURCE_TEXTURE_EXT", f"RVMAT references source texture extension {suffix}; use final .paa.")
        resolved = resolve_packed_path(texture_str, pdrive_root)
        if resolved is not None and not resolved.exists():
            add(findings, file_path, texture_line, "WARN", "TEXTURE_NOT_FOUND", f"Texture path was not found under {pdrive_root}: {texture_str}")

    pixel_l = (pixel or "").lower()
    vertex_l = (vertex or "").lower()

    if pixel_l == "super":
        if vertex_l != "super":
            add(findings, file_path, 1, "ERROR", "SUPER_VERTEX_MISMATCH", "PixelShaderID Super should normally pair with VertexShaderID Super.")
        stage1 = stages.get(1)
        if not stage1:
            add(findings, file_path, 1, "WARN", "SUPER_MISSING_STAGE1", "Super material has no Stage1 normal map/procedural normal.")
        else:
            tex = str(stage1.get("texture") or "").lower()
            if "nohq" not in tex and not re.search(r"\bno\b", tex):
                add(findings, file_path, int(stage1["texture_line"]), "WARN", "SUPER_STAGE1_NOT_NORMAL", "Stage1 does not look like a normal/_nohq texture.")
        stage5 = stages.get(5)
        if not stage5:
            add(findings, file_path, 1, "WARN", "SUPER_MISSING_STAGE5", "Super material has no Stage5 SMDI/specular map.")
        else:
            tex = str(stage5.get("texture") or "").lower()
            if "smdi" not in tex:
                add(findings, file_path, int(stage5["texture_line"]), "WARN", "SUPER_STAGE5_NOT_SMDI", "Stage5 does not look like an SMDI texture/procedural SMDI.")
        file_l = file_path.lower()
        stage3 = stages.get(3)
        if stage3 and ("damage" in file_l or "destruct" in file_l):
            tex = str(stage3.get("texture") or "")
            if tex.startswith("#"):
                add(findings, file_path, int(stage3["texture_line"]), "WARN", "DAMAGE_STAGE3_PROCEDURAL", "Damage/destruct material Stage3 is procedural; visible damage often needs a macro overlay texture.")

    if pixel_l == "multi" or vertex_l == "multi":
        if pixel_l != "multi" or vertex_l != "multi":
            add(findings, file_path, 1, "ERROR", "MULTI_SHADER_MISMATCH", "Multi materials should set both PixelShaderID and VertexShaderID to Multi.")
        for required in range(0, 5):
            if required not in stages:
                add(findings, file_path, 1, "ERROR", "MULTI_MISSING_BASE_STAGE", f"Multi material is missing required Stage{required}.")
        for recommended in list(range(5, 11)) + list(range(11, 15)):
            if recommended not in stages:
                add(findings, file_path, 1, "WARN", "MULTI_MISSING_RECOMMENDED_STAGE", f"Multi material is missing Stage{recommended}; verify this is intentional.")
        stage4 = stages.get(4)
        if stage4:
            uses_tex1 = str(stage4.get("uvSource") or "").lower() == "tex1"
            texgen_ref = stage4.get("texGen")
            if texgen_ref is not None:
                texgen = texgens.get(str(texgen_ref))
                uses_tex1 = uses_tex1 or (str((texgen or {}).get("uvSource") or "").lower() == "tex1")
            if not uses_tex1:
                # A warning, not an error: 587 vanilla Multi materials read the mask from tex
                # (P:\DZ\rocks_bliss\data\r_rock_general1.rvmat:55), against 1,373 on tex1.
                add(findings, file_path, int(stage4["line"]), "WARN", "MULTI_MASK_NOT_TEX1", "Multi Stage4 mask does not read tex1; check that the UV set it reads lays the mask over the mesh once, and that the detail textures tile on the other set.")

    return findings


def check_matpbr_companion(rvmat_path: Path, pixel: str | None, has_stages: bool) -> list[Finding]:
    """Validate the .emat companion of a MatPBR-style stub .rvmat (see
    skills/_shared/textures/matpbr-emat.md). A stub is a non-Super/Multi shader with zero
    Stage blocks; that shape is ambiguous (it also matches legitimate flat shaders), so
    every finding here is a WARN, not an ERROR.
    """
    findings: list[Finding] = []
    pixel_l = (pixel or "").lower()
    if has_stages or not pixel or pixel_l in ("super", "multi") or pixel_l in NO_STAGE_LEGITIMATE_SHADERS:
        return findings

    file_str = str(rvmat_path)
    emat_path = rvmat_path.with_suffix(".emat")
    if not emat_path.exists():
        add(
            findings, file_str, 1, "WARN", "STUB_RVMAT_NO_EMAT",
            f'PixelShaderID "{pixel}" has no Stage blocks and no matching {emat_path.name} next to it. '
            "If this is intentionally a flat/no-stage material, ignore this. If it's meant to be a MatPBR "
            "companion, the .emat must exist with this exact base name (see skills/_shared/textures/matpbr-emat.md).",
        )
        return findings

    try:
        emat_text = emat_path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        emat_text = emat_path.read_text(encoding="cp1252")

    if not re.search(r"\bMatPBR\s*\{", emat_text):
        # Vanilla water ships this same pairing with another material class: a two-line
        # CalmWater .rvmat next to an .emat holding MatWaterPool { ... }
        # (P:\DZ\water_bliss\ponds\data\enoch_pond.rvmat and enoch_pond.emat). That is not MatPBR
        # and not a mistake, so it gets no finding.
        if re.search(r"\bMatWaterPool\s*\{", emat_text):
            return findings
        add(findings, str(emat_path), 1, "WARN", "MATPBR_BLOCK_MISSING", "Companion .emat has no MatPBR { ... } block.")
        return findings

    for key in MATPBR_REQUIRED_MAPS:
        match = re.search(rf'{key}\s*"([^"]*)"', emat_text)
        if not match:
            add(findings, str(emat_path), 1, "WARN", "MATPBR_MISSING_MAP", f"Companion .emat has no {key} entry.")
            continue
        value = match.group(1)
        if not RESOURCE_ID_RE.match(value):
            add(
                findings, str(emat_path), 1, "WARN", "MATPBR_MAP_NOT_REGISTERED",
                f'{key} value "{value}" does not look like a Workbench Resource ID ({{HEX}}...); '
                "re-import and register the texture in Workbench instead of hand-typing a path.",
            )

    return findings


def lint_file(path: Path, pdrive_root: Path | None) -> list[Finding]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = path.read_text(encoding="cp1252")
    findings = lint_text(text, str(path), pdrive_root)
    pixel = top_string_value(text, "PixelShaderID")
    has_stages = bool(re.search(r"\bclass\s+Stage\d+\b", text))
    findings.extend(check_matpbr_companion(path, pixel, has_stages))
    return findings


def run_self_test() -> int:
    good = r'''
PixelShaderID="Super";
VertexShaderID="Super";
class Stage1 { texture="dz\weapons\x\data\x_nohq.paa"; };
class Stage5 { texture="dz\weapons\x\data\x_smdi.paa"; };
'''
    bad = r'''
PixelShaderID="Multi";
VertexShaderID="Super";
class Stage0 { texture="x\data\a.png"; };
class Stage4 { texture="x\data\mask_co.paa"; uvSource="tex"; };
'''
    good_findings = lint_text(good, "good.rvmat")
    bad_findings = lint_text(bad, "bad.rvmat")
    if any(item.severity == "ERROR" for item in good_findings):
        print("self-test failed: good fixture produced errors", file=sys.stderr)
        return 1
    expected = {"MULTI_SHADER_MISMATCH", "SOURCE_TEXTURE_EXT", "MULTI_MASK_NOT_TEX1"}
    got = {item.code for item in bad_findings}
    missing = expected - got
    if missing:
        print(f"self-test failed: missing expected findings {sorted(missing)}", file=sys.stderr)
        return 1
    print("self-test passed")
    return 0


def run_matpbr_self_test() -> int:
    # A well-formed MatPBR block as the fixture.
    good_emat = '''
MatPBR {
 AlbedoMap "{62634FC733258F68}path/albedo.edds"
 CastShadow 1
 ReceiveShadow 1
 SpecularMul 0.05
 NormalMap "{0B04E2D029CCEDAF}path/normal.edds"
 RoughnessMap "{5697E7B79A3CF21E}path/roughness.edds"
 MetalnessMap "{A2E5C39185F32DC1}path/metallic.edds"
 AOMap "{C4B8FDBD52394E5D}path/ao.edds"
 EnvReflMap "{066623E928F029E6}path/env_land_co.edds" cube
}
'''
    stub_rvmat = 'PixelShaderID = "CalmWater";\nVertexShaderID = "CalmWater";\n'

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        good_rvmat = tmp_path / "good_material.rvmat"
        good_rvmat.write_text(stub_rvmat, encoding="utf-8")
        (tmp_path / "good_material.emat").write_text(good_emat, encoding="utf-8")
        good_findings = check_matpbr_companion(good_rvmat, "CalmWater", False)
        if good_findings:
            print(f"matpbr self-test failed: well-formed pairing produced findings: {good_findings}", file=sys.stderr)
            return 1

        orphan_rvmat = tmp_path / "orphan_material.rvmat"
        orphan_rvmat.write_text(stub_rvmat, encoding="utf-8")
        orphan_findings = check_matpbr_companion(orphan_rvmat, "CalmWater", False)
        if "STUB_RVMAT_NO_EMAT" not in {item.code for item in orphan_findings}:
            print("matpbr self-test failed: missing .emat did not raise STUB_RVMAT_NO_EMAT", file=sys.stderr)
            return 1

        incomplete_rvmat = tmp_path / "incomplete_material.rvmat"
        incomplete_rvmat.write_text(stub_rvmat, encoding="utf-8")
        incomplete_emat = good_emat.replace(' RoughnessMap "{5697E7B79A3CF21E}path/roughness.edds"\n', '')
        (tmp_path / "incomplete_material.emat").write_text(incomplete_emat, encoding="utf-8")
        incomplete_findings = check_matpbr_companion(incomplete_rvmat, "CalmWater", False)
        if "MATPBR_MISSING_MAP" not in {item.code for item in incomplete_findings}:
            print("matpbr self-test failed: missing RoughnessMap did not raise MATPBR_MISSING_MAP", file=sys.stderr)
            return 1

        flat_rvmat = tmp_path / "flat_material.rvmat"
        flat_rvmat.write_text('PixelShaderID = "Normal";\nVertexShaderID = "Normal";\n', encoding="utf-8")
        flat_findings = check_matpbr_companion(flat_rvmat, "Normal", False)
        if flat_findings:
            print(f"matpbr self-test failed: legitimate flat Normal shader produced findings: {flat_findings}", file=sys.stderr)
            return 1

    print("matpbr self-test passed")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint DayZ .rvmat files.")
    parser.add_argument("rvmat", nargs="*", help="One or more .rvmat files.")
    parser.add_argument("--pdrive-root", help="Optional P: root for existence checks, e.g. P:\\")
    parser.add_argument("--json", action="store_true", help="Emit JSON findings.")
    parser.add_argument("--warnings-as-errors", action="store_true", help="Exit non-zero on warnings.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in tests.")
    args = parser.parse_args(argv)

    if args.self_test:
        result = run_self_test()
        if result != 0:
            return result
        return run_matpbr_self_test()
    if not args.rvmat:
        parser.error("at least one .rvmat file is required unless --self-test is used")

    pdrive_root = Path(args.pdrive_root) if args.pdrive_root else None
    if pdrive_root is not None and not pdrive_root.is_dir():
        # Without this every texture would be reported as not found, which hides the real cause.
        print(f"ERROR: --pdrive-root {args.pdrive_root} is not a folder. If it is P:\\, mount the work drive first "
              "(/dayz-workdrive), or run without --pdrive-root to skip the existence check.", file=sys.stderr)
        return 2
    findings: list[Finding] = []
    for item in args.rvmat:
        path = Path(item)
        if not path.exists():
            findings.append(Finding(str(path), 1, "ERROR", "FILE_NOT_FOUND", "File not found."))
            continue
        findings.extend(lint_file(path, pdrive_root))

    if args.json:
        print(json.dumps([asdict(item) for item in findings], indent=2))
    else:
        for item in findings:
            print(f"{item.file}:{item.line}: {item.severity} {item.code}: {item.message}")
        if not findings:
            print("No findings.")

    has_error = any(item.severity == "ERROR" for item in findings)
    has_warn = any(item.severity == "WARN" for item in findings)
    return 1 if has_error or (args.warnings_as_errors and has_warn) else 0


if __name__ == "__main__":
    raise SystemExit(main())

