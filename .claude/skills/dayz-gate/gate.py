"""dayz-gate: script-only build and in-game gates for the mod team.

  gate.py build  <ModName> [--yes] [--json]
  gate.py ingame <ModName> [--deps CF ...] [--server <instance>] [--port N]
                 [--timeout S] [--settle S] [--ready-pattern REGEX] [--yes] [--json]
  gate.py behavior <ModName> [--checks FILE] [--deps CF ...] [--server <instance>]
                 [--port N] [--timeout S] [--done-timeout S] [--ready-pattern REGEX]
                 [--prepare-only | --logs FILE ...] [--yes] [--json]
  gate.py visual <ModName> [--shots FILE] [--deps CF ...] [--server <instance>] [--port N]
                 [--timeout S] [--threshold R] [--ready-pattern REGEX]
                 [--compare [DIR] | --accept [DIR] [--shot ID ...]] [--yes] [--json]

Every mode that packs or launches stops a running DayZDiag session first
(build only once lint passes; a session the gate did not start is stopped only
with --yes or a yes at the terminal prompt, else the gate exits ERROR; behavior --logs and --prepare-only and visual
--compare and --accept launch nothing and leave a session alone), runs the existing skill
scripts (/dayz-build-pbo, /dayz-deploy-pbo, /dayz-launch-test) as subprocesses,
applies the pass/fail rules of the dayz-build-checker and dayz-ingame-tester
agents, triages every failure against known-errors.json, and prints the verdict
on the first line (PASS, FAIL, or ERROR), then a summary or, with --json, JSON.

Exit codes: 0 PASS, 1 FAIL, 2 usage or environment error in the gate itself
(the orchestrator then falls back to the gate agents). behavior runs the
in-game flow on a copy of the instance whose mission spawns and uses each item
in a checks file (behavior.py). visual captures the client window at set
seconds of the in-game flow and compares each capture with its stored
baseline (visual.py). Every PASS or FAIL is stored for /dayz-health
(health.py), which then rebuilds the mod's health page. See SKILL.md.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, NamedTuple, Optional

HERE = Path(__file__).resolve().parent
SKILLS_DIR = HERE.parent
sys.path.insert(0, str(SKILLS_DIR / "_shared"))
import skill_helpers as h  # noqa: E402

triage = h.load_module("dayz_gate_triage", HERE / "triage.py")
behavior = h.load_module("dayz_gate_behavior", HERE / "behavior.py")
visual = h.load_module("dayz_gate_visual", HERE / "visual.py")
lint = h.load_module("dayz_gate_lint", SKILLS_DIR / "dayz-lint" / "lint.py")
health = h.load_module("dayz_gate_health", SKILLS_DIR / "dayz-health" / "health.py")

BUILD_PY = SKILLS_DIR / "dayz-build-pbo" / "build.py"
DEPLOY_PY = SKILLS_DIR / "dayz-deploy-pbo" / "deploy.py"
LAUNCH_PY = SKILLS_DIR / "dayz-launch-test" / "launch.py"
STOP_BAT = SKILLS_DIR / "dayz-stop-test" / "stop_test.bat"
DIAG_EXE = "DayZDiag_x64.exe"

DEFAULT_TIMEOUT_S = 300  # dayz-ingame-tester gives the client five minutes
DEFAULT_SETTLE_S = 30    # keep reading after the ready signal to catch spawn-time errors
BEHAVIOR_DONE_TIMEOUT_S = 600  # behavior: upper bound after the ready signal; the test mission's DONE line ends it sooner
POLL_S = 2
MAX_LISTED = 30          # cap per list in the report; the rest is counted

# The client's script log prints this when it creates the multiplayer mission
# after joining the server: vanilla P:\scripts\5_mission\somemission.c,
# CreateMission() -> Print("Creating Mission: " + path), path mpmissions\__cur_mp.<world>.
DEFAULT_READY_RE = r"Creating Mission: mpmissions[\\/]__cur_mp\."

# dayz-ingame-tester: NULL pointer and Can't find errors fail only when they name
# the mod; these categories fail whatever they name (unless they are vanilla noise).
MOD_QUALIFIED = {"null_pointer", "cant_find"}

# AddonBuilder diagnostics (dayz-build-checker: errors, and warnings about missing
# files, missing textures or unknown classes). Matched by keyword because
# AddonBuilder, CfgConvert and Binarize each word their messages differently.
# [FATAL] and .NET exceptions: AddonBuilder 1.0.240639 crashed on -exclude= with only these lines.
BUILD_ERROR_RE = re.compile(r"(?i)\berror\b|\bfailed\b|\bfatal\b|\w+exception\b|undefined base class|encountered instead of")
BUILD_ERROR_EXCLUDE_RE = re.compile(r"(?i)\b0 errors?\b|\bno errors?\b")
BUILD_WARNING_RE = re.compile(
    r"(?i)(?=.*\bwarn(?:ing)?\b)(?=.*(?:missing|not found|cannot (?:open|find|load)|can't (?:open|find|load)"
    r"|unknown class|undefined|does not exist|no entry))"
)
BUILD_MISSING_RE = re.compile(r"(?i)\b(?:cannot|can't) (?:open|find|load)\b|\bnot found\b")
FILE_REF_RE = re.compile(
    r"(?i)(?:[a-z]:\\)?[\w$@.\\/-]*[\w$@-]\.(?:cpp|hpp|h|c|p3d|paa|rvmat|layout|imageset|xml|json|csv|wrp|ogg|wss)\b"
)
# Lines that continue a multi-line engine error (NULL pointer blocks, stack traces).
CONTINUATION_RE = re.compile(
    r"^\s*(?:Class:|Function:|Stack trace:|SCRIPT\s+\(E\):\s{2,}|[\w$@.\\/-]+\.c(?::\d+|\(\d+\)| : \d+))"
)
MAX_CONTINUATION = 12
LOG_SUFFIXES = (".rpt", ".log")
NAME_STAMP_RE = re.compile(r"_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})\.")


class GateError(Exception):
    """The gate itself cannot run (exit 2); not a verdict on the mod."""


class Runtime(NamedTuple):
    """Everything that touches processes or time, so tests can run without DayZ."""
    run: Callable[[list[str]], tuple[int, str]]
    diag_pids: Callable[[], list[int]]
    pid_alive: Callable[[int], bool]
    sleep: Callable[[float], None] = time.sleep
    clock: Callable[[], float] = time.monotonic
    capture: Callable[[int, Path], None] = visual.capture_window
    confirm: Callable[[list[int]], bool] = lambda pids: confirm_at_terminal(pids)


def run_captured(cmd: list[str]) -> tuple[int, str]:
    """Run cmd, return (exit code, stdout+stderr).

    Output goes to a temp file, not a pipe: /dayz-launch-test leaves DayZ running,
    and a child that inherited a pipe would keep it open, so reading it would hang.
    """
    with tempfile.TemporaryFile() as out:
        rc = subprocess.run(cmd, stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL).returncode
        out.seek(0)
        return rc, out.read().decode("utf-8", errors="replace")


def parse_tasklist(output: str, pid: Optional[int] = None) -> list[int]:
    """PIDs of DayZDiag_x64.exe rows in `tasklist /FO CSV /NH` output."""
    pids = []
    for row in csv.reader(output.splitlines()):
        if len(row) >= 2 and row[0].lower() == DIAG_EXE.lower() and row[1].isdigit():
            if pid is None or int(row[1]) == pid:
                pids.append(int(row[1]))
    return pids


def confirm_at_terminal(pids: list[int]) -> bool:
    """Ask on an interactive terminal whether to end a DayZDiag session the gate did not start.

    No terminal (an agent or a pipe) means no: the caller must pass --yes.
    """
    stdin = sys.stdin
    if stdin is None or not stdin.isatty():
        return False
    prompt = f"{DIAG_EXE} is already running (PIDs {pids}); the gate must stop it. Stop it now? [y/N] "
    try:
        answer = input(prompt)
    except EOFError:
        return False
    return answer.strip().lower() in ("y", "yes")


def real_runtime() -> Runtime:
    def diag_pids() -> list[int]:
        _, out = run_captured(["tasklist", "/FI", f"IMAGENAME eq {DIAG_EXE}", "/FO", "CSV", "/NH"])
        return parse_tasklist(out)

    def pid_alive(pid: int) -> bool:
        _, out = run_captured(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"])
        return bool(parse_tasklist(out, pid))

    return Runtime(run=run_captured, diag_pids=diag_pids, pid_alive=pid_alive)


# --- shared steps -------------------------------------------------------------

def stop_session(rt: Runtime, started_by_gate: bool = False) -> dict:
    """Stop every DayZDiag_x64.exe with /dayz-stop-test; GateError if any survive.

    A session the gate did not start may be the user's own play session, so it
    is stopped only when rt.confirm agrees (--yes, or a yes at the terminal).
    """
    pids = rt.diag_pids()
    if not pids:
        return {"step": "stop-session", "result": "no DayZDiag session running"}
    if not started_by_gate and not rt.confirm(pids):
        raise GateError(
            f"{DIAG_EXE} is already running (PIDs {pids}) and the gate did not start it. "
            "Close it yourself, or rerun with --yes to let the gate stop it."
        )
    rc, out = rt.run(["cmd", "/c", str(STOP_BAT)])
    if rc != 0:
        raise GateError(f"/dayz-stop-test exited {rc}: {out.strip()}")
    rt.sleep(POLL_S)
    left = rt.diag_pids()
    if left:
        raise GateError(f"{DIAG_EXE} still running after /dayz-stop-test (PIDs {left})")
    return {"step": "stop-session", "result": f"stopped PIDs {pids}"}


def file_refs(text: str) -> list[str]:
    return sorted(set(FILE_REF_RE.findall(text)))


def script_fail_findings(output: str, step: str) -> list[dict]:
    """[FAIL] lines of a skill script's output, each with its indented hint lines."""
    lines = output.splitlines()
    findings = []
    for i, line in enumerate(lines):
        if line.startswith("[FAIL]"):
            hint = []
            for nxt in lines[i + 1:i + 6]:
                if not nxt.startswith(" ") or not nxt.strip():
                    break
                hint.append(nxt.strip())
            findings.append(_finding("script_fail", line.strip(), step, i + 1, hint))
    return findings


