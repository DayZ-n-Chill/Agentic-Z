import re

from shared.method_recognition import find_block_end_line, find_if_body_range


ES_EMPTY_IFDEF_RE_OPEN = re.compile(
    r"^\s*#(?P<directive>ifdef|ifndef)\s+(?P<macro>\w+)\s*$"
)


ES_EMPTY_IFDEF_RE_CLOSE = re.compile(r"^\s*#endif\b")


ES_EMPTY_IFDEF_RE_UNSUPPORTED_IFDEF = re.compile(r"^\s*#(?:ifdef|ifndef)\b")


ES_EMPTY_IFDEF_RE_UNSUPPORTED_DIRECTIVE = re.compile(r"^\s*#(?:if|elif|else)\b")


SERVER_GUARD_IF_RE = re.compile(
    r"\bif\s*\(\s*"
    r"(?:GetGame\(\)\.IsServer\(\)|g_Game\.IsServer\(\)|"
    r"!\s*GetGame\(\)\.IsClient\(\)|IsServer\(\))"
    r"\s*\)"
)


TRY_BLOCK_RE = re.compile(r"^\s*try\s*\{")


def mark_supported_ifdef_stack_has_statement(stack):
    for frame in stack:
        if not frame["unsupported"]:
            frame["has_statement"] = True


def unsupported_directive_opens_block(line):
    return re.match(r"^\s*#if\b", line) is not None


def update_ifdef_stack_for_line(stack, line):
    open_match = ES_EMPTY_IFDEF_RE_OPEN.match(line)
    if open_match:
        stack.append(
            {
                "macro": open_match.group("macro"),
                "directive": open_match.group("directive"),
            }
        )
        return

    if ES_EMPTY_IFDEF_RE_UNSUPPORTED_IFDEF.match(line):
        stack.append({"macro": None, "directive": "unsupported"})
        return

    if ES_EMPTY_IFDEF_RE_UNSUPPORTED_DIRECTIVE.match(line):
        if unsupported_directive_opens_block(line):
            stack.append({"macro": None, "directive": "unsupported"})
        elif stack:
            stack[-1] = {"macro": None, "directive": "unsupported"}
        return

    if ES_EMPTY_IFDEF_RE_CLOSE.match(line):
        if stack:
            stack.pop()


def compute_ifdef_stack_at(lines, end_line_exclusive):
    stack = []
    for index in range(end_line_exclusive):
        update_ifdef_stack_for_line(stack, lines[index])
    return stack


def ifdef_stack_is_definitely_server_side(stack):
    has_server_ifdef = False
    for frame in stack:
        if frame["directive"] == "unsupported":
            return False
        if frame["macro"] != "SERVER":
            continue
        if frame["directive"] == "ifndef":
            return False
        if frame["directive"] == "ifdef":
            has_server_ifdef = True
    return has_server_ifdef


def line_is_inside_server_ifdef(method, line_number, lines):
    stack = compute_ifdef_stack_at(lines, method["start_line"] - 1)

    for current_line in range(method["start_line"], method["end_line"] + 1):
        line = lines[current_line - 1]
        if current_line == line_number:
            return ifdef_stack_is_definitely_server_side(stack)
        update_ifdef_stack_for_line(stack, line)

    return False


def line_is_inside_server_if_guard(method, line_number, lines):
    method_end_index = method["end_line"] - 1

    for index in range(method["start_line"] - 1, method["end_line"]):
        if not SERVER_GUARD_IF_RE.search(lines[index]):
            continue
        start_line, end_line = find_if_body_range(lines, index, method_end_index)
        if start_line <= line_number <= end_line:
            return True

    return False


def line_is_inside_server_guard(method, line_number, lines):
    if method is None:
        return False
    return line_is_inside_server_ifdef(
        method, line_number, lines
    ) or line_is_inside_server_if_guard(method, line_number, lines)


def line_is_inside_try_block(lines, line_index, method):
    method_end_index = method["end_line"] - 1 if method else len(lines) - 1
    start_index = method["start_line"] - 1 if method else 0

    for index in range(start_index, line_index + 1):
        if not TRY_BLOCK_RE.match(lines[index]):
            continue
        end_line = find_block_end_line(lines, index, method_end_index)
        if index + 1 <= line_index + 1 <= end_line:
            return True

    return False


