"""PreToolUse hook: block writes to other mods while /dayz-scope-mod is active.

/dayz-scope-mod <Mod> records the active mod in
<project>/.claude/local-memory/dayz-active-scope.json (written by
.claude/skills/dayz-scope-mod/scope.py) and adds Edit deny rules for the
sibling mods that existed at that moment. This hook backs those rules up with
a reason Claude can act on, and also covers mod folders created after the
scope was set. While a scope is active, every top-level folder under
workspace/ other than the active mod counts as a mod, including one that does
not exist yet, so the files of a sibling mod are blocked before its
config.cpp is written. The exceptions are helper folders, whose names start
with an underscore (workspace/_notes/), and dotted folders (workspace/.git/).
A helper folder that has config.cpp or $PBOPREFIX$ at its root, or that the
edit gives one, is a mod again. The guarded places are:

  - <project>/workspace/<Other>/...   any folder other than the active mod, as above
  - P:\\<Other>\\... and P:\\Mods\\@<Other>\\...   when <Other> is a mod in workspace/
    (a folder there with config.cpp or $PBOPREFIX$ at its root)
  - <DayZ game>\\!Workshop\\@<Other>\\...   the real folder behind the P:\\Mods
    junction, when <Other> is a mod in workspace/. The game folder is found
    the way scope.py finds it (/dayz-preflight's find_dayz_game:
    $DAYZ_GAME_PATH, then the Steam libraries). Without preflight.py or a
    game install this one place is not checked; the others still are.

A path is read the way Windows reads it: a leading \\\\?\\ or \\\\.\\ is dropped,
trailing dots and spaces are cut from each name (workspace\\OtherMod.\\a.c
lands in OtherMod) and '..' segments are collapsed. The path is then checked
a second time with junctions, symlinks and short 8.3 names resolved, so a link
inside the active mod that points into another mod is caught too.

The hook matches Edit, Write and MultiEdit (tool_input.file_path) and Bash and
PowerShell (tool_input.command). A shell command is split at ;, |, &&, || and
new lines, and these write targets are checked, with relative paths read
against the hook input's cwd and any cd, pushd, popd, Set-Location,
Push-Location or Pop-Location before them:

  - redirects: >, >>, 2>, &>, *> (2>&1 and other stream copies are not files)
  - every path argument of rm, mv, touch, mkdir, rmdir, tee, truncate,
    unlink, Set-Content, Add-Content, Out-File, Clear-Content, New-Item,
    Remove-Item, Move-Item, Rename-Item and their aliases
  - the destination of cp, Copy-Item, install, rsync, scp, ln,
    Expand-Archive and Compress-Archive (-Destination, -DestinationPath, -t,
    or the last path; Expand-Archive with only the zip unpacks into the
    current folder), and of robocopy and xcopy (their second path);
    reading from another mod is fine
  - the files of sed -i and perl -i
  - the same inside bash -c, sh -c, powershell -Command, pwsh -c and cmd /c

$CLAUDE_PROJECT_DIR, $env:NAME, ${NAME}, $NAME and a leading ~ are expanded
first, and heredoc bodies and # comments are skipped. Writes the hook cannot
see from the command line still go through: a script file, python -c,
node -e, git checkout, or a .NET call such as [IO.File]::WriteAllText.

No scope file means no scope: the hook exits silently. A malformed hook input
or state file (not JSON, not an object, no active_mod) also exits silently,
so the hook never blocks on its own bug.
Output format: https://code.claude.com/docs/en/hooks#pretooluse-decision-control
"""
from __future__ import annotations

import importlib.util
import json
import os
import posixpath
import re
import sys
from pathlib import Path
from typing import Iterator, Optional

SCOPE_STATE = Path(".claude") / "local-memory" / "dayz-active-scope.json"
PREFLIGHT = Path(__file__).resolve().parents[1] / ".claude" / "skills" / "dayz-preflight" / "preflight.py"
EDIT_TOOLS = {"Edit", "Write", "MultiEdit"}
SHELL_TOOLS = {"Bash", "PowerShell"}