def _finding(category: str, text: str, where: str, line: Optional[int], context: Optional[list[str]] = None) -> dict:
    block = "\n".join([text, *(context or [])])
    return {
        "category": category,
        "file": where,
        "line": line,
        "text": text,
        "context": context or [],
        "points_to": file_refs(block),
    }


def tail(output: str, n: int = 25) -> list[str]:
    return output.splitlines()[-n:]


# --- build gate ---------------------------------------------------------------

def parse_build_output(output: str) -> list[dict]:
    """dayz-build-checker rules over build.py output.

    AddonBuilder lines (after build.py's `[AddonBuilder] ` command echo) that
    report an error, or a warning about missing files, textures or unknown
    classes; plus every [FAIL] line build.py printed.
    """
    findings = script_fail_findings(output, "dayz-build-pbo")
    in_builder = False
    for number, line in enumerate(output.splitlines(), 1):
        if line.startswith("[AddonBuilder] "):
            in_builder = True
            continue
        if not in_builder or line.startswith(("[OK]", "[FAIL]", "[WARN]")) or not line.strip():
            continue
        if BUILD_ERROR_RE.search(line) and not BUILD_ERROR_EXCLUDE_RE.search(line):
            findings.append(_finding("build_error", line.strip(), "dayz-build-pbo", number))
        elif BUILD_WARNING_RE.search(line) or BUILD_MISSING_RE.search(line):
            findings.append(_finding("build_warning", line.strip(), "dayz-build-pbo", number))
    return sorted(findings, key=lambda f: f["line"])


def parse_deploy_output(output: str) -> list[dict]:
    """dayz-build-checker bundle rule: every [FAIL], and every [WARN] about a missing .bisign."""
    findings = script_fail_findings(output, "dayz-deploy-pbo")
    for number, line in enumerate(output.splitlines(), 1):
        if line.startswith("[WARN]") and ".bisign" in line:
            findings.append(_finding("unsigned", line.strip(), "dayz-deploy-pbo", number))
    return sorted(findings, key=lambda f: f["line"])


