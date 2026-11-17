import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

from .diff import diff_anatomy
from .errors import OdolStrictError
from .inspect import inspect_odol


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        if args.command == "inspect":
            backend_root = args.backend_root or os.environ.get(
                "DAYZ_ODOL_BACKEND_ROOT"
            )
            if not backend_root:
                raise OdolStrictError(
                    "ODOL_BACKEND_MISSING",
                    "an explicit backend root is required",
                )
            result = inspect_odol(
                args.file,
                backend_root,
                backend_manifest=args.backend_manifest,
            )
            exit_code = 0
        else:
            reference = _read_summary(args.reference)
            candidate = _read_summary(args.candidate)
            result = diff_anatomy(reference, candidate)
            exit_code = 0 if result["equal"] else 1
    except OdolStrictError as error:
        sys.stdout.write(_json_line({
            "error": {
                "code": error.code,
                "message": error.message,
                "offset": error.offset,
            }
        }))
        return 2
    text = _json_line(result)
    if args.json_output:
        try:
            _atomic_write_text(Path(args.json_output), text)
        except OSError:
            error = OdolStrictError(
                "ODOL_OUTPUT_UNWRITABLE",
                "JSON output cannot be written atomically",
            )
            sys.stdout.write(_json_line({
                "error": {
                    "code": error.code,
                    "message": error.message,
                    "offset": error.offset,
                }
            }))
            return 2
    else:
        sys.stdout.write(text)
    return exit_code


def _parser():
    parser = argparse.ArgumentParser(prog="dayz-odol-strict")
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect")
    inspect.add_argument("file")
    inspect.add_argument("--backend-root")
    inspect.add_argument("--backend-manifest")
    inspect.add_argument("--json", dest="json_output")
    diff = commands.add_parser("diff")
    diff.add_argument("reference")
    diff.add_argument("candidate")
    diff.add_argument("--json", dest="json_output")
    return parser


def _read_summary(path):
    try:
        return json.loads(
            Path(path).read_text(encoding="utf-8", errors="strict")
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise OdolStrictError(
            "ODOL_SUMMARY_INVALID",
            "summary is not readable strict UTF-8 JSON",
        )


def _json_line(value):
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    )


def _atomic_write_text(path, text):
    directory = path.parent.resolve()
    fd, temporary = tempfile.mkstemp(
        prefix=path.name + ".tmp.", dir=directory
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
