"""PostToolUse hook: fast syntax check for DayZ config and layout files.

Runs after Edit, Write and MultiEdit. Checks only:
  - config.cpp anywhere, and *.cpp / *.hpp under a workspace/ folder: balanced
    braces, '};' after every class body, ';' after every property and array,
    '[]' on array properties, ',' (not ';') between array elements.
  - *.layout: the brace property format DayZ uses (not XML), balanced blocks,
    child widgets inside the parent's anonymous '{ }' children block,
    properties inside a widget block.

Clean files produce no output. On a problem it prints the documented
PostToolUse JSON ({"decision": "block", "reason": ...}) so Claude sees each
file:line and the fix next to the tool result (the edit itself already ran).
Any failure of the hook itself exits 0 silently: a checker bug must never get
in the way of an edit. https://code.claude.com/docs/en/hooks#posttooluse

Manual use: python hooks/edit_check.py --file <path>   (prints problems, exit 1)
"""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

MAX_PROBLEMS = 5
MAX_BYTES = 2 * 1024 * 1024  # bigger files are generated, not hand-edited; keeps the hook fast


@dataclass
class Problem:
    line: int
    message: str


# ---------------------------------------------------------------- relevance

def file_kind(path: str) -> Optional[str]:
    """'config' or 'layout' for files this hook checks, else None."""
    p = Path(path)
    name = p.name.lower()
    if name.endswith(".layout"):
        return "layout"
    if name == "config.cpp":
        return "config"
    if p.suffix.lower() in (".cpp", ".hpp") and any(part.lower() == "workspace" for part in p.parts[:-1]):
        return "config"
    return None


# ---------------------------------------------------------- config tokenizer

@dataclass
class Tok:
    kind: str  # ident, num, str, punct
    text: str
    line: int


class TokenizeError(Exception):
    def __init__(self, line: int, message: str):
        super().__init__(message)
        self.line = line
        self.message = message


# Names may start with digits (class 1kHz_mono_SoundShader), so try this before numbers.
_IDENT = re.compile(r"[0-9]*[A-Za-z_][A-Za-z0-9_]*")
_NUM = re.compile(r"[0-9]+(?:\.[0-9]*)?(?:[eE][+-]?[0-9]+)?|\.[0-9]+(?:[eE][+-]?[0-9]+)?|0[xX][0-9A-Fa-f]+")


def tokenize(text: str) -> list[Tok]:
    toks: list[Tok] = []
    i, n, line = 0, len(text), 1
    at_line_start = True
    while i < n:
        c = text[i]
        if c == "\n":
            line += 1
            i += 1
            at_line_start = True
            continue
        if c in " \t\r\f\v﻿":
            i += 1
            continue
        if c == "#" and at_line_start:
            # Preprocessor directive: skip to end of line, honoring '\' continuations.
            while i < n and text[i] != "\n":
                if text[i] == "\\" and i + 1 < n and text[i + 1] == "\n":
                    line += 1
                    i += 2
                    continue
                i += 1
            continue
        at_line_start = False
        if text.startswith("//", i):
            while i < n and text[i] != "\n":
                i += 1
            continue
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            if end < 0:
                raise TokenizeError(line, "'/*' comment is never closed; add '*/'")
            line += text.count("\n", i, end)
            i = end + 2
            continue
        if c in "\"'":
            start_line, j = line, i + 1
            while True:
                if j >= n or text[j] == "\n":
                    raise TokenizeError(start_line, f"string starting with {c} is not closed on this line; add the closing {c}")
                if text[j] == c:
                    if j + 1 < n and text[j + 1] == c:  # "" is an escaped quote in BI configs
                        j += 2
                        continue
                    break
                j += 1
            toks.append(Tok("str", text[i : j + 1], line))
            i = j + 1
            continue
        m = _IDENT.match(text, i)
        if m:
            toks.append(Tok("ident", m.group(), line))
            i = m.end()
            continue
        m = _NUM.match(text, i)
        if m:
            toks.append(Tok("num", m.group(), line))
            i = m.end()
            continue
        if text.startswith("+=", i):
            toks.append(Tok("punct", "+=", line))
            i += 2
            continue
        toks.append(Tok("punct", c, line))
        i += 1
    return toks


# -------------------------------------------------------------- config parser