def bundle_layout(mod_dir: Path) -> tuple[bool, bool]:
    """(has config.cpp, has a prebuilt Addons/*.pbo payload) for workspace/<ModName>/."""
    addons = mod_dir / "Addons"
    has_payload = addons.is_dir() and any(addons.glob("*.pbo"))
    return (mod_dir / "config.cpp").is_file(), has_payload


def run_lint(report: dict, mod: str, mod_dir: Path, project_dir: Path) -> bool:
    """/dayz-lint first: its errors become failures, its warnings warnings. True when it passed."""
    try:
        result = lint.lint_mod(mod, mod_dir, project_dir, project_dir=project_dir)
    except lint.LintError as e:
        raise GateError(str(e)) from e
    report["lint"] = {key: result[key] for key in ("verdict", "errors", "warnings")}
    for f in result["findings"]:
        finding = {**_finding("lint", f["text"], f["file"], f["line"]), "rule": f["rule"]}
        report["failures" if f["severity"] == lint.ERROR else "warnings"].append(finding)
    return result["verdict"] == "PASS"


def gate_build(mod: str, project_dir: Path, rt: Runtime) -> dict:
    report = new_report("build", mod)
    mod_dir = project_dir / "workspace" / mod
    # /dayz-lint first: a mod that would not load is not packed (and a running session is left alone).
    if not run_lint(report, mod, mod_dir, project_dir):
        return finish(report, project_dir)
    report["steps"].append(stop_session(rt))
    has_cfg, has_payload = bundle_layout(mod_dir)
    # Tier 2 conventions/config.md, "Bundle / umbrella mods": a payload-only bundle has nothing to build;
    # a bundle with a linker config.cpp is built, then its payload deployed.
    if has_cfg or not has_payload:
        rc, out = rt.run([sys.executable, str(BUILD_PY), mod])
        findings = parse_build_output(out)
        step = {"step": "dayz-build-pbo", "rc": rc}
        if rc != 0:
            step["tail"] = tail(out)  # the build output, kept so a failure can be diagnosed
        report["steps"].append(step)
        if rc != 0 and not findings:
            findings.append(_finding("script_fail", f"dayz-build-pbo exited {rc}", "dayz-build-pbo", None, tail(out)))
        report["failures"] += findings
    else:
        report["steps"].append({"step": "dayz-build-pbo", "result": "skipped: payload-only bundle (no config.cpp)"})
    if has_payload:
        rc, out = rt.run([sys.executable, str(DEPLOY_PY), mod])
        findings = parse_deploy_output(out)
        report["steps"].append({"step": "dayz-deploy-pbo", "rc": rc})
        if rc != 0 and not any(f["category"] == "script_fail" for f in findings):
            findings.append(_finding("script_fail", f"dayz-deploy-pbo exited {rc}", "dayz-deploy-pbo", None, tail(out)))
        report["failures"] += findings
    return finish(report, project_dir)


# --- in-game gate -------------------------------------------------------------

class ModIdentity(NamedTuple):
    """What makes a log line "name the mod": its folder, $PBOPREFIX$ and classes."""
    name: str
    path_re: re.Pattern
    class_re: Optional[re.Pattern]
    required_addons: list[str]

    def names(self, text: str) -> bool:
        return bool(self.path_re.search(text) or (self.class_re and self.class_re.search(text)))


def mod_identity(mod: str, mod_dir: Path) -> ModIdentity:
    roots = {mod}
    prefix_file = mod_dir / "$PBOPREFIX$"
    if prefix_file.is_file():
        prefix = prefix_file.read_text(encoding="utf-8-sig").strip()
        if prefix:
            roots.add(prefix.split("\\")[0].split("/")[0])
    path_re = re.compile(
        "|".join(rf"(?:@|\b){re.escape(r)}(?:[\\/]|\b)" for r in sorted(roots)), re.IGNORECASE
    )
    classes: set[str] = set()
    required: list[str] = []
    cfg = mod_dir / "config.cpp"
    if cfg.is_file():
        text = h.strip_cpp_comments(cfg.read_text(encoding="utf-8", errors="replace"))
        classes |= config_classes(text)
        for block in re.findall(r"requiredAddons\s*\[\]\s*=\s*\{([^}]*)\}", text):
            required += re.findall(r'"([^"]+)"', block)
    for script in (mod_dir / "scripts").rglob("*.c") if (mod_dir / "scripts").is_dir() else []:
        text = script.read_text(encoding="utf-8", errors="replace")
        # A modded class reuses a vanilla name; only classes the mod declares count.
        classes |= set(re.findall(r"^\s*class\s+(\w+)", text, re.MULTILINE))
    class_re = re.compile(r"\b(?:" + "|".join(map(re.escape, sorted(classes))) + r")\b") if classes else None
    return ModIdentity(mod, path_re, class_re, required)


def config_classes(text: str) -> set[str]:
    """Classes config.cpp defines directly inside a Cfg* block (CfgVehicles, CfgPatches, ...).

    Nested helper classes (DamageSystem, Cargo) and forward declarations of
    vanilla parents (`class Vest_Base;`) are left out: they are not the mod's.
    """
    text = h.strip_cpp_comments(text)
    classes, depth = set(), 0
    for m in re.finditer(r"\bclass\s+(\w+)[^;{}]*[;{]|[{}]", text):
        token = m.group(0)
        if token == "{":
            depth += 1
        elif token == "}":
            depth -= 1
        elif token.endswith("{"):
            if depth == 1:
                classes.add(m.group(1))
            depth += 1
    return classes


def non_vanilla_addons(identity: ModIdentity) -> list[str]:
    return [a for a in identity.required_addons if not a.upper().startswith("DZ_")]


def is_log(path: Path) -> bool:
    return path.suffix.lower() in LOG_SUFFIXES


def snapshot(dirs: list[Path]) -> dict[Path, int]:
    """Size of every log file now, so only lines written after this are read."""
    return {p: p.stat().st_size for d in dirs if d.is_dir() for p in d.iterdir() if p.is_file() and is_log(p)}