def _parts(path: str) -> list[str]:
    """Split on both separators; 'P:\\A\\b' and '/p/A/b' both give ['p:', 'A', 'b'].

    The path is read the way Win32 reads it, so no spelling slips past the
    guard: a leading \\\\?\\ or \\\\.\\ is dropped, trailing dots and spaces are
    cut from each name (workspace/OtherMod./a.c lands in OtherMod), and '..'
    segments are collapsed (workspace/MyVest/../OtherMod/a.c is
    workspace/OtherMod/a.c).
    """
    s = path.replace("\\", "/")
    if s.startswith(("//?/", "//./")):  # Win32 long-path and device prefixes
        s = s[4:]
    m = re.match(r"^/([A-Za-z])/(.*)$", s)  # Git Bash form /p/Foo
    if m:
        s = f"{m.group(1)}:/{m.group(2)}"
    drive, rest = (s[:2], s[2:]) if re.match(r"^[A-Za-z]:", s) else ("", s)
    rest = "/".join(seg if seg in (".", "..") else seg.rstrip(". ") for seg in rest.split("/"))
    rest = posixpath.normpath("/" + rest) if drive else posixpath.normpath(rest)  # '..' stops at the drive root, as on Windows
    return [p for p in ([drive] if drive else []) + rest.split("/") if p not in ("", ".")]


def _norm(path: str) -> list[str]:
    return [p.lower() for p in _parts(path)]


MOD_MARKERS = ("config.cpp", "$PBOPREFIX$")


def _is_mod_dir(folder: Path) -> bool:
    return any((folder / m).is_file() for m in MOD_MARKERS)


def workspace_mods(project: Path) -> list[str]:
    ws = project / "workspace"
    if not ws.is_dir():
        return []
    return [p.name for p in ws.iterdir() if p.is_dir() and not p.name.startswith(".") and _is_mod_dir(p)]


