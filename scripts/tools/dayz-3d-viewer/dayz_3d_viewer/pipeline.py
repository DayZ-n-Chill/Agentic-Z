"""Full orchestration: P3D + PAA + RVMAT → interactive Three.js viewer."""

from __future__ import annotations

import glob
import os
import shutil
from pathlib import Path

from .paa_to_png import convert_paa_to_png
from .p3d_to_gltf import p3d_info, p3d_to_glb
from .rvmat_parser import parse_rvmat
from .viewer_template import extract_geometry_for_viewer, generate_viewer_html


def run_pipeline(
    p3d_path: str,
    texture_dirs: list | None = None,
    rvmat_dirs: list | None = None,
    output_dir: str | None = None,
    model_name: str | None = None,
    mode: str = "embedded",
    generate_viewer: bool = True,
    verbose: bool = False,
) -> dict:
    """Run the P3D + textures + materials → 3D viewer pipeline.

    Returns a dict of generated paths. Search directories are recorded as
    given; generated file names are relative to `output_dir`.
    """
    results = {
        "input_p3d": Path(p3d_path).name,
        "converted_textures": [],
        "parsed_rvmats": [],
        "glb_path": None,
        "viewer_path": None,
        "errors": [],
    }

    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(p3d_path) or ".", "output")
    os.makedirs(output_dir, exist_ok=True)
    tex_output_dir = os.path.join(output_dir, "textures")
    os.makedirs(tex_output_dir, exist_ok=True)

    if model_name is None:
        model_name = Path(p3d_path).stem
    if texture_dirs is None:
        texture_dirs = []
    else:
        texture_dirs = list(texture_dirs)
    if rvmat_dirs is None:
        rvmat_dirs = []
    else:
        rvmat_dirs = list(rvmat_dirs)

    p3d_parent = os.path.dirname(os.path.abspath(p3d_path))
    if p3d_parent not in texture_dirs:
        texture_dirs.append(p3d_parent)
    if p3d_parent not in rvmat_dirs:
        rvmat_dirs.append(p3d_parent)

    if verbose:
        print("=" * 60)
        print("STEP 1: Analyzing P3D: %s" % p3d_path)
        print("=" * 60)

    info = p3d_info(p3d_path)
    p3d_textures = set()
    p3d_materials = set()
    for lod_info in info["lods"]:
        for tex in lod_info.get("textures", []):
            if tex:
                p3d_textures.add(tex)
        for mat in lod_info.get("materials", []):
            if mat:
                p3d_materials.add(mat)

    if verbose:
        print("  LODs: %s" % info["num_lods"])
        print("  Textures referenced: %s" % sorted(p3d_textures))
        print("  Materials referenced: %s" % sorted(p3d_materials))

    if verbose:
        print()
        print("=" * 60)
        print("STEP 2: Converting textures (PAA → PNG)")
        print("=" * 60)

    texture_map = {}
    available_files = {}
    for tex_dir in texture_dirs:
        for ext in ("*.paa", "*.pac", "*.png", "*.jpg", "*.tga"):
            for filepath in glob.glob(os.path.join(tex_dir, "**", ext), recursive=True):
                available_files[Path(filepath).stem.lower()] = filepath

    for tex_ref in p3d_textures:
        basename = os.path.basename(tex_ref.replace("\\", "/"))
        stem = os.path.splitext(basename)[0].lower()
        if stem not in available_files:
            if verbose:
                print("  ? %s not found in search dirs" % basename)
            continue
        src = available_files[stem]
        if src.lower().endswith(".paa") or src.lower().endswith(".pac"):
            png_out = os.path.join(tex_output_dir, stem + ".png")
            try:
                convert_paa_to_png(src, png_out, verbose=verbose)
                texture_map[stem] = png_out
                results["converted_textures"].append(
                    {"source": Path(src).name, "output": os.path.abspath(png_out), "status": "ok"}
                )
                if verbose:
                    print("  + %s -> %s" % (basename, png_out))
            except Exception as exc:
                results["errors"].append("PAA convert failed: %s: %s" % (Path(src).name, exc))
                if verbose:
                    print("  x %s: %s" % (basename, exc))
        elif src.lower().endswith(".png"):
            png_out = os.path.join(tex_output_dir, stem + ".png")
            shutil.copyfile(src, png_out)
            texture_map[stem] = png_out
            results["converted_textures"].append(
                {"source": Path(src).name, "output": os.path.abspath(png_out), "status": "copied"}
            )
            if verbose:
                print("  -> %s (PNG, copied)" % basename)

    if verbose:
        print()
        print("=" * 60)
        print("STEP 3: Parsing RVMAT materials")
        print("=" * 60)

    for mat_ref in p3d_materials:
        basename = os.path.basename(mat_ref.replace("\\", "/"))
        stem = os.path.splitext(basename)[0].lower()
        found = False
        for rvmat_dir in rvmat_dirs:
            for filepath in glob.glob(os.path.join(rvmat_dir, "**", "*.rvmat"), recursive=True):
                if Path(filepath).stem.lower() != stem:
                    continue
                try:
                    parsed = parse_rvmat(filepath)
                    results["parsed_rvmats"].append(parsed)
                    for role, tex_path in parsed.get("textures", {}).items():
                        if tex_path.startswith("#("):
                            continue
                        tex_basename = os.path.basename(tex_path.replace("\\", "/"))
                        tex_stem = os.path.splitext(tex_basename)[0].lower()
                        if tex_stem in available_files and tex_stem not in texture_map:
                            src = available_files[tex_stem]
                            if src.lower().endswith((".paa", ".pac")):
                                png_out = os.path.join(tex_output_dir, tex_stem + ".png")
                                try:
                                    convert_paa_to_png(src, png_out)
                                    texture_map[tex_stem] = png_out
                                except Exception:
                                    pass
                    if verbose:
                        print(
                            "  + %s: stages=%s, emissive=%s"
                            % (basename, len(parsed["stages"]), parsed.get("is_emissive", False))
                        )
                    found = True
                    break
                except Exception as exc:
                    results["errors"].append(
                        "RVMAT parse failed: %s: %s" % (Path(filepath).name, exc)
                    )
                    if verbose:
                        print("  x %s: %s" % (basename, exc))
            if found:
                break
        if not found and verbose:
            print("  ? %s not found" % basename)

    if verbose:
        print()
        print("=" * 60)
        print("STEP 4: Converting P3D -> GLB")
        print("=" * 60)

    rvmat_dict = {}
    for parsed in results["parsed_rvmats"]:
        stem = os.path.splitext(os.path.basename(parsed["file"]))[0].lower()
        rvmat_dict[stem] = parsed

    glb_path = os.path.join(output_dir, model_name + ".glb")
    try:
        p3d_to_glb(
            p3d_path=p3d_path,
            output_path=glb_path,
            texture_map=texture_map,
            rvmat_data=rvmat_dict,
            verbose=verbose,
        )
        # Report a path the caller can open. The basename alone is unusable: the file
        # lands under output_dir, so a consumer parsing this JSON looked in the wrong place.
        results["glb_path"] = os.path.abspath(glb_path)
    except Exception as exc:
        results["errors"].append("P3D->GLB failed: %s" % exc)
        if verbose:
            print("  x Conversion failed: %s" % exc)
        return results

    if generate_viewer:
        if verbose:
            print()
            print("=" * 60)
            print("STEP 5: Generating Three.js viewer")
            print("=" * 60)
        viewer_path = os.path.join(output_dir, model_name + "_viewer.html")
        try:
            if mode == "web":
                generate_viewer_html(
                    model_name=model_name,
                    mode="web",
                    glb_url=model_name + ".glb",
                    output_path=viewer_path,
                )
            else:
                geo_data = extract_geometry_for_viewer(
                    p3d_path=p3d_path,
                    texture_map=texture_map,
                    rvmat_data=rvmat_dict,
                )
                generate_viewer_html(
                    model_name=model_name,
                    mode="embedded",
                    geometry_data=geo_data,
                    output_path=viewer_path,
                )
            results["viewer_path"] = os.path.abspath(viewer_path)
            if verbose:
                print("  + %s" % viewer_path)
        except Exception as exc:
            results["errors"].append("Viewer generation failed: %s" % exc)
            if verbose:
                print("  x %s" % exc)

    if verbose:
        print()
        print("=" * 60)
        print("PIPELINE COMPLETE")
        print("=" * 60)
        print("  GLB: %s" % results["glb_path"])
        print("  Viewer: %s" % results["viewer_path"])
        print("  Textures converted: %s" % len(results["converted_textures"]))
        print("  RVMATs parsed: %s" % len(results["parsed_rvmats"]))
        if results["errors"]:
            print("  Errors: %s" % len(results["errors"]))
            for err in results["errors"]:
                print("    - %s" % err)
    return results