class LogTail:
    """Reads the lines appended to log files after a snapshot, file by file."""

    def __init__(self, dirs: list[Path], start: dict[Path, int]):
        self.dirs = dirs
        self.start = start
        self.offsets = dict(start)
        self.line_numbers: dict[Path, int] = {}

    def poll(self, final: bool = False) -> list[tuple[Path, int, str]]:
        new = []
        for d in self.dirs:
            if not d.is_dir():
                continue
            for path in sorted(p for p in d.iterdir() if p.is_file() and is_log(p)):
                offset = self.offsets.get(path, 0)
                with path.open("rb") as f:
                    if path not in self.line_numbers:
                        self.line_numbers[path] = f.read(offset).count(b"\n")
                    f.seek(offset)
                    chunk = f.read()
                if not final:  # hold back a partly written last line
                    chunk = chunk[: chunk.rfind(b"\n") + 1]
                if not chunk:
                    continue
                self.offsets[path] = offset + len(chunk)
                for text in chunk.decode("utf-8", errors="replace").splitlines():
                    self.line_numbers[path] += 1
                    new.append((path, self.line_numbers[path], text))
        return new

    def new_files(self) -> list[Path]:
        return [p for p in self.offsets if p not in self.start]


def group_entries(lines: list[tuple[Path, int, str]]) -> list[dict]:
    """Error lines with their continuation lines (stack traces) as context."""
    entries = []
    current = None
    for path, number, text in lines:
        if current is not None and path == current["path"] and CONTINUATION_RE.match(text) \
                and len(current["context"]) < MAX_CONTINUATION and triage.classify(text) is None:
            current["context"].append(text.strip())
            continue
        current = None
        category = triage.classify(text)
        if category is not None and category != "script_fail":
            current = {"path": path, "line": number, "text": text.strip(), "category": category, "context": []}
            entries.append(current)
    return entries


def name_stamp(path: Path) -> Optional[datetime]:
    match = NAME_STAMP_RE.search(path.name)
    return datetime.strptime(match.group(1), "%Y-%m-%d_%H-%M-%S") if match else None


def find_baseline(dirs: list[Path], existing: dict[Path, int], mod: str, sessions: int = 2) -> tuple[set[str], list[str]]:
    """Fingerprints from older sessions run without the mod (dayz-ingame-tester's vanilla-only run).

    A session is an RPT whose `CLI params:` line has no @<ModName>, plus the
    script logs created within 30 s after it in the same folder. Up to
    `sessions` newest such sessions per folder.
    """
    mod_re = re.compile(rf"@{re.escape(mod)}\b", re.IGNORECASE)
    prints: set[str] = set()
    used: list[str] = []
    for d in dirs:
        old = [p for p in existing if p.parent == d]
        rpts = sorted((p for p in old if p.suffix.lower() == ".rpt"), key=lambda p: p.stat().st_mtime, reverse=True)
        taken = 0
        for rpt in rpts:
            if taken >= sessions:
                break
            text = rpt.read_text(encoding="utf-8", errors="replace")
            cli = next((line for line in text.splitlines() if "CLI params:" in line), None)
            if cli is None or mod_re.search(cli):
                continue
            files = [rpt]
            stamp = name_stamp(rpt)
            if stamp is not None:
                for log in old:
                    other = name_stamp(log)
                    if log.suffix.lower() == ".log" and other is not None and 0 <= (other - stamp).total_seconds() <= 30:
                        files.append(log)
            for f in files:
                prints |= {triage.fingerprint(line) for line in f.read_text(encoding="utf-8", errors="replace").splitlines()}
                used.append(str(f))
            taken += 1
    return prints, used


def judge_entries(entries: list[dict], identity: ModIdentity, baseline: set[str], have_baseline: bool) -> tuple[list[dict], list[dict], list[dict]]:
    """dayz-ingame-tester rules: (failures, warnings, noise).

    A line that names the mod (folder, $PBOPREFIX$ or a class it declares)
    fails. A line that names nothing of the mod is vanilla noise only if the
    same line is in a vanilla-only run; with no such run it is a warning. NULL
    pointer and Can't find lines that don't name the mod never fail.
    """
    failures, warnings, noise = [], [], []
    for e in entries:
        block = "\n".join([e["text"], *e["context"]])
        if identity.names(block):
            failures.append(e)
        elif triage.fingerprint(e["text"]) in baseline:
            noise.append(e)
        elif e["category"] in MOD_QUALIFIED or not have_baseline:
            warnings.append(e)
        else:
            failures.append(e)
    return failures, warnings, noise


def entry_finding(e: dict, project_dir: Path) -> dict:
    return _finding(e["category"], e["text"], _rel(e["path"], project_dir), e["line"], e["context"])


def _rel(path: Path, project_dir: Path) -> str:
    try:
        return str(path.relative_to(project_dir))
    except ValueError:
        return str(path)


def gate_ingame(
    mod: str,
    project_dir: Path,
    rt: Runtime,
    deps: list[str],
    instance: str = "chernarus",
    port: int = 2302,
    timeout: float = DEFAULT_TIMEOUT_S,
    settle: float = DEFAULT_SETTLE_S,
    ready_pattern: str = DEFAULT_READY_RE,
) -> dict:
    report, _ = ingame_session(mod, project_dir, rt, deps, instance, port, timeout, settle, ready_pattern)
    return finish(report, project_dir, {"instance": instance})


