import argparse
import json
from pathlib import Path
import sys

from .errors import AnimationFormatError
from .inspect import inspect_bytes


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


def _error_value(error):
    return {
        "error": {
            "code": error.code,
            "message": error.message,
            "offset": error.offset,
        }
    }


def _parser():
    parser = argparse.ArgumentParser(prog="dayz-animation-formats")
    commands = parser.add_subparsers(dest="command", required=True)
    inspect_parser = commands.add_parser("inspect")
    inspect_parser.add_argument("file")
    inspect_parser.add_argument("--output")
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        data = Path(args.file).read_bytes()
        text = _json_line(inspect_bytes(data))
    except AnimationFormatError as error:
        sys.stdout.write(_json_line(_error_value(error)))
        return 2
    except OSError:
        error = AnimationFormatError(
            "ANIM_IO_ERROR", "could not read input file"
        )
        sys.stdout.write(_json_line(_error_value(error)))
        return 2

    if args.output:
        try:
            Path(args.output).write_text(text, encoding="utf-8", newline="")
        except OSError:
            error = AnimationFormatError(
                "ANIM_IO_ERROR", "could not write output file"
            )
            sys.stdout.write(_json_line(_error_value(error)))
            return 2
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
