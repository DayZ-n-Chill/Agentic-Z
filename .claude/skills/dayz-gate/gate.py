"""dayz-gate: script-only build and in-game gates for the mod team.

  gate.py build  <ModName> [--json]
  gate.py ingame <ModName> [--deps CF ...] [--server <instance>] [--port N]
                 [--timeout S] [--settle S] [--ready-pattern REGEX] [--json]

Both modes stop a running DayZDiag session first, run the existing skill
scripts (/dayz-build-pbo, /dayz-deploy-pbo, /dayz-launch-test) as subprocesses,
apply the pass/fail rules of the dayz-build-checker and dayz-ingame-tester
agents, triage every failure against known-errors.json, and print the verdict
on the first line (PASS, FAIL, or ERROR), then a summary or, with --json, JSON.

Exit codes: 0 PASS, 1 FAIL, 2 usage or environment error in the gate itself
(the orchestrator then falls back to the gate agents). See SKILL.md.
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

BUILD_PY = SKILLS_DIR / "dayz-build-pbo" / "build.py"
DEPLOY_PY = SKILLS_DIR / "dayz-deploy-pbo" / "deploy.py"
LAUNCH_PY = SKILLS_DIR / "dayz-launch-test" / "launch.py"
STOP_BAT = SKILLS_DIR / "dayz-stop-test" / "stop_test.bat"
DIAG_EXE = "DayZDiag_x64.exe"

DEFAULT_TIMEOUT_S = 300  # dayz-ingame-tester gives the client five minutes
DEFAULT_SETTLE_S = 30    # keep reading after the ready signal to catch spawn-time errors
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
BUILD_ERROR_RE = re.compile(r"(?i)\berror\b|\bfailed\b|undefined base class|encountered instead of")
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


def real_runtime() -> Runtime:
    def diag_pids() -> list[int]:
        _, out = run_captured(["tasklist", "/FI", f"IMAGENAME eq {DIAG_EXE}", "/FO", "CSV", "/NH"])
        return parse_tasklist(out)

    def pid_alive(pid: int) -> bool:
        _, out = run_captured(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"])
        return bool(parse_tasklist(out, pid))

    return Runtime(run=run_captured, diag_pids=diag_pids, pid_alive=pid_alive)


# --- shared steps -------------------------------------------------------------

def stop_session(rt: Runtime) -> dict:
    """Stop every DayZDiag_x64.exe with /dayz-stop-test; GateError if any survive."""
    pids = rt.diag_pids()
    if not pids:
        return {"step": "stop-session", "result": "no DayZDiag session running"}
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


def gate_build(mod: str, project_dir: Path, rt: Runtime) -> dict:
    report = new_report("build", mod)
    report["steps"].append(stop_session(rt))
    mod_dir = project_dir / "workspace" / mod
    has_cfg, has_payload = bundle_layout(mod_dir)
    # Tier 2 conventions/config.md, "Bundle / umbrella mods": a payload-only bundle has nothing to build;
    # a bundle with a linker config.cpp is built, then its payload deployed.
    if has_cfg or not has_payload:
        rc, out = rt.run([sys.executable, str(BUILD_PY), mod])
        findings = parse_build_output(out)
        report["steps"].append({"step": "dayz-build-pbo", "rc": rc})
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
        text = cfg.read_text(encoding="utf-8", errors="replace")
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
    text = re.sub(r"//[^\n]*|/\*.*?\*/", "", text, flags=re.DOTALL)
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
    report = new_report("ingame", mod)
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
            lines, ready, problem = watch_session(rt, logs, client_dir, pids, ready_re, timeout, settle)
            report["ready"] = ready
            if problem is not None:
                extra.append(problem)
    finally:
        report["steps"].append(stop_session(rt))  # always, even after a failure
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
    return finish(report, project_dir, {"instance": instance})


def watch_session(
    rt: Runtime, logs: LogTail, client_dir: Path, pids: list[int], ready_re: re.Pattern, timeout: float, settle: float
) -> tuple[list[tuple[Path, int, str]], Optional[dict], Optional[dict]]:
    """Poll the logs until the client is in the mission plus `settle` seconds.

    Returns (lines read, ready signal or None, failure or None). Stops early
    when a script module fails to compile, a crash log appears, or the server
    or client process exits.
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
        if any(triage.classify(t) == "compile" and "script module" in t for _, _, t in new):
            return lines, ready, None
        if any(p.name.lower().startswith("crash") for p in logs.new_files()):
            return lines, ready, None
        dead = [pid for pid in pids if not rt.pid_alive(pid)]
        if dead:
            return lines, ready, _finding("crash", f"DayZDiag process exited before the gate stopped it (PID {', '.join(map(str, dead))})", "process", None)
        now = rt.clock()
        if ready_at is not None and now - ready_at >= settle:
            return lines, ready, None
        if now >= deadline:
            return lines, ready, _finding(
                "no_ready",
                f"client never reached the mission within {int(timeout)} s (no line matching {ready_re.pattern!r} in the client script log)",
                "client", None,
            )
        rt.sleep(POLL_S)