def ingame_session(
    mod: str,
    project_dir: Path,
    rt: Runtime,
    deps: list[str],
    instance: str,
    port: int,
    timeout: float,
    settle: float,
    ready_pattern: str,
    mode: str = "ingame",
    done_re: Optional[re.Pattern] = None,
    on_poll: Optional[Callable[[Optional[float], Optional[int]], None]] = None,
) -> tuple[dict, list[tuple[Path, int, str]]]:
    """The in-game flow up to the verdict: (unfinished report, every new log line).

    `on_poll(seconds since the client joined or None, client PID)` runs on every poll.
    """
    report = new_report(mode, mod)
    mod_dir = project_dir / "workspace" / mod
    identity = mod_identity(mod, mod_dir)
    deps = [d.lstrip("@") for d in deps]
    missing_deps = non_vanilla_addons(identity)
    if missing_deps and not deps and not bundle_layout(mod_dir)[1]:
        raise GateError(
            f"config.cpp requires non-vanilla addons {missing_deps} but no --deps were given. "
            "Map each to the @mod under P:\\Mods\\ that ships it and pass them in load order, "
            "for example --deps CF."
        )
    ready_re = re.compile(ready_pattern)
    server_dir = project_dir / ".server" / instance / "Profiles"
    client_dir = project_dir / ".server" / "!ClientDiagLogs"
    dirs = [server_dir, client_dir]

    report["steps"].append(stop_session(rt))
    start = snapshot(dirs)
    logs = LogTail(dirs, start)
    lines: list[tuple[Path, int, str]] = []
    extra: list[dict] = []
    try:
        cmd = [sys.executable, str(LAUNCH_PY), *deps, mod, "--server", instance, "--port", str(port)]
        rc, out = rt.run(cmd)
        report["steps"].append({"step": "dayz-launch-test", "rc": rc})
        if rc != 0:
            extra += script_fail_findings(out, "dayz-launch-test") or [
                _finding("script_fail", f"dayz-launch-test exited {rc}", "dayz-launch-test", None, tail(out))
            ]
        else:
            pids = sorted({int(p) for p in re.findall(r"(?:Server|Client) PID: (\d+)", out)})
            client = re.search(r"Client PID: (\d+)", out)
            client_pid = int(client.group(1)) if client else None
            hook = (lambda elapsed: on_poll(elapsed, client_pid)) if on_poll else None
            lines, ready, problem = watch_session(rt, logs, client_dir, pids, ready_re, timeout, settle, done_re, hook)
            report["ready"] = ready
            if problem is not None:
                extra.append(problem)
    finally:
        report["steps"].append(stop_session(rt, started_by_gate=True))  # always, even after a failure
    lines += logs.poll(final=True)

    for path in logs.new_files():
        if path.name.lower().startswith("crash"):
            head = [t.strip() for p, _, t in lines if p == path and t.strip()][:8]
            extra.append(_finding("crash", f"crash log written: {path.name}", _rel(path, project_dir), None, head))

    baseline, used = find_baseline(dirs, start, mod)
    report["baseline"] = used
    failures, warnings, noise = judge_entries(group_entries(lines), identity, baseline, bool(used))
    report["failures"] = extra + [entry_finding(e, project_dir) for e in failures]
    report["warnings"] = [entry_finding(e, project_dir) for e in warnings]
    report["noise"] = [entry_finding(e, project_dir) for e in noise]
    return report, lines


def watch_session(
    rt: Runtime, logs: LogTail, client_dir: Path, pids: list[int], ready_re: re.Pattern, timeout: float, settle: float,
    done_re: Optional[re.Pattern] = None,
    on_poll: Optional[Callable[[Optional[float]], None]] = None,
) -> tuple[list[tuple[Path, int, str]], Optional[dict], Optional[dict]]:
    """Poll the logs until the client is in the mission plus `settle` seconds.

    Returns (lines read, ready signal or None, failure or None). Stops early
    when a script module fails to compile, a crash log appears, the server
    or client process exits, or a line matches `done_re` after the ready signal.
    `on_poll` gets the seconds since the ready signal (None before it) on every poll.
    """
    lines: list[tuple[Path, int, str]] = []
    ready: Optional[dict] = None
    ready_at = None
    deadline = rt.clock() + timeout
    while True:
        new = logs.poll()
        lines += new
        for path, number, text in new:
            if ready is None and path.parent == client_dir and path.name.lower().startswith("script") and ready_re.search(text):
                ready = {"file": str(path.name), "line": number, "text": text.strip()}
                ready_at = rt.clock()
        if ready is not None and done_re is not None and any(done_re.search(t) for _, _, t in new):
            return lines, ready, None
        if any(triage.classify(t) == "compile" and "script module" in t for _, _, t in new):
            return lines, ready, None
        if any(p.name.lower().startswith("crash") for p in logs.new_files()):
            return lines, ready, None
        dead = [pid for pid in pids if not rt.pid_alive(pid)]
        if dead:
            return lines, ready, _finding("crash", f"DayZDiag process exited before the gate stopped it (PID {', '.join(map(str, dead))})", "process", None)
        now = rt.clock()
        if on_poll is not None:
            on_poll(None if ready_at is None else now - ready_at)
        if ready_at is not None and now - ready_at >= settle:
            return lines, ready, None
        if now >= deadline:
            return lines, ready, _finding(
                "no_ready",
                f"client never reached the mission within {int(timeout)} s (no line matching {ready_re.pattern!r} in the client script log)",
                "client", None,
            )
        rt.sleep(POLL_S)


# --- behavior gate --------------------------------------------------------------

def gate_behavior(
    mod: str,
    project_dir: Path,
    rt: Runtime,
    checks_path: Optional[Path],
    deps: list[str],
    instance: str = "chernarus",
    port: int = 2302,
    timeout: float = DEFAULT_TIMEOUT_S,
    done_timeout: float = BEHAVIOR_DONE_TIMEOUT_S,
    ready_pattern: str = DEFAULT_READY_RE,
) -> dict:
    """Copy the instance with the test mission injected, run the in-game flow on it, judge the checks."""
    checks = behavior.load_checks(checks_path or behavior.default_checks_path(project_dir, mod))
    stop_session(rt)  # a running session can hold the old copy's files open
    prepared = behavior.prepare_instance(project_dir, instance, checks)
    report, lines = ingame_session(
        mod, project_dir, rt, deps, prepared["instance"], port, timeout, done_timeout, ready_pattern,
        mode="behavior", done_re=behavior.DONE_RE,
    )
    add_behavior_results(report, behavior.parse_lines(lines, checks), project_dir)
    refuse_unstarted_mission(report, prepared["instance"])
    return finish(report, project_dir, {"instance": prepared["instance"]})