class ConfigParser:
    """Recursive parser for the class / property / array grammar of config.cpp."""

    def __init__(self, toks: list[Tok]):
        self.t = toks
        self.i = 0
        self.problems: list[Problem] = []

    # helpers
    def peek(self, k: int = 0) -> Optional[Tok]:
        j = self.i + k
        return self.t[j] if j < len(self.t) else None

    def is_p(self, tok: Optional[Tok], text: str) -> bool:
        return tok is not None and tok.kind == "punct" and tok.text == text

    def add(self, line: int, msg: str) -> None:
        if len(self.problems) < MAX_PROBLEMS:
            self.problems.append(Problem(line, msg))

    def starts_item(self, k: int = 0) -> bool:
        """Does the token at offset k begin a new class-body item?"""
        a, b = self.peek(k), self.peek(k + 1)
        if a is None or a.kind != "ident":
            return False
        if a.text in ("class", "delete"):
            return True
        return self.is_p(b, "=") or self.is_p(b, "+=") or (self.is_p(b, "[") and self.is_p(self.peek(k + 2), "]"))

    def expect_semicolon(self, after_line: int, what: str) -> None:
        if self.is_p(self.peek(), ";"):
            self.i += 1
        else:
            self.add(after_line, f"missing ';' after {what}")

    # grammar
    def parse(self) -> list[Problem]:
        self.body(None)
        return self.problems

    def body(self, cls: Optional[tuple[str, int]]) -> None:
        while len(self.problems) < MAX_PROBLEMS:
            tok = self.peek()
            if tok is None:
                if cls:
                    self.add(cls[1], f"class {cls[0]} opened here is never closed; add '}};' at its end")
                return
            if self.is_p(tok, "}"):
                if cls:
                    return
                self.add(tok.line, "unexpected '}' with no open class; remove it or check the braces above")
                self.i += 1
                continue
            if self.is_p(tok, ";"):
                self.i += 1  # a stray ';' is harmless
                continue
            self.item()

    def item(self) -> None:
        tok = self.peek()
        assert tok is not None
        if tok.kind == "ident" and tok.text == "class":
            self.class_def()
            return
        if tok.kind == "ident" and tok.text == "delete":
            self.i += 1
            name = self.peek()
            if name is not None and name.kind == "ident":
                self.i += 1
            self.expect_semicolon(tok.line, f"'delete {name.text if name else ''}'")
            return
        if tok.kind == "ident" and tok.text == "enum" and self.is_p(self.peek(1), "{"):
            self.i += 1
            self.skip_braced()
            self.expect_semicolon(tok.line, "enum block")
            return
        if self.starts_item():
            self.property()
            return
        if tok.kind == "ident":
            nxt = self.peek(1)
            if self.is_p(nxt, "("):  # macro call such as MY_MACRO(a, b)
                self.i += 1
                self.skip_parens()
                if self.is_p(self.peek(), ";"):
                    self.i += 1
                return
            if nxt is not None and nxt.line == tok.line and nxt.kind in ("num", "str"):
                self.add(tok.line, f"missing '=' between '{tok.text}' and its value")
                self.i += 2
                if self.is_p(self.peek(), ";"):
                    self.i += 1
                return
            self.i += 1  # bare macro name; can't judge it, skip
            return
        self.add(tok.line, f"unexpected '{tok.text}' in a class body; expected 'class', a property or '}}'")
        self.i += 1

    def class_def(self) -> None:
        kw = self.peek()
        assert kw is not None
        self.i += 1
        name = self.peek()
        if name is None or name.kind != "ident":
            self.add(kw.line, "'class' must be followed by a class name")
            return
        self.i += 1
        if self.is_p(self.peek(), ":"):
            self.i += 1
            base = self.peek()
            if base is None or base.kind != "ident":
                self.add(name.line, f"class {name.text}: ':' must be followed by the base class name")
            else:
                self.i += 1
        nxt = self.peek()
        if self.is_p(nxt, ";"):  # forward declaration: class Foo;
            self.i += 1
            return
        if not self.is_p(nxt, "{"):
            self.add(name.line, f"class {name.text} needs '{{ ... }};' or ';' (external declaration)")
            return
        self.i += 1
        self.body((name.text, name.line))
        close = self.peek()
        if close is None:
            return  # body() already reported the unclosed class
        self.i += 1  # the '}'
        self.expect_semicolon(close.line, f"'}}' closing class {name.text}; write '}};'")

    def property(self) -> None:
        name = self.peek()
        assert name is not None
        self.i += 1
        is_array = False
        if self.is_p(self.peek(), "["):
            is_array = True
            self.i += 2  # '[' ']'
        op = self.peek()
        self.i += 1  # '=' or '+='
        assert op is not None
        if self.is_p(self.peek(), "{"):
            if not is_array:
                self.add(name.line, f"'{name.text}' is given an array; declare it as '{name.text}[]'")
            open_tok = self.peek()
            assert open_tok is not None
            end_line = self.array(open_tok.line, name.text)
            if end_line is not None:
                self.expect_semicolon(end_line, f"array '{name.text}[]'")
            return
        self.scalar(name)

    def scalar(self, name: Tok) -> None:
        depth = 0
        last_line = name.line
        while True:
            tok = self.peek()
            if tok is None:
                self.add(last_line, f"missing ';' after '{name.text}'")
                return
            if depth == 0:
                if self.is_p(tok, ";"):
                    self.i += 1
                    return
                if self.is_p(tok, "}"):
                    self.add(last_line, f"missing ';' after '{name.text}'")
                    return
                if tok.line > last_line and self.starts_item():
                    self.add(last_line, f"missing ';' after '{name.text}'")
                    return
            if self.is_p(tok, "("):
                depth += 1
            elif self.is_p(tok, ")"):
                depth = max(0, depth - 1)
            last_line = tok.line
            self.i += 1

    def array(self, open_line: int, name: str) -> Optional[int]:
        """Parse '{ ... }' starting at the current '{'. Returns the closing line, or None at EOF."""
        self.i += 1
        last_line = open_line
        depth = 0
        while True:
            tok = self.peek()
            if tok is None:
                self.add(open_line, f"array '{name}[]' opened here is never closed; add '}};'")
                return None
            if self.is_p(tok, "{"):
                end = self.array(tok.line, name)
                if end is None:
                    return None
                last_line = end
                continue
            if self.is_p(tok, "}") and depth == 0:
                self.i += 1
                return tok.line
            if self.is_p(tok, ";") and depth == 0:
                self.add(tok.line, f"';' inside array '{name}[]'; separate elements with ',' and end with '}};'")
                self.i += 1
                continue
            if tok.line > last_line and depth == 0 and self.starts_item() and self.peek(1) is not None:
                # A new property inside an array means the array's '};' is missing.
                self.add(last_line, f"array '{name}[]' is not closed before the next property; add '}};'")
                return last_line
            if self.is_p(tok, "("):
                depth += 1
            elif self.is_p(tok, ")"):
                depth = max(0, depth - 1)
            last_line = tok.line
            self.i += 1

    def skip_parens(self) -> None:
        depth = 0
        while (tok := self.peek()) is not None:
            self.i += 1
            if self.is_p(tok, "("):
                depth += 1
            elif self.is_p(tok, ")"):
                depth -= 1
                if depth == 0:
                    return

    def skip_braced(self) -> None:
        depth = 0
        while (tok := self.peek()) is not None:
            self.i += 1
            if self.is_p(tok, "{"):
                depth += 1
            elif self.is_p(tok, "}"):
                depth -= 1
                if depth == 0:
                    return


