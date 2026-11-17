import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

from .findings import finding, sort_findings
from .runner import run_preflight


EXIT_CODES = {"PASS": 0, "FAIL": 1, "INVALID": 2}


def main(argv=None):
    args = _parser().parse_args(argv)
    result = run_preflight(args.model, args.contract)
    text = _json_line(result)
    if args.json_output:
        try:
            _atomic_write_text(Path(args.json_output), text)
        except OSError:
            result = dict(result)
            result["verdict"] = "INVALID"
            result["findings"] = sort_findings(
                list(result["findings"])
                + [
                    finding(
                        "PREFLIGHT_OUTPUT_UNWRITABLE",
                        "ERROR",
                        "JSON output cannot be written atomically",
                        lod_index=None,
                    )
                ]
            )
            sys.stdout.write(_json_line(result))
            return 2
    else:
        sys.stdout.write(text)
    return EXIT_CODES[result["verdict"]]


def _parser():
    parser = argparse.ArgumentParser(prog="dayz-model-preflight")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check")
    check.add_argument("model")
    check.add_argument("--contract", required=True)
    check.add_argument("--json", dest="json_output")
    return parser


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