def gate_behavior_logs(mod: str, project_dir: Path, checks_path: Optional[Path], instance: str, files: list[Path]) -> dict:
    """Judge the checks from logs of a session already run (default: the behavior copy's server script logs)."""
    behavior.check_instance(instance)
    checks = behavior.load_checks(checks_path or behavior.default_checks_path(project_dir, mod))
    copy = instance + behavior.INSTANCE_SUFFIX
    files = files or behavior.server_script_logs(project_dir, copy)
    if not files:
        raise GateError(f"no script logs in .server/{copy}/Profiles/; run the behavior gate or pass --logs")
    report = new_report("behavior", mod)
    report["steps"].append({"step": "read-logs", "result": f"{len(files)} file(s)"})
    add_behavior_results(report, behavior.parse_lines(behavior.read_logs(files), checks), project_dir)
    refuse_unstarted_mission(report, copy)
    return finish(report, project_dir, {"instance": copy})


def add_behavior_results(report: dict, parsed: dict, project_dir: Path) -> None:
    """Per-check results into the report; every failed check is a failure."""
    report["checks"] = []
    for r in parsed["results"]:
        where = _rel(r["file"], project_dir) if r["file"] else "server script log"
        report["checks"].append({**r, "file": where})
        if r["status"] == "FAIL":
            text = r["text"] or f"{behavior.TAG} FAIL {r['id']} {r['reason']}"
            finding = _finding("behavior", text, where, r["line"])
            finding["check"] = r["id"]
            report["failures"].append(finding)
    report["behavior"] = {"started": parsed["started"], "done": parsed["done"], "unexpected": parsed["unexpected"]}


def refuse_unstarted_mission(report: dict, copy: str) -> None:
    """ERROR, not FAIL, when the test mission never ran and nothing else went wrong.

    Without a START line every check fails, but when the session shows no other
    problem (the client joined, no crash, no script error) the cause is the
    gate's own injected mission, so judging the mod on it would mislead.
    """
    if report["behavior"]["started"] or any(f["category"] != "behavior" for f in report["failures"]):
        return
    raise GateError(
        f"the behavior test mission never printed {behavior.TAG} START, yet the session shows no mod error, "
        f"so this is not a verdict on the mod. Look for an init.c error in the server script log under "
        f".server/{copy}/Profiles/ and report it against /dayz-gate."
    )


# --- visual gate ----------------------------------------------------------------

def gate_visual(
    mod: str,
    project_dir: Path,
    rt: Runtime,
    shots_path: Optional[Path],
    deps: list[str],
    instance: str = "chernarus",
    port: int = 2302,
    timeout: float = DEFAULT_TIMEOUT_S,
    threshold: Optional[float] = None,
    ready_pattern: str = DEFAULT_READY_RE,
) -> dict:
    """Run the in-game flow, capture each shot at its second, compare the captures with the baselines."""
    spec = visual.load_shots(shots_path or visual.default_shots_path(project_dir, mod))
    run_dir = visual.new_run_dir(project_dir, mod)
    capturer = visual.Capturer(spec["shots"], run_dir, rt.capture)
    report, _ = ingame_session(
        mod, project_dir, rt, deps, instance, port, timeout, visual.last_shot_at(spec) + POLL_S, ready_pattern,
        mode="visual", on_poll=capturer,
    )
    capturer.finish()
    results = visual.compare_run(spec, run_dir, visual.baseline_dir(project_dir, mod), threshold, capturer.errors)
    add_visual_results(report, results, run_dir, project_dir)
    return finish(report, project_dir, {"instance": instance})


def gate_visual_compare(mod: str, project_dir: Path, shots_path: Optional[Path], run_dir: Optional[Path],
                        threshold: Optional[float] = None) -> dict:
    """Compare captures already taken (default: the newest run) with the baselines."""
    spec = visual.load_shots(shots_path or visual.default_shots_path(project_dir, mod))
    run_dir = run_dir or visual.latest_run_dir(project_dir, mod)
    if not run_dir.is_dir():
        raise GateError(f"no folder {run_dir}")
    report = new_report("visual", mod)
    report["steps"].append({"step": "compare", "result": f"captures in {_rel(run_dir, project_dir)}"})
    results = visual.compare_run(spec, run_dir, visual.baseline_dir(project_dir, mod), threshold)
    add_visual_results(report, results, run_dir, project_dir)
    return finish(report, project_dir)


VISUAL_TEXT = {
    visual.FAIL: "[visual:diff] {id}: {reason}",
    visual.NEW: "[visual:no-baseline] {id}: {reason}",
    visual.MISSING: "[visual:no-capture] {id}: {reason}",
}


def add_visual_results(report: dict, results: list[dict], run_dir: Path, project_dir: Path) -> None:
    """Per-shot results into the report; every shot that did not pass is a failure."""
    report["shots"] = []
    for r in results:
        entry = {**r, **{k: _rel(r[k], project_dir) if r[k] else None for k in ("capture", "baseline", "diff")}}
        report["shots"].append(entry)
        if r["status"] != visual.PASS:
            where = entry["capture"] or _rel(run_dir, project_dir)
            context = [f"{k}: {entry[k]}" for k in ("capture", "baseline", "diff") if entry[k]]
            finding = _finding("visual", VISUAL_TEXT[r["status"]].format(**r), where, None, context)
            finding["shot"] = r["id"]
            report["failures"].append(finding)
    report["visual"] = {
        "run": _rel(run_dir, project_dir),
        "baseline": _rel(visual.baseline_dir(project_dir, report["mod"]), project_dir),
    }


# --- report -------------------------------------------------------------------

def new_report(mode: str, mod: str) -> dict:
    return {"verdict": None, "mode": mode, "mod": mod, "steps": [], "failures": [], "warnings": [], "noise": []}


def dedupe(findings: list[dict]) -> list[dict]:
    """One finding per fingerprint (head line plus stack), first occurrence kept, with a count."""
    seen: dict[str, dict] = {}
    for f in findings:
        # Behavior failures are per check: two checks failing alike stay two findings.
        key = f.get("check", f.get("shot", "")) + "|" + triage.fingerprint(" | ".join([f["text"], *f["context"][:3]]))
        if key in seen:
            seen[key]["count"] += 1
        else:
            seen[key] = {**f, "count": 1}
    return list(seen.values())


def capped(findings: list[dict]) -> tuple[list[dict], int]:
    return findings[:MAX_LISTED], max(0, len(findings) - MAX_LISTED)