def check_config(text: str) -> list[Problem]:
    try:
        toks = tokenize(text)
    except TokenizeError as e:
        return [Problem(e.line, e.message)]
    return ConfigParser(toks).parse()


# --------------------------------------------------------------- layout check

# Token-based: Workbench writes one property per line, but hand-written layouts
# also put a whole widget on one line (TextWidgetClass Cell0 { text "" size 0 34 }).
_LAYOUT_TOKEN = re.compile(r'"[^"\n]*"|[{}]|[^\s{}"]+|"')


def check_layout(text: str) -> list[Problem]:
    problems: list[Problem] = []

    def add(line: int, msg: str) -> None:
        if len(problems) < MAX_PROBLEMS:
            problems.append(Problem(line, msg))

    text = text.lstrip("﻿")  # a UTF-8 BOM is not part of the first widget header
    first = text.lstrip(" \t\r\n")
    if first.startswith("<"):
        line = text[: len(text) - len(first)].count("\n") + 1
        return [Problem(line, "this is XML; DayZ .layout files use the brace format: "
                              "'FrameWidgetClass rootFrame {' then one 'property value' per line, "
                              "children inside a bare '{ }' block, closing '}'")]

    # Stack entries: ("widget" | "children", name, line). Top level acts like a children block.
    stack: list[tuple[str, str, int]] = []
    roots = 0
    pending: list[tuple[str, int]] = []  # words since the last brace, for headers and stray properties

    def flush_stray(context: str) -> None:
        """Words in a children block or at top level that never became a widget header."""
        if pending:
            add(pending[0][1], f"property '{pending[0][0]}' is {context}; move it into a widget's own block")
            pending.clear()

    for lineno, raw in enumerate(text.splitlines(), 1):
        if raw.strip().startswith("//"):
            continue
        for tok in _LAYOUT_TOKEN.findall(raw):
            top = stack[-1][0] if stack else None
            if tok == '"':
                add(lineno, "unbalanced '\"' on this line; close the string")
                break
            if tok == "{":
                header = [w for w, ln in pending if ln == lineno]
                if top == "widget":
                    pending.clear()
                    if header:
                        add(lineno, f"child widget {header[-1]} must be inside the parent's bare '{{ }}' children block, "
                                    "not directly in the parent's property block")
                        stack.append(("widget", header[-1], lineno))
                    else:
                        stack.append(("children", "", lineno))
                    continue
                context = "outside any widget" if top is None else "in a children block"
                stray = pending[: len(pending) - len(header)]
                if stray:
                    add(stray[0][1], f"property '{stray[0][0]}' is {context}; move it into a widget's own block")
                pending.clear()
                if not header:
                    add(lineno, "a bare '{' children block must sit directly inside a widget block")
                    stack.append(("children", "", lineno))
                    continue
                if len(header) > 2 or not re.match(r"[A-Za-z_]\w*$", header[0]):
                    add(lineno, "a widget must open as '<Type>WidgetClass <name> {'")
                name = header[-1]
                if top is None:
                    roots += 1
                    if roots > 1:
                        add(lineno, f"second root widget {name}; a .layout has exactly one root, nest it inside the first")
                stack.append(("widget", name, lineno))
                continue
            if tok == "}":
                if top != "widget":
                    flush_stray("outside any widget" if top is None else "in a children block")
                pending.clear()
                if not stack:
                    add(lineno, "unexpected '}' with no open block; remove it or check the braces above")
                else:
                    stack.pop()
                continue
            pending.append((tok, lineno))
        # End of line: in a children block or at top level a line of words that didn't
        # end in '{' is a stray property (a widget header always ends its line with '{').
        top = stack[-1][0] if stack else None
        if top == "widget":
            pending.clear()
        elif pending and pending[-1][1] == lineno:
            flush_stray("outside any widget" if top is None else "in a children block")
    for kind, name, lineno in reversed(stack):
        what = f"widget {name}" if kind == "widget" else "children block"
        add(lineno, f"{what} opened here is never closed; add '}}'")
    if roots == 0 and not problems and text.strip():
        add(1, "no root widget; a .layout starts with '<Type>WidgetClass <name> {'")
    return problems