def game_workshop_dir() -> Optional[Path]:
    """<DayZ game>\\!Workshop, found as scope.py finds it (preflight's find_dayz_game), or None."""
    if not PREFLIGHT.is_file():
        return None
    spec = importlib.util.spec_from_file_location("scope_guard_preflight", PREFLIGHT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    game = module.find_dayz_game()
    return game / "!Workshop" if game is not None else None


def _deployed_mod(parts: list[str], low: list[str], root: list[str], known: set[str]) -> Optional[str]:
    """The mod of a path at or inside <root>/@<mod>/, when <mod> is a workspace mod."""
    n = len(root)
    if len(low) > n and low[:n] == root and low[n].startswith("@") and low[n][1:] in known:
        return parts[n][1:]
    return None


def _real_name(folder: Path) -> str:
    """The folder's own long name (an 8.3 short name such as MYVEST~1 becomes MyVestLonger)."""
    try:
        return Path(os.path.realpath(folder)).name if folder.exists() else folder.name
    except (OSError, ValueError):
        return folder.name


def target_mod(file_path: str, project: Path, mods: list[str]) -> Optional[str]:
    """The mod a path belongs to, as spelled in the path, or None if it isn't inside a mod folder.

    A path that is the mod folder itself (rm -rf workspace/OtherMod) counts, for
    a known mod. Under workspace/, a folder that is not a known mod counts as
    one too unless its name starts with '_' or '.' (see the module docstring).
    """
    parts = _parts(file_path)
    low = [p.lower() for p in parts]
    known = {m.lower() for m in mods}
    ws = _norm(str(project / "workspace"))
    if len(low) > len(ws) and low[: len(ws)] == ws:
        name = parts[len(ws)]
        if name.lower() in known:
            return name
        if len(low) == len(ws) + 1 or name.startswith("."):
            return None  # a file directly in workspace/, or a dotted folder
        creates_marker = len(low) == len(ws) + 2 and low[-1] in {m.lower() for m in MOD_MARKERS}
        if name.startswith("_") and not creates_marker:
            return None  # a helper folder
        return _real_name(project / "workspace" / name)
    if low and low[0] == "p:":
        deployed = _deployed_mod(parts, low, ["p:", "mods"], known)
        if deployed:
            return deployed
        if len(low) > 1 and low[1] in known:
            return parts[1]
    if "!workshop" in low:  # look the game up only for a path that could be inside it
        workshop = game_workshop_dir()
        if workshop is not None:
            return _deployed_mod(parts, low, _norm(str(workshop)), known)
    return None


def _other_mod(path: str, project: Path, active: str, mods: list[str]) -> Optional[str]:
    """The mod other than the active one that an absolute path lands in, or None."""
    try:
        real = os.path.realpath(path)
    except (OSError, ValueError):
        real = path
    # The path as written, then with links and 8.3 names resolved (against the
    # resolved project, so both sides are spelled the same way).
    for spelled, root in ((path, project), (real, Path(os.path.realpath(project)))):
        other = target_mod(spelled, root, mods)
        if other is not None and other.lower() != active.lower():
            return other
    return None


def _absolute(path: str, cwd: str) -> str:
    if path.startswith("~"):
        path = str(Path.home()) + path[1:]
    if re.match(r"^(?:[A-Za-z]:|[\\/])", path):
        return path
    return cwd.rstrip("\\/") + "/" + path


# ---- shell commands ---------------------------------------------------------

_ALL_ARGS = {
    "rm", "mv", "touch", "mkdir", "rmdir", "tee", "truncate", "unlink", "shred",
    "set-content", "sc", "add-content", "ac", "out-file", "clear-content", "clc",
    "new-item", "ni", "md", "remove-item", "ri", "del", "erase", "rd",
    "move-item", "mi", "move", "rename-item", "ren", "rni",
}
_DEST = {"cp", "copy", "copy-item", "cpi", "install", "rsync", "scp", "ln", "expand-archive", "compress-archive"}
_DEST_SECOND = {"robocopy", "xcopy"}  # robocopy <src> <dst> [files] [/opts]
_IN_PLACE = {"sed", "perl"}
_WRAPPERS = {"sudo", "env", "command", "nohup", "time", "exec", "builtin", "nice", "xargs"}
# Bash keywords that can start a command: in `then rm x` the command is rm, not then.
_KEYWORDS = {"if", "then", "elif", "else", "do", "while", "until", "!"}
_CD = {"cd", "pushd", "push-location", "chdir", "set-location", "sl"}
_PUSHD = {"pushd", "push-location"}  # also save the old folder, for popd
_POPD = {"popd", "pop-location"}
_POSIX_SHELLS = {"bash", "sh", "zsh", "dash"}
_PS_SHELLS = {"powershell", "pwsh"}
_DEST_OPTIONS = {"-destination", "-destinationpath"}
_VALUE_OPTIONS = {"-value", "-inputobject", "-encoding", "-itemtype", "-type"}
_SCRIPT_OPTIONS = {"-e", "-f", "--expression"}  # sed and perl: the value is the script, not a file
_VAR = re.compile(r"\$env:([A-Za-z_]\w*)|\$\{([A-Za-z_]\w*)\}|\$([A-Za-z_]\w*)", re.IGNORECASE)


def _expand(command: str, project: Path) -> str:
    """Replace $CLAUDE_PROJECT_DIR, $env:NAME, ${NAME} and $NAME with their values; unknown names stay."""
    env = {k.upper(): v for k, v in os.environ.items()}
    env["CLAUDE_PROJECT_DIR"] = str(project)

    def value(m: re.Match) -> str:
        name = next(g for g in m.groups() if g)
        return env.get(name.upper(), m.group(0))

    return _VAR.sub(value, command)


def _tokens(command: str) -> list[tuple[str, str]]:
    """('word', text), ('sep', op), ('out', '>') and ('in', '<') tokens of a command line.

    Quotes group a word, with no escapes inside; backslashes stay literal so
    Windows paths survive. Heredoc bodies and # comments are dropped.
    """
    toks: list[tuple[str, str]] = []
    word: Optional[str] = None
    heredocs: list[str] = []
    want_delim = False
    i, n = 0, len(command)

    def end() -> None:
        nonlocal word, want_delim
        if word is not None:
            if want_delim:
                heredocs.append(word)
                want_delim = False
            else:
                toks.append(("word", word))
            word = None

    while i < n:
        c = command[i]
        if c in "'\"":
            j = command.find(c, i + 1)
            j = n if j < 0 else j
            word = (word or "") + command[i + 1:j]
            i = j + 1
        elif c in "\\`" and command.startswith(("\n", "\r\n"), i + 1):  # a line continued with \ (bash) or ` (PowerShell)
            i += 2 if command[i + 1] == "\n" else 3
        elif c == "#" and word is None:
            while i < n and command[i] != "\n":
                i += 1
        elif c == "\n":
            end()
            toks.append(("sep", "\n"))
            i += 1
            for delim in heredocs:  # skip each body up to its delimiter line
                while i < n:
                    j = command.find("\n", i)
                    j = n if j < 0 else j
                    line = command[i:j]
                    i = j + 1
                    if line.strip() == delim:
                        break
            heredocs.clear()
        elif command.startswith("<<<", i):  # a here-string: the next word is input, not a heredoc delimiter
            end()
            toks.append(("in", "<"))
            i += 3
        elif command.startswith("<<", i):
            end()
            i += 2
            while i < n and command[i] in "-~":
                i += 1
            want_delim = True
        elif c == "<":
            end()
            toks.append(("in", "<"))
            i += 1
        elif c == ">" or command.startswith("&>", i):
            if word is not None and re.fullmatch(r"\d|\*", word):
                word = None  # a stream number: 2>file, *>file (PowerShell)
            end()
            i += 1 if c == ">" else 2
            if i < n and command[i] in ">|":
                i += 1
            k = i
            while k < n and command[k] in " \t":
                k += 1
            if k < n and command[k] == "&":  # 2>&1, >&2: a copy of another stream, not a file
                i = k + 1
                while i < n and (command[i].isdigit() or command[i] == "-"):
                    i += 1
            else:
                toks.append(("out", ">"))
        elif command.startswith(("&&", "||", "|&"), i):
            end()
            toks.append(("sep", command[i:i + 2]))
            i += 2
        elif c in ";|&" or (c in "({" and word is None) or (c == ")" and "(" not in (word or "")) \
                or (c == "}" and "{" not in (word or "")):
            end()
            toks.append(("sep", c))
            i += 1
        elif c.isspace():
            end()
            i += 1
        else:
            word = (word or "") + c
            i += 1
    end()
    return toks


def _simple_commands(toks: list[tuple[str, str]]) -> Iterator[tuple[list[str], list[str]]]:
    """(words, redirect targets) of each simple command; '<' sources are dropped."""
    words: list[str] = []
    outs: list[str] = []
    expect = None
    for kind, val in toks:
        if kind == "sep":
            if words or outs:
                yield words, outs
            words, outs, expect = [], [], None
        elif kind in ("out", "in"):
            expect = kind
        else:
            if expect == "out":
                outs.append(val)
            elif expect is None:
                words.append(val)
            expect = None
    if words or outs:
        yield words, outs


def _name(word: str) -> str:
    base = re.split(r"[\\/]", word)[-1].lower()
    return re.sub(r"\.(exe|cmd|bat)$", "", base)


def _arg_targets(name: str, args: list[str]) -> list[str]:
    """The paths a command writes, from its arguments."""
    positional: list[str] = []
    named: dict[str, str] = {}
    in_place = False
    i = 0
    while i < len(args):
        a = args[i]
        low = a.lower()
        if a.startswith("-") and len(a) > 1:
            # The value may be inline: --expression=SCRIPT, or PowerShell's -Destination:<path>.
            parts = re.split(r"[=:]", a, maxsplit=1)
            raw_key, inline = parts[0], len(parts) > 1
            key = raw_key.lower()
            value = parts[1] if inline else (args[i + 1] if i + 1 < len(args) else None)
            step = 1 if inline else 2
            if key in ("-t", "--target-directory"):
                named["-t"] = value or ""
                i += step
                continue
            # sed and perl options are case-sensitive: sed -E is extended regex, not -e.
            if key in _DEST_OPTIONS or key in _VALUE_OPTIONS or (name in _IN_PLACE and raw_key in _SCRIPT_OPTIONS):
                if value is not None:
                    named[key] = value
                i += step
                continue
            # PowerShell's -Path:<path> carries the path inline; the space form leaves it positional.
            if inline and key in ("-path", "-literalpath"):
                positional.append(parts[1])
            elif re.match(r"^-[^-]*i", a) or low.startswith("--in-place"):
                in_place = True
            i += 1
            continue
        positional.append(a)
        i += 1
    if name in _ALL_ARGS:
        return positional + [named[k] for k in ("-destination", "-destinationpath", "-t") if k in named]
    if name in _DEST:
        for key in ("-destination", "-destinationpath", "-t"):
            if key in named:
                return [named[key]]
        # Expand-Archive <zip> with no destination unpacks into the current folder, not onto the zip.
        if name == "expand-archive" and len(positional) < 2:
            return ["."]
        return positional[-1:] if len(positional) > 1 or name == "compress-archive" else []
    if name in _DEST_SECOND:
        return positional[1:2]
    if name in _IN_PLACE and in_place:
        has_script = any(k in named for k in _SCRIPT_OPTIONS)
        return positional if has_script else positional[1:]
    return []


def shell_targets(command: str, cwd: str, project: Path) -> list[str]:
    """Absolute paths a shell command writes to, as far as its command line shows."""
    targets: list[str] = []
    stack: list[str] = []  # folders saved by pushd and Push-Location
    for words, outs in _simple_commands(_tokens(_expand(command, project))):
        targets += [_absolute(o, cwd) for o in outs if o.lower() not in ("/dev/null", "$null", "nul")]
        while words and (re.match(r"^[A-Za-z_]\w*=", words[0]) or words[0] in _KEYWORDS or _name(words[0]) in _WRAPPERS):
            words = words[1:]
        if not words:
            continue
        name, args = _name(words[0]), words[1:]
        if name in _POPD:
            if stack:
                cwd = stack.pop()
            continue
        if name in _CD:
            # Skip options and cmd switches such as cd /d; a lone /x is still a path (Git Bash /d is D:\).
            rest = [a for a in args if not a.startswith("-")]
            while len(rest) > 1 and re.match(r"^/[A-Za-z]$", rest[0]):
                rest = rest[1:]
            dest = rest[0] if rest else None
            if dest and dest != "-":
                if name in _PUSHD:
                    stack.append(cwd)
                cwd = _absolute(dest, cwd)
            continue
        inner = None
        if name in _POSIX_SHELLS and "-c" in args:
            inner = args[args.index("-c") + 1:args.index("-c") + 2]
        elif name in _PS_SHELLS:
            flag = next((k for k, a in enumerate(args) if a.lower() in ("-c", "-command", "/c", "/command")), None)
            inner = args[flag + 1:] if flag is not None else None
        elif name == "cmd":
            flag = next((k for k, a in enumerate(args) if a.lower() in ("/c", "/k")), None)
            inner = args[flag + 1:] if flag is not None else None
        if inner:
            targets += shell_targets(" ".join(inner), cwd, project)
            continue
        targets += [_absolute(t, cwd) for t in _arg_targets(name, args) if t]
    return targets


# ---- decision ---------------------------------------------------------------

def _reason(active: str, other: str, target: str, what: str, mods: list[str]) -> str:
    reason = (
        f"Blocked by /dayz-scope-mod: the active scope is {active}, and {what} "
        f"the mod {other} ({target}). Edit only files of {active} (workspace/{active}/, "
        f"P:\\{active}\\). If {other} really needs this change, ask the user to run "
        f"/dayz-scope-mod {other} or /dayz-scope-mod --clear first."
    )
    if other.lower() not in {m.lower() for m in mods}:
        reason += (
            f" workspace/{other}/ has no config.cpp or $PBOPREFIX$ yet, but while a scope is active "
            f"every workspace folder other than {active} counts as a mod. A helper folder needs a "
            f"leading underscore, such as workspace/_notes/."
        )
    return reason


def decide(data: dict, project: Path) -> Optional[str]:
    """Return a deny reason, or None to let the tool call through."""
    state_file = project / SCOPE_STATE
    if not state_file.is_file():
        return None
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    active = state.get("active_mod") if isinstance(state, dict) else None
    tool_input = data.get("tool_input")
    if not isinstance(active, str) or not active or not isinstance(tool_input, dict):
        return None
    tool = data.get("tool_name")
    cwd = str(data.get("cwd") or project)
    if tool in SHELL_TOOLS:
        command = tool_input.get("command")
        if not isinstance(command, str):
            return None
        targets, what = shell_targets(command, cwd, project), "this command writes to"
    else:
        file_path = tool_input.get("file_path")
        if not isinstance(file_path, str) or not file_path:
            return None
        targets, what = [_absolute(file_path, cwd)], "this edit targets"
    mods = workspace_mods(project)
    for target in targets:
        other = _other_mod(target, project, active, mods)
        if other is not None:
            return _reason(active, other, target, what, mods)
    return None


def shadowed_by_project() -> bool:
    """True when this is the plugin copy and the project has its own copy of the hook.

    A clone with the agentic-z plugin enabled wires each hook twice: once from
    .claude/settings.json and once from the plugin's hooks.json. The plugin
    copy then steps aside so the project copy runs alone. It steps aside only
    when the project copy both exists and is wired in the project's settings,
    so a clone that keeps hooks/ but drops the wiring still gets the plugin copy.
    """
    project = os.environ.get("CLAUDE_PROJECT_DIR")
    if not project:
        return False
    here = Path(__file__).resolve()
    root = Path(project).resolve()
    if here.is_relative_to(root):
        return False
    if not (root / "hooks" / here.name).is_file():
        return False
    return any(_wires(root / ".claude" / name, here.name) for name in ("settings.json", "settings.local.json"))


def _wires(settings: Path, hook: str) -> bool:
    """True when a settings file has a hook command that runs the project's hooks/<hook>."""
    try:
        config = json.loads(settings.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    events = config.get("hooks") if isinstance(config, dict) else None
    for groups in (events.values() if isinstance(events, dict) else []):
        for group in groups if isinstance(groups, list) else []:
            for entry in (group.get("hooks") or []) if isinstance(group, dict) else []:
                command = str(entry.get("command") or "") if isinstance(entry, dict) else ""
                if f"hooks/{hook}" in command.replace("\\", "/") and "CLAUDE_PLUGIN_ROOT" not in command:
                    return True
    return False


def main() -> int:
    try:
        shadowed = shadowed_by_project()
    except Exception:  # a broken shadow check must not switch this copy off; run it instead
        shadowed = False
    if shadowed:
        return 0
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace") or "{}")  # Claude Code sends UTF-8
        project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd())
        reason = decide(data, project)
    except Exception:  # a guard bug must not block unrelated tool calls
        return 0
    if reason:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