def finish(report: dict, project_dir: Path, extra_context: Optional[dict] = None) -> dict:
    """Dedupe, triage every failure, set the verdict."""
    context = {"ModName": report["mod"], **(extra_context or {})}
    known = triage.load_known(triage.KNOWN_ERRORS, triage.learned_path(project_dir))
    mod_dir = project_dir / "workspace" / report["mod"]
    report["failures"] = dedupe(report["failures"])
    for f in report["failures"]:
        f["triage"] = triage.match_line(f["text"], known, context)
    for key in ("warnings", "noise"):
        report[key], report[f"{key}_not_listed"] = capped(dedupe(report[key]))
    report["verdict"] = "FAIL" if report["failures"] else "PASS"
    if report["failures"] and mod_dir.is_dir():
        report["source_findings"] = triage.check_sources(mod_dir, known, context)
    return report


def render_text(report: dict) -> str:
    """The human summary printed under the verdict line without --json."""
    out = []
    if report.get("lint"):
        out.append(f"  dayz-lint: {report['lint']['verdict']}, {report['lint']['errors']} error(s), {report['lint']['warnings']} warning(s)")
    for step in report["steps"]:
        out.append(f"  {step['step']}: " + (f"exit {step['rc']}" if "rc" in step else step["result"]))
    if report.get("ready"):
        out.append(f"  ready: {report['ready']['file']}:{report['ready']['line']}  {report['ready']['text']}")
    for c in report.get("checks", []):
        out.append(f"  {c['status']} {c['id']}" + (f"  {c['reason']}" if c["reason"] else ""))
    for s in report.get("shots", []):
        detail = s["reason"] or (f"{s['ratio']:.2%} of pixels differ" if s["ratio"] is not None else "")
        out.append(f"  {s['status']} {s['id']}" + (f"  {detail}" if detail else ""))
    for f in report["failures"]:
        where = f"{f['file']}:{f['line']}" if f["line"] else f["file"]
        times = f" (x{f['count']})" if f["count"] > 1 else ""
        out.append(f"- [{f['category']}] {where}{times}  {f['text']}")
        for c in f["context"][:6]:
            out.append(f"      {c}")
        t = f["triage"]
        if t["status"] == "known":
            out.append(f"    known {t['id']} -> {t['owner_agent']}: {t['fix']}")
        else:
            out.append("    new -> dayz-mod-debugger")
    for s in report.get("source_findings", []):
        out.append(f"- [source] {s['file']}:{s['line'] or ''}  known {s['id']} -> {s['owner_agent']}: {s['fix']}")
    if report["warnings"] or report["noise"]:
        out.append(
            f"  warnings: {len(report['warnings']) + report.get('warnings_not_listed', 0)}, "
            f"vanilla noise skipped: {len(report['noise']) + report.get('noise_not_listed', 0)} (see --json)"
        )
    if report.get("health"):
        out.append(f"  health page: {report['health']}")
    if report.get("health_error"):
        out.append(f"  health page not updated: {report['health_error']}")
    return "\n".join(out)


def save_health(report: dict, project_dir: Path) -> None:
    """Store the result for /dayz-health. A store that fails is noted in the report; the verdict stands."""
    try:
        health.record_gate(project_dir, report)
        report["health"] = _rel(health.mod_dir(project_dir, report["mod"]) / "health.md", project_dir)
    except (health.HealthError, OSError) as e:
        report["health_error"] = str(e)


def emit(report: dict, as_json: bool) -> None:
    print(report["verdict"])
    print(json.dumps(report, indent=2) if as_json else render_text(report))


YES_HELP = "Stop a DayZDiag session the gate did not start without asking (it may be your own play session)."