# --------------------------------------------------------------------- driver

def check_file(path: Path) -> list[Problem]:
    kind = file_kind(str(path))
    if kind is None or not path.is_file() or path.stat().st_size > MAX_BYTES:
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    return check_config(text) if kind == "config" else check_layout(text)


def format_reason(path: Path, problems: list[Problem]) -> str:
    lines = [f"Syntax check found {len(problems)} problem(s) in {path.name}. Fix them before moving on:"]
    lines += [f"{path}:{p.line}: {p.message}" for p in problems]
    return "\n".join(lines)


def shadowed_by_project() -> bool:
    """True when this is the plugin copy and the project has its own copy of the hook.

    A clone with the agentic-z plugin enabled wires each hook twice: once from
    .claude/settings.json and once from the plugin's hooks.json. The plugin
    copy then steps aside so the project copy runs alone.
    """
    project = os.environ.get("CLAUDE_PROJECT_DIR")
    if not project:
        return False
    here = Path(__file__).resolve()
    root = Path(project).resolve()
    if here.is_relative_to(root):
        return False
    return (root / "hooks" / here.name).is_file()


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[0] == "--file":
        path = Path(argv[1])
        problems = check_file(path)
        if problems:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # a cp1252 console cannot print every message
            print(format_reason(path, problems))
            return 1
        return 0
    if shadowed_by_project():
        return 0
    try:
        data = json.loads(sys.stdin.read() or "{}")
        file_path = (data.get("tool_input") or {}).get("file_path")
        if not file_path:
            return 0
        path = Path(file_path)
        problems = check_file(path)
    except Exception:  # never let a checker bug get in the way of an edit
        return 0
    if problems:
        print(json.dumps({"decision": "block", "reason": format_reason(path, problems)}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
