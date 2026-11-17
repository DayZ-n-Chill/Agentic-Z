"""Command line for the DayZ 3D viewer tool."""

from __future__ import annotations

import argparse
import json
import sys

from .errors import MissingDependencyError, ViewerError
from .paa_to_png import convert_paa_to_png
from .p3d_to_gltf import p3d_info, p3d_to_glb
from .pipeline import run_pipeline
from .rvmat_parser import parse_rvmat


def main(argv=None):
    parser = argparse.ArgumentParser(prog="dayz-3d-viewer")
    commands = parser.add_subparsers(dest="command", required=True)

    p3d = commands.add_parser("p3d-to-glb", help="Convert an MLOD .p3d to .glb")
    p3d.add_argument("input")
    p3d.add_argument("output", nargs="?")
    p3d.add_argument("--textures")
    p3d.add_argument("--info", action="store_true")
    p3d.add_argument("-v", "--verbose", action="store_true")

    paa = commands.add_parser("paa-to-png", help="Decode a .paa texture to PNG")
    paa.add_argument("input")
    paa.add_argument("output", nargs="?")
    paa.add_argument("-v", "--verbose", action="store_true")

    rvmat = commands.add_parser("parse-rvmat", help="Parse one or more .rvmat files")
    rvmat.add_argument("inputs", nargs="+")

    build = commands.add_parser("build-viewer", help="Convert a model and emit HTML")
    build.add_argument("p3d")
    build.add_argument("--textures", nargs="+", default=[])
    build.add_argument("--rvmats", nargs="+", default=[])
    build.add_argument("--output", default=None)
    build.add_argument("--name", default=None)
    build.add_argument("--mode", default="embedded", choices=["embedded", "web"])
    build.add_argument("--no-viewer", action="store_true")
    build.add_argument("-v", "--verbose", action="store_true")

    commands.add_parser(
        "install-lzo-shim",
        help="Write an lzokay-backed lzo.py into user site-packages",
    )

    args = parser.parse_args(argv)
    try:
        return _dispatch(args)
    except MissingDependencyError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except ViewerError as exc:
        print(str(exc), file=sys.stderr)
        return 1


def _dispatch(args):
    if args.command == "p3d-to-glb":
        if args.info:
            print(json.dumps(p3d_info(args.input), indent=2, sort_keys=True))
            return 0
        p3d_to_glb(
            args.input,
            args.output,
            texture_dir=args.textures,
            verbose=args.verbose,
        )
        return 0
    if args.command == "paa-to-png":
        convert_paa_to_png(args.input, args.output, verbose=args.verbose)
        return 0
    if args.command == "parse-rvmat":
        for path in args.inputs:
            print(json.dumps(parse_rvmat(path), indent=2, sort_keys=True))
        return 0
    if args.command == "build-viewer":
        results = run_pipeline(
            p3d_path=args.p3d,
            texture_dirs=args.textures,
            rvmat_dirs=args.rvmats,
            output_dir=args.output,
            model_name=args.name,
            mode=args.mode,
            generate_viewer=not args.no_viewer,
            verbose=args.verbose,
        )
        print(json.dumps(results, indent=2, sort_keys=True, default=str))
        return 1 if results["errors"] else 0
    if args.command == "install-lzo-shim":
        from .install_lzo_shim import install_lzo_shim

        return install_lzo_shim()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