def main(argv: Optional[list[str]] = None, rt: Optional[Runtime] = None) -> int:
    parser = argparse.ArgumentParser(description="Script-only build and in-game gates.")
    sub = parser.add_subparsers(dest="mode", required=True)
    b = sub.add_parser("build", help="Build (or deploy a bundle) and check the output.")
    b.add_argument("mod")
    b.add_argument("--json", action="store_true")
    b.add_argument("--yes", action="store_true", help=YES_HELP)
    g = sub.add_parser("ingame", help="Launch server and client, read the logs, stop the session.")
    g.add_argument("mod")
    g.add_argument("--deps", nargs="+", default=[], metavar="MOD", help="Dependency mods in load order (CF or @CF).")
    g.add_argument("--server", default="chernarus", help="Server instance (default chernarus).")
    g.add_argument("--port", type=int, default=2302)
    g.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S, help="Seconds to wait for the client to reach the mission.")
    g.add_argument("--settle", type=float, default=DEFAULT_SETTLE_S, help="Seconds to keep reading after the ready signal.")
    g.add_argument("--ready-pattern", default=DEFAULT_READY_RE, help="Regex in the client script log that means the mission is running.")
    g.add_argument("--json", action="store_true")
    g.add_argument("--yes", action="store_true", help=YES_HELP)
    v = sub.add_parser("behavior", help="Run a test mission that spawns and uses each item in a checks file.")
    v.add_argument("mod")
    v.add_argument("--checks", type=Path, help="Checks JSON (default output/<ModName>-plan/behavior-checks.json).")
    v.add_argument("--deps", nargs="+", default=[], metavar="MOD", help="Dependency mods in load order (CF or @CF).")
    v.add_argument("--server", default="chernarus", help="Server instance to copy (default chernarus).")
    v.add_argument("--port", type=int, default=2302)
    v.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S, help="Seconds to wait for the client to reach the mission.")
    v.add_argument("--done-timeout", type=float, default=BEHAVIOR_DONE_TIMEOUT_S,
                   help="Most seconds to wait after the client joins for the test mission's DONE line.")
    v.add_argument("--ready-pattern", default=DEFAULT_READY_RE, help="Regex in the client script log that means the mission is running.")
    only = v.add_mutually_exclusive_group()
    only.add_argument("--prepare-only", action="store_true", help="Write the behavior instance copy and stop.")
    only.add_argument("--logs", nargs="*", type=Path, metavar="FILE",
                      help="Judge logs of a session already run (no files: the copy's server script logs).")
    v.add_argument("--json", action="store_true")
    v.add_argument("--yes", action="store_true", help=YES_HELP)
    s = sub.add_parser("visual", help="Capture the client window during the in-game test and compare with baselines.")
    s.add_argument("mod")
    s.add_argument("--shots", type=Path, help="Shots JSON (default output/<ModName>-plan/visual-shots.json).")
    s.add_argument("--deps", nargs="+", default=[], metavar="MOD", help="Dependency mods in load order (CF or @CF).")
    s.add_argument("--server", default="chernarus", help="Server instance (default chernarus).")
    s.add_argument("--port", type=int, default=2302)
    s.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S, help="Seconds to wait for the client to reach the mission.")
    s.add_argument("--threshold", type=float, help="Share of pixels allowed to differ, 0 to 1, for shots without their own.")
    s.add_argument("--ready-pattern", default=DEFAULT_READY_RE, help="Regex in the client script log that means the mission is running.")
    offline = s.add_mutually_exclusive_group()
    offline.add_argument("--compare", nargs="?", const=True, type=Path, metavar="DIR",
                         help="Compare captures already taken (no folder: the newest run).")
    offline.add_argument("--accept", nargs="?", const=True, type=Path, metavar="DIR",
                         help="Make captures the new baselines (no folder: the newest run).")
    s.add_argument("--shot", nargs="+", metavar="ID", help="--accept: only these shots.")
    s.add_argument("--json", action="store_true")
    s.add_argument("--yes", action="store_true", help=YES_HELP)
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        if e.code == 0:
            return 0
        # argparse printed usage on stderr; keep the ERROR first-line contract on stdout.
        raw = sys.argv[1:] if argv is None else argv
        return _error("bad arguments (usage on stderr)", "--json" in raw)

    try:
        if args.mode in ("ingame", "behavior", "visual"):
            re.compile(args.ready_pattern)
        if args.mode == "visual" and args.shot and args.accept is None:
            raise GateError("--shot works with --accept only")
        if args.mode == "visual" and args.threshold is not None and not 0 <= args.threshold <= 1:
            raise GateError("--threshold must be from 0 to 1")
        project_dir = h.resolve_project_dir()
        rt = rt or real_runtime()
        if args.yes:
            rt = rt._replace(confirm=lambda pids: True)
        if args.mode == "build":
            report = gate_build(args.mod, project_dir, rt)
        elif args.mode == "behavior" and args.prepare_only:
            return _prepared(args.mod, project_dir, args.checks, args.server, args.json)
        elif args.mode == "behavior" and args.logs is not None:
            report = gate_behavior_logs(args.mod, project_dir, args.checks, args.server, args.logs)
        elif args.mode == "visual" and args.accept is not None:
            return _accepted(args.mod, project_dir, args.shots, args.accept, args.shot, args.json)
        elif args.mode == "visual" and args.compare is not None:
            report = gate_visual_compare(args.mod, project_dir, args.shots, _dir_arg(args.compare), args.threshold)
        elif args.mode == "visual":
            report = gate_visual(
                args.mod, project_dir, rt, args.shots, args.deps, args.server, args.port, args.timeout, args.threshold,
                args.ready_pattern,
            )
        elif args.mode == "behavior":
            report = gate_behavior(
                args.mod, project_dir, rt, args.checks, args.deps, args.server, args.port, args.timeout,
                args.done_timeout, args.ready_pattern,
            )
        else:
            report = gate_ingame(
                args.mod, project_dir, rt, args.deps, args.server, args.port,
                args.timeout, args.settle, args.ready_pattern,
            )
    except SystemExit:  # resolve_project_dir already printed why on stderr
        return _error("no usable project: run /dayz-init", args.json)
    except (GateError, OSError, ValueError, re.error) as e:
        return _error(str(e), args.json)
    except Exception as e:  # any other crash is ERROR (exit 2), never a FAIL
        return _error(f"gate crashed: {type(e).__name__}: {e}", args.json)
    save_health(report, project_dir)
    emit(report, args.json)
    return 0 if report["verdict"] == "PASS" else 1


def _prepared(mod: str, project_dir: Path, checks_path: Optional[Path], instance: str, as_json: bool) -> int:
    """--prepare-only: write the copy, print PREPARED and how to run it by hand."""
    checks = behavior.load_checks(checks_path or behavior.default_checks_path(project_dir, mod))
    prepared = behavior.prepare_instance(project_dir, instance, checks)
    info = {"verdict": "PREPARED", "instance": prepared["instance"], "init": _rel(prepared["init"], project_dir), "checks": len(checks)}
    print("PREPARED")
    if as_json:
        print(json.dumps(info, indent=2))
    else:
        print(f"  instance {info['instance']}: {info['checks']} checks in {info['init']}")
        print(f"  run: /dayz-launch-test {mod} --server {info['instance']}, then gate.py behavior {mod} --logs")
    return 0


def _dir_arg(value: object) -> Optional[Path]:
    """--compare / --accept: a folder, or True when given with no folder (the newest run)."""
    return None if value is True else value


def _accepted(mod: str, project_dir: Path, shots_path: Optional[Path], run_dir: object,
              only: Optional[list[str]], as_json: bool) -> int:
    """--accept: copy captures into the baseline folder, print ACCEPTED."""
    spec = visual.load_shots(shots_path or visual.default_shots_path(project_dir, mod))
    run_dir = _dir_arg(run_dir) or visual.latest_run_dir(project_dir, mod)
    done = visual.accept(spec, run_dir, visual.baseline_dir(project_dir, mod), only)
    info = {"verdict": "ACCEPTED", "shots": done, "from": _rel(run_dir, project_dir),
            "baseline": _rel(visual.baseline_dir(project_dir, mod), project_dir)}
    print("ACCEPTED")
    print(json.dumps(info, indent=2) if as_json else f"  {len(done)} baseline(s) in {info['baseline']}: {', '.join(done)}")
    return 0


def _error(message: str, as_json: bool) -> int:
    print("ERROR")
    print(json.dumps({"verdict": "ERROR", "error": message}, indent=2) if as_json else f"  {message}")
    return 2


if __name__ == "__main__":
    # Log lines can hold characters a cp1252 console can't print.
    sys.stdout.reconfigure(errors="replace")
    sys.exit(main())
