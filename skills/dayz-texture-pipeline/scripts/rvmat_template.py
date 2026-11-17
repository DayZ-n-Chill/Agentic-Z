#!/usr/bin/env python3
"""Generate starter DayZ .rvmat templates.

Templates are intentionally marked as starting points. Verify against a nearby
vanilla material before shipping the output.

Pure offline script: it prints a template or writes it to --output. It reads nothing
from the P: work drive and does not run /dayz-preflight.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from string import Template


def normalize_prefix(prefix: str) -> str:
    prefix = prefix.replace("/", "\\").strip().strip('"')
    for suffix in (".rvmat", "_co.paa", "_nohq.paa", "_smdi.paa"):
        if prefix.lower().endswith(suffix):
            prefix = prefix[: -len(suffix)]
    return prefix


def render_super(prefix: str) -> str:
    prefix = normalize_prefix(prefix)
    return Template(r'''ambient[]={1,1,1,1};
diffuse[]={1,1,1,1};
forcedDiffuse[]={0,0,0,0};
emmisive[]={0,0,0,1};
specular[]={0.4,0.4,0.4,1};
specularPower=80;
PixelShaderID="Super";
VertexShaderID="Super";
class Stage1
{
	texture="${prefix}_nohq.paa";
	uvSource="tex";
	class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; };
};
class Stage2
{
	texture="#(argb,8,8,3)color(0.5,0.5,0.5,0.5,DT)";
	uvSource="tex";
	class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; };
};
class Stage3
{
	texture="#(argb,8,8,3)color(0,0,0,0,MC)";
	uvSource="tex";
	class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; };
};
class Stage4
{
	texture="#(argb,8,8,3)color(1,1,1,1,AS)";
	uvSource="tex";
	class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; };
};
class Stage5
{
	texture="${prefix}_smdi.paa";
	uvSource="tex";
	class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; };
};
class Stage6
{
	texture="#(ai,32,1,1)fresnel(1.12,0.78)";
	uvSource="tex";
	class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; };
};
class Stage7
{
	texture="dz\data\data\env_land_co.paa";
	uvSource="tex";
	class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; };
};
''').substitute(prefix=prefix)


def render_damage(prefix: str, overlay: str) -> str:
    content = render_super(prefix)
    old_stage3 = '''class Stage3
{
\ttexture="#(argb,8,8,3)color(0,0,0,0,MC)";
\tuvSource="tex";
\tclass uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; };
};'''
    new_stage3 = f'''class Stage3
{{
\ttexture="{overlay}";
\tuvSource="tex";
\tclass uvTransform {{ aside[]={{4,0,0}}; up[]={{0,4,0}}; dir[]={{0,0,1}}; pos[]={{0,0,0}}; }};
}};'''
    return content.replace(old_stage3, new_stage3)


def render_emissive(prefix: str, strength: str) -> str:
    content = render_super(prefix)
    return content.replace("emmisive[]={0,0,0,1};", f"emmisive[]={{1,1,1,{strength}}};")


def render_penetration(surface: str) -> str:
    return Template(r'''surfaceInfo="$surface";
ambient[]={0.78799999,0.55000001,0,1};
diffuse[]={0.78799999,0.55000001,0,1};
forcedDiffuse[]={0,0,0,0};
emmisive[]={0,0,0,1};
specular[]={0,0,0,1};
specularPower=1;
PixelShaderID="Normal";
VertexShaderID="Basic";
''').substitute(surface=surface.replace("/", "\\"))


def render_multi(prefix: str) -> str:
    prefix = normalize_prefix(prefix)
    return Template(r'''PixelShaderID="Multi";
VertexShaderID="Multi";

class TexGen0 { uvSource="tex"; class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; }; };
class TexGen1 { uvSource="tex"; class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; }; };
class TexGen2 { uvSource="tex"; class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; }; };
class TexGen3 { uvSource="tex"; class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; }; };
class TexGen4 { uvSource="tex1"; class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; }; };

class Stage0 { texture="${prefix}_black_co.paa"; texGen="0"; };
class Stage1 { texture="${prefix}_red_co.paa"; texGen="1"; };
class Stage2 { texture="${prefix}_green_co.paa"; texGen="2"; };
class Stage3 { texture="${prefix}_blue_co.paa"; texGen="3"; };
class Stage4 { texture="${prefix}_mask_co.paa"; texGen="4"; };
class Stage5 { texture="${prefix}_black_smdi.paa"; texGen="0"; };
class Stage6 { texture="${prefix}_red_smdi.paa"; texGen="1"; };
class Stage7 { texture="${prefix}_green_smdi.paa"; texGen="2"; };
class Stage8 { texture="${prefix}_blue_smdi.paa"; texGen="3"; };
class Stage9 { texture="#(argb,8,8,3)color(0,0,0,0,MC)"; texGen="0"; };
class Stage10 { texture="#(argb,8,8,3)color(1,1,1,1,AS)"; texGen="4"; };
class Stage11 { texture="${prefix}_black_nohq.paa"; texGen="0"; };
class Stage12 { texture="${prefix}_red_nohq.paa"; texGen="1"; };
class Stage13 { texture="${prefix}_green_nohq.paa"; texGen="2"; };
class Stage14 { texture="${prefix}_blue_nohq.paa"; texGen="3"; };
''').substitute(prefix=prefix)


def write_or_print(content: str, output: str | None) -> None:
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    else:
        print(content, end="")


def run_self_test() -> int:
    samples = [
        render_super("x\\data\\thing"),
        render_damage("x\\data\\thing_damage", "dz\\weapons\\data\\weapons_damage_generic_mc.paa"),
        render_emissive("x\\data\\lamp", "25"),
        render_penetration("dz\\data\\data\\penetration\\wood.bisurf"),
        render_multi("x\\data\\wall"),
    ]
    for sample in samples:
        if "$prefix" in sample or "$surface" in sample:
            print("self-test failed: unresolved template variable", file=sys.stderr)
            return 1
        if "PixelShaderID" not in sample or "VertexShaderID" not in sample:
            print("self-test failed: missing shader IDs", file=sys.stderr)
            return 1
    print("self-test passed")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate starter DayZ .rvmat templates.")
    parser.add_argument("kind", nargs="?", choices=["super", "damage", "emissive", "penetration", "multi"], help="Template kind.")
    parser.add_argument("--prefix", help="Packed path prefix without suffix, e.g. myaddon\\data\\asset.")
    parser.add_argument("--overlay", default=r"dz\weapons\data\weapons_damage_generic_mc.paa", help="Damage/destruct Stage3 overlay path.")
    parser.add_argument("--surface", default=r"dz\data\data\penetration\wood.bisurf", help="Penetration .bisurf path.")
    parser.add_argument("--strength", default="25", help="Emissive alpha/strength value.")
    parser.add_argument("--output", help="Optional output .rvmat path.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in tests.")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()
    if not args.kind:
        parser.error("kind is required unless --self-test is used")

    if args.kind == "penetration":
        content = render_penetration(args.surface)
    else:
        if not args.prefix:
            parser.error("--prefix is required for this template kind")
        if args.kind == "super":
            content = render_super(args.prefix)
        elif args.kind == "damage":
            content = render_damage(args.prefix, args.overlay.replace("/", "\\"))
        elif args.kind == "emissive":
            content = render_emissive(args.prefix, args.strength)
        elif args.kind == "multi":
            content = render_multi(args.prefix)
        else:
            raise AssertionError(args.kind)

    write_or_print(content, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
