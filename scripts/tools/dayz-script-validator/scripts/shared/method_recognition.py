import re


PARAMS_READ_CONTEXT_PARAM_RE = re.compile(r"^\s*ParamsReadContext\s+(?P<name>\w+)\b")


# What METHOD_SIGNATURE_RE matches before the "(" that opens the parameters.
# It holds no "(", so that "(" is the first one of the line the signature
# starts on.
METHOD_SIGNATURE_HEAD = (
    r"(?P<indent>\s*)"
    r"(?:override\s+|static\s+|protected\s+|private\s+)*"
    r"(?P<return_type>\w[\w\s]*?)\s+"
    r"(?P<name>\w+)"
    r"\s*"
)

METHOD_SIGNATURE_RE = re.compile(
    r"^" + METHOD_SIGNATURE_HEAD
    + r"\((?P<params>[^)]*)\)"
    r"\s*(?P<brace>\{)?.*$"
)

METHOD_SIGNATURE_HEAD_RE = re.compile(METHOD_SIGNATURE_HEAD)


def count_braces(line):
    return line.count("{") - line.count("}")


def collect_method_signature(lines, start_index):
    # Joined once at the end: a "(" that never closes reaches the end of the file.
    parts = [lines[start_index]]
    end_index = start_index
    open_parens = parts[0].count("(")
    close_parens = parts[0].count(")")

    while open_parens > close_parens and end_index + 1 < len(lines):
        end_index += 1
        next_line = lines[end_index].strip()
        parts.append(next_line)
        open_parens += next_line.count("(")
        close_parens += next_line.count(")")

    return " ".join(parts), end_index


def may_start_method_signature(line):
    """False when no signature collected from `line` can match METHOD_SIGNATURE_RE."""
    open_at = line.find("(")
    return open_at >= 0 and METHOD_SIGNATURE_HEAD_RE.fullmatch(line[:open_at]) is not None


def find_block_end_line(lines, brace_line_index, max_line_index=None):
    if max_line_index is None:
        max_line_index = len(lines) - 1

    balance = 0
    seen_open = False
    for index in range(brace_line_index, max_line_index + 1):
        line = lines[index]
        if "{" in line:
            seen_open = True
        balance += count_braces(line)
        if seen_open and balance <= 0:
            return index + 1

    return max_line_index + 1


def find_signature_brace_line(lines, signature_index, signature_end_index, match):
    if match.group("brace"):
        for index in range(signature_index, signature_end_index + 1):
            if "{" in lines[index]:
                return index
        return signature_end_index

    for index in range(signature_end_index + 1, len(lines)):
        stripped = lines[index].strip()
        if stripped == "":
            continue
        if stripped.startswith("{"):
            return index
        return None

    return None


class _Signatures:
    """collect_method_signature at any line of one text, read once.

    From a "(" that never closes, each collection ran to the end of the file:
    method headers split by #ifdef branches took 21 s for 135 KB (second Codex
    review of #113, J2). The end index comes from the parenthesis depth before
    each line, and the signature stops with the line that holds the first
    character after its first ")" that is not a space: what follows changes no
    group of METHOD_SIGNATURE_RE.
    """

    def __init__(self, lines):
        self.lines = lines
        self.stripped = [line.strip() for line in lines]
        count = len(lines)
        depth = [0]
        for line in lines:
            depth.append(depth[-1] + line.count("(") - line.count(")"))
        # Each start ends on the line before the first later depth at or below
        # its own, or on the last line.
        self.ends = [count - 1] * count
        later = [count]
        for start in range(count - 1, -1, -1):
            while later and depth[later[-1]] > depth[start]:
                later.pop()
            if later:
                self.ends[start] = later[-1] - 1
            later.append(start)
        # From each line, the first one with a ")" and the first one not blank.
        self.next_close = [count] * (count + 1)
        self.next_text = [count] * (count + 1)
        for index in range(count - 1, -1, -1):
            self.next_close[index] = (
                index if ")" in lines[index] else self.next_close[index + 1]
            )
            self.next_text[index] = (
                index if self.stripped[index] else self.next_text[index + 1]
            )

    def collect(self, start):
        """What METHOD_SIGNATURE_RE reads of collect_method_signature(lines, start),
        and its end index. `start` holds a "(" (may_start_method_signature)."""
        end = self.ends[start]
        first = self.lines[start]
        close_at = first.find(")", first.find("("))
        if close_at >= 0:
            closing, after = start, first[close_at + 1:]
        else:
            closing = self.next_close[start + 1]
            if closing > end:
                return first, end  # no ")": no match, as on the whole signature
            text = self.stripped[closing]
            after = text[text.find(")") + 1:]
        last = closing
        if not after.strip() and self.next_text[closing + 1] <= end:
            last = self.next_text[closing + 1]
        return " ".join([first] + self.stripped[start + 1:last + 1]), end


