"""RVMAT parser.

Extracts texture stage assignments, material colors (including the BI
`emmisive` spelling), specular power and shader IDs from a text .rvmat.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


def parse_rvmat(filepath: str) -> dict:
    """Parse an .rvmat file and extract material properties.

    RVMAT files are C-style config text with:
    - ambient[], diffuse[], specular[], emissive[] color arrays
    - specularPower float
    - PixelShaderID / VertexShaderID
    - Stage blocks with texture assignments

    Returns a dict with all extracted properties. The `file` field stores
    the path as given by the caller (use a relative path if the result
    must not contain a machine root).
    """
    with open(filepath, "r", encoding="utf-8", errors="replace", newline="") as handle:
        content = handle.read()

    result = {
        "file": filepath.replace("\\", "/"),
        "name": Path(filepath).stem,
        "colors": {},
        "specular_power": None,
        "pixel_shader": None,
        "vertex_shader": None,
        "stages": [],
        "textures": {},
    }

    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
    content = re.sub(r"//.*$", "", content, flags=re.MULTILINE)

    color_pattern = r"(\w+)\s*\[\s*\]\s*=\s*\{([^}]+)\}"
    for match in re.finditer(color_pattern, content):
        name = match.group(1).lower()
        values_str = match.group(2)
        try:
            values = [float(item.strip()) for item in values_str.split(",") if item.strip()]
            result["colors"][name] = values
        except ValueError:
            pass

    spec_match = re.search(r"specularPower\s*=\s*([\d.]+)", content, re.IGNORECASE)
    if spec_match:
        result["specular_power"] = float(spec_match.group(1))

    ps_match = re.search(r'PixelShaderID\s*=\s*"([^"]*)"', content, re.IGNORECASE)
    if ps_match:
        result["pixel_shader"] = ps_match.group(1)

    vs_match = re.search(r'VertexShaderID\s*=\s*"([^"]*)"', content, re.IGNORECASE)
    if vs_match:
        result["vertex_shader"] = vs_match.group(1)

    stage_pattern = r"class\s+Stage(\d+)\s*\{([^}]*)\}"
    for match in re.finditer(stage_pattern, content):
        stage_num = int(match.group(1))
        stage_content = match.group(2)
        stage = {"index": stage_num}
        tex_match = re.search(r'texture\s*=\s*"([^"]*)"', stage_content)
        if tex_match:
            stage["texture"] = tex_match.group(1)
        uv_match = re.search(r'uvSource\s*=\s*"([^"]*)"', stage_content)
        if uv_match:
            stage["uvSource"] = uv_match.group(1)
        result["stages"].append(stage)

    for stage in result["stages"]:
        tex = stage.get("texture", "")
        if not tex:
            continue
        tex_lower = tex.lower()
        basename = os.path.basename(tex_lower.replace("\\", "/"))
        if "_co." in basename or basename.endswith("_co.paa"):
            result["textures"]["diffuse"] = tex
        elif "_nohq." in basename:
            result["textures"]["normal"] = tex
        elif "_smdi." in basename:
            result["textures"]["specular"] = tex
        elif "_as." in basename:
            result["textures"]["ambient_shadow"] = tex
        elif "_mc." in basename:
            result["textures"]["macro"] = tex
        elif "_dt." in basename:
            result["textures"]["detail"] = tex
        elif "#(ai" in tex_lower or "#(arg" in tex_lower:
            result["textures"]["procedural_stage%s" % stage["index"]] = tex
        else:
            result["textures"]["stage%s" % stage["index"]] = tex

    emissive = result["colors"].get("emissive", result["colors"].get("forceddiffuse", []))
    result["is_emissive"] = bool(emissive and any(value > 0.01 for value in emissive[:3]))
    return result


def find_textures_for_model(rvmat_paths: list, p3d_textures: list | None = None) -> dict:
    """Build a map of every texture referenced by the given .rvmat files."""
    all_textures = {}
    for rvmat_path in rvmat_paths:
        if not os.path.exists(rvmat_path):
            continue
        mat = parse_rvmat(rvmat_path)
        for role, tex_path in mat["textures"].items():
            if tex_path.startswith("#("):
                continue
            normalized = tex_path.replace("\\", "/")
            all_textures[normalized] = {
                "role": role,
                "source_rvmat": rvmat_path.replace("\\", "/"),
                "original_path": tex_path,
                "is_emissive": mat.get("is_emissive", False) and role == "diffuse",
            }
    if p3d_textures:
        for tex in p3d_textures:
            normalized = tex.replace("\\", "/")
            if normalized not in all_textures:
                all_textures[normalized] = {
                    "role": "diffuse",
                    "source_rvmat": None,
                    "original_path": tex,
                    "is_emissive": False,
                }
    return all_textures


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("Usage: python -m dayz_3d_viewer parse-rvmat <file.rvmat> [...]")
        return 2
    for path in args:
        print(json.dumps(parse_rvmat(path), indent=2, sort_keys=True))
    return 0