# --- report -------------------------------------------------------------------

def new_report(mode: str, mod: str) -> dict:
    return {"verdict": None, "mode": mode, "mod": mod, "steps": [], "failures": [], "warnings": [], "noise": []}


def dedupe(findings: list[dict]) -> list[dict]:
    """One finding per fingerprint (head line plus stack), first occurrence kept, with a count."""
    seen: dict[str, dict] = {}
    for f in findings:
        key = triage.fingerprint(" | ".join([f["text"], *f["context"][:3]]))
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
    for step in report["steps"]:
        out.append(f"  {step['step']}: " + (f"exit {step['rc']}" if "rc" in step else step["result"]))
    if report.get("ready"):
        out.append(f"  ready: {report['ready']['file']}:{report['ready']['line']}  {report['ready']['text']}")
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
    return "\n".join(out)


def emit(report: dict, as_json: bool) -> None:
    print(report["verdict"])
    print(json.dumps(report, indent=2) if as_json else render_text(report))


def main(argv: Optional[list[str]] = None, rt: Optional[Runtime] = None) -> int:
    parser = argparse.ArgumentParser(description="Script-only build and in-game gates.")
    sub = parser.add_subparsers(dest="mode", required=True)
    b = sub.add_parser("build", help="Build (or deploy a bundle) and check the output.")
    b.add_argument("mod")
    b.add_argument("--json", action="store_true")
    g = sub.add_parser("ingame", help="Launch server and client, read the logs, stop the session.")
    g.add_argument("mod")
    g.add_argument("--deps", nargs="+", default=[], metavar="MOD", help="Dependency mods in load order (CF or @CF).")
    g.add_argument("--server", default="chernarus", help="Server instance (default chernarus).")
    g.add_argument("--port", type=int, default=2302)
    g.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S, help="Seconds to wait for the client to reach the mission.")
    g.add_argument("--settle", type=float, default=DEFAULT_SETTLE_S, help="Seconds to keep reading after the ready signal.")
    g.add_argument("--ready-pattern", default=DEFAULT_READY_RE, help="Regex in the client script log that means the mission is running.")
    g.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code == 0 else 2

    try:
        if args.mode == "ingame":
            re.compile(args.ready_pattern)
        project_dir = h.resolve_project_dir()
        rt = rt or real_runtime()
        if args.mode == "build":
            report = gate_build(args.mod, project_dir, rt)
        else:
            report = gate_ingame(
                args.mod, project_dir, rt, args.deps, args.server, args.port,
                args.timeout, args.settle, args.ready_pattern,
            )
    except SystemExit:  # resolve_project_dir already printed why on stderr
        return _error("no usable project: run /dayz-init", args.json)
    except (GateError, OSError, ValueError, re.error) as e:
        return _error(str(e), args.json)
    emit(report, args.json)
    return 0 if report["verdict"] == "PASS" else 1


def _error(message: str, as_json: bool) -> int:
    print("ERROR")
    print(json.dumps({"verdict": "ERROR", "error": message}, indent=2) if as_json else f"  {message}")
    return 2


if __name__ == "__main__":
    # Log lines can hold characters a cp1252 console can't print.
    sys.stdout.reconfigure(errors="replace")
    sys.exit(main())