def find_method_regions(stripped_source):
    lines = stripped_source.split("\n")
    signatures = None
    methods = []
    index = 0

    while index < len(lines):
        if not may_start_method_signature(lines[index]):
            index += 1
            continue
        if signatures is None:
            signatures = _Signatures(lines)
        signature, signature_end_index = signatures.collect(index)
        match = METHOD_SIGNATURE_RE.match(signature)
        if not match:
            index += 1
            continue

        brace_line_index = find_signature_brace_line(
            lines, index, signature_end_index, match
        )
        if brace_line_index is None:
            index += 1
            continue

        end_line = find_block_end_line(lines, brace_line_index)
        methods.append(
            {
                "start_line": index + 1,
                "end_line": end_line,
                "brace_line": brace_line_index + 1,
                "return_type": " ".join(match.group("return_type").split()),
                "name": match.group("name"),
                "params": match.group("params"),
            }
        )
        index = end_line

    return methods


def find_method_for_line(methods, line_number):
    containing = [
        method
        for method in methods
        if method["start_line"] <= line_number <= method["end_line"]
    ]
    if not containing:
        return None
    return max(containing, key=lambda method: method["start_line"])


def find_params_read_context_param_name(method):
    if method is None:
        return None
    for param in method["params"].split(","):
        match = PARAMS_READ_CONTEXT_PARAM_RE.match(param.strip())
        if match:
            return match.group("name")
    return None


def first_param_is_params_read_context(method):
    if method is None:
        return False
    first_param = method["params"].split(",", 1)[0].strip()
    return PARAMS_READ_CONTEXT_PARAM_RE.match(first_param) is not None


def method_is_onstoreload(method):
    if method is None:
        return False
    if method["name"] != "OnStoreLoad":
        return False
    if method["return_type"] != "bool":
        return False
    return first_param_is_params_read_context(method)


def method_is_onrpc(method):
    if method is None:
        return False
    return method["name"] == "OnRPC" and method["return_type"] == "void"


def find_next_nonblank_line(lines, start_index, max_index):
    for index in range(start_index, max_index + 1):
        if lines[index].strip() != "":
            return index
    return None


def find_if_body_range(lines, if_line_index, method_end_index):
    line = lines[if_line_index]
    if "{" in line:
        return if_line_index + 1, find_block_end_line(
            lines, if_line_index, method_end_index
        )

    close_paren = line.rfind(")")
    if close_paren != -1 and line[close_paren + 1 :].strip() != "":
        return if_line_index + 1, if_line_index + 1

    next_index = find_next_nonblank_line(lines, if_line_index + 1, method_end_index)
    if next_index is None:
        return if_line_index + 1, if_line_index + 1

    if "{" in lines[next_index]:
        return if_line_index + 1, find_block_end_line(
            lines, next_index, method_end_index
        )

    return next_index + 1, next_index + 1


def find_inline_pattern_line(pattern, lines, line_index):
    if pattern.search(lines[line_index]):
        return line_index
    if line_index == 0:
        return None
    combined = lines[line_index - 1] + " " + lines[line_index]
    if pattern.search(combined):
        return line_index - 1
    return None
