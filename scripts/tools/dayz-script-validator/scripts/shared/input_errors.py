INPUT_NOT_FOUND_RULE_ID = "INPUT-NOT-FOUND"


INPUT_ENCODING_ERROR_RULE_ID = "INPUT-ENCODING-ERROR"


def build_input_not_found_error(addon_root):
    message = (
        f"[FAIL] addon_root '{addon_root}' does not exist on disk. Provide a "
        "valid file or directory path."
    )
    return {
        "check": INPUT_NOT_FOUND_RULE_ID,
        "file": str(addon_root),
        "line": None,
        "message": message,
        "severity": "FAIL",
        "rule_id": INPUT_NOT_FOUND_RULE_ID,
    }


def decode_error_line_number(error):
    prefix = error.object[: error.start]
    if isinstance(prefix, bytes):
        return prefix.count(b"\n") + 1
    return prefix.count("\n") + 1


def build_input_encoding_error(rel_path, error):
    message = (
        f"[FAIL] {rel_path}: file is not valid UTF-8. Decode error at byte "
        f"{error.start}: {error.reason}. Convert source to UTF-8 or document "
        "encoding in assumptions.md."
    )
    return {
        "check": INPUT_ENCODING_ERROR_RULE_ID,
        "file": rel_path,
        "line": decode_error_line_number(error),
        "message": message,
        "severity": "FAIL",
        "rule_id": INPUT_ENCODING_ERROR_RULE_ID,
    }


def read_text_utf8_or_error(path, rel_path):
    try:
        return path.read_text(encoding="utf-8"), None
    except UnicodeDecodeError as error:
        return None, build_input_encoding_error(rel_path, error)


def discover_files(addon_root):
    if addon_root.is_file():
        if addon_root.suffix.lower() in (".c", ".rvmat", ".layout", ".cpp"):
            return [addon_root]
        return []

    files = []
    for path in addon_root.rglob("*"):
        if path.is_file() and path.suffix.lower() in (".c", ".rvmat", ".layout", ".cpp"):
            files.append(path)
    return sorted(files)


def relative_path(path, addon_root):
    try:
        return str(path.relative_to(addon_root))
    except ValueError:
        return str(path)