def find_matching_endif_line(lines, ifdef_start_line):
    balance = 0
    for index in range(ifdef_start_line - 1, len(lines)):
        line = lines[index]
        opens_supported_ifdef = ES_EMPTY_IFDEF_RE_OPEN.match(line) is not None
        opens_unsupported_ifdef = (
            ES_EMPTY_IFDEF_RE_UNSUPPORTED_IFDEF.match(line) is not None
        )
        opens_unsupported_if = (
            ES_EMPTY_IFDEF_RE_UNSUPPORTED_DIRECTIVE.match(line) is not None
            and unsupported_directive_opens_block(line)
        )
        if opens_supported_ifdef or opens_unsupported_ifdef or opens_unsupported_if:
            balance += 1
            continue

        if ES_EMPTY_IFDEF_RE_CLOSE.match(line):
            balance -= 1
            if balance == 0:
                return index + 1

    return len(lines)


def compute_ifdef_then_else_path(lines, end_line_exclusive):
    """Return [(macro, branch), ...] active at end_line_exclusive (0-based).

    branch is 'then', 'else', or 'elif'. Used to decide whether two
    declarations sit in mutually exclusive preprocessor arms.
    """
    stack = []
    for index in range(end_line_exclusive):
        line = lines[index]
        open_match = ES_EMPTY_IFDEF_RE_OPEN.match(line)
        if open_match:
            stack.append(
                {
                    "macro": open_match.group("macro"),
                    "branch": "then",
                }
            )
            continue

        if ES_EMPTY_IFDEF_RE_UNSUPPORTED_IFDEF.match(line):
            stack.append({"macro": None, "branch": "then"})
            continue

        if ES_EMPTY_IFDEF_RE_UNSUPPORTED_DIRECTIVE.match(line):
            if unsupported_directive_opens_block(line):
                stack.append({"macro": None, "branch": "then"})
            elif stack:
                if re.match(r"^\s*#else\b", line):
                    stack[-1] = {
                        "macro": stack[-1]["macro"],
                        "branch": "else",
                    }
                elif re.match(r"^\s*#elif\b", line):
                    stack[-1] = {
                        "macro": stack[-1]["macro"],
                        "branch": "elif",
                    }
            continue

        if ES_EMPTY_IFDEF_RE_CLOSE.match(line):
            if stack:
                stack.pop()

    return [(frame["macro"], frame["branch"]) for frame in stack]


def ifdef_paths_are_exclusive(path_a, path_b):
    """True when the two paths split on then/else/elif of the same macro."""
    limit = min(len(path_a), len(path_b))
    index = 0
    while index < limit and path_a[index] == path_b[index]:
        index += 1
    if index >= len(path_a) or index >= len(path_b):
        return False
    macro_a, branch_a = path_a[index]
    macro_b, branch_b = path_b[index]
    if macro_a is None or macro_a != macro_b:
        return False
    return branch_a != branch_b


def find_server_ifdef_block_for_line(lines, line_number):
    stack = []
    for index in range(line_number - 1):
        line = lines[index]
        open_match = ES_EMPTY_IFDEF_RE_OPEN.match(line)
        if open_match:
            stack.append(
                {
                    "macro": open_match.group("macro"),
                    "directive": open_match.group("directive"),
                    "line": index + 1,
                }
            )
            continue

        if ES_EMPTY_IFDEF_RE_UNSUPPORTED_IFDEF.match(line):
            stack.append(
                {"macro": None, "directive": "unsupported", "line": index + 1}
            )
            continue

        if ES_EMPTY_IFDEF_RE_UNSUPPORTED_DIRECTIVE.match(line):
            if unsupported_directive_opens_block(line):
                stack.append(
                    {"macro": None, "directive": "unsupported", "line": index + 1}
                )
            elif stack:
                stack[-1] = {
                    "macro": None,
                    "directive": "unsupported",
                    "line": index + 1,
                }
            continue

        if ES_EMPTY_IFDEF_RE_CLOSE.match(line):
            if stack:
                stack.pop()

    for frame in reversed(stack):
        if frame["macro"] == "SERVER" and frame["directive"] == "ifdef":
            return frame["line"], find_matching_endif_line(lines, frame["line"])

    return None
