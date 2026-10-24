"""dayz-gate visual: the shots file, window capture, baselines and the perceptual compare.

gate.py imports this module. The visual gate runs the in-game flow and, at the
seconds after the client joins that the shots file names, captures the DayZ
client window to output/<ModName>-visual/runs/<stamp>/<shot id>.png. Each
capture is compared with output/<ModName>-visual/baseline/<shot id>.png:

  * both images are shrunk to ANALYSIS_WIDTH with a box filter, which averages
    away single pixel noise such as anti-aliasing and dithering;
  * a pixel differs when its YIQ colour distance (the pixelmatch measure, which
    weights brightness over hue the way the eye does) is above PIXEL_TOLERANCE
    of the largest possible distance;
  * the shot fails when the share of differing pixels is above its threshold.

Every compare writes <shot id>.diff.png next to the capture: the baseline in
pale grey, differing pixels in red and ignored areas in blue.

capture_window() is the only part that needs Windows and a running client; the
tests pass their own capture function instead.
"""
from __future__ import annotations

import json
import re
import shutil
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

HERE = Path(__file__).resolve().parent
REQUIREMENTS = HERE / "requirements.txt"

SHOTS_FILENAME = "visual-shots.json"
DEFAULT_THRESHOLD = 0.01  # share of compared pixels allowed to differ
PIXEL_TOLERANCE = 0.1     # per pixel: share of the largest YIQ distance (pixelmatch default)
ANALYSIS_WIDTH = 640
MAX_YIQ_DELTA = 35215.0   # YIQ distance between black and white

SHOT_KEYS = {"id", "feature", "at", "threshold", "ignore"}
FILE_KEYS = {"mod", "threshold", "shots"}
ID_RE = re.compile(r"^[A-Za-z0-9][\w.-]{0,63}$")

PASS, FAIL, NEW, MISSING = "PASS", "FAIL", "NEW", "MISSING"


class VisualError(ValueError):
    """A bad shots file, a missing image or a capture that could not run (gate exit 2 or one failed shot)."""


def _pil():
    try:
        from PIL import Image
    except ImportError as e:
        raise VisualError(f'Pillow is not installed. Install it: py -m pip install -r "{REQUIREMENTS}"') from e
    return Image


# --- paths ------------------------------------------------------------------------

def default_shots_path(project_dir: Path, mod: str) -> Path:
    return project_dir / "output" / f"{mod}-plan" / SHOTS_FILENAME


def visual_dir(project_dir: Path, mod: str) -> Path:
    return project_dir / "output" / f"{mod}-visual"


def baseline_dir(project_dir: Path, mod: str) -> Path:
    return visual_dir(project_dir, mod) / "baseline"


def new_run_dir(project_dir: Path, mod: str) -> Path:
    """The folder for this run's captures; Capturer creates it with the first one."""
    return visual_dir(project_dir, mod) / "runs" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def latest_run_dir(project_dir: Path, mod: str) -> Path:
    runs = visual_dir(project_dir, mod) / "runs"
    found = sorted(p for p in runs.iterdir() if p.is_dir()) if runs.is_dir() else []
    if not found:
        raise VisualError(f"no captures in {runs}; run the visual gate or pass a folder")
    return found[-1]


# --- shots file --------------------------------------------------------------------

def load_shots(path: Path) -> dict:
    if not path.is_file():
        raise VisualError(f"no shots file at {path}; write one (see shots-file.md in the dayz-gate skill) or pass --shots")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        raise VisualError(f"{path}: not valid JSON ({e})") from e
    return validate_shots(data, str(path))


def _fraction(value: object, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise VisualError(f"{where}: threshold must be a number from 0 to 1")
    return float(value)


def validate_shots(data: object, where: str = "shots") -> dict:
    """{"threshold": float or None, "shots": [...]} from a shots file, or VisualError naming the problem."""
    if not isinstance(data, dict) or not isinstance(data.get("shots"), list) or not data["shots"]:
        raise VisualError(f'{where}: expected {{"shots": [...]}} with at least one shot')
    extra = set(data) - FILE_KEYS
    if extra:
        raise VisualError(f"{where}: unknown keys {sorted(extra)}")
    threshold = _fraction(data["threshold"], where) if "threshold" in data else None
    shots, seen = [], set()
    for n, shot in enumerate(data["shots"], 1):
        here = f"{where}: shot {n}"
        if not isinstance(shot, dict):
            raise VisualError(f"{here}: expected an object")
        extra = set(shot) - SHOT_KEYS
        if extra:
            raise VisualError(f"{here}: unknown keys {sorted(extra)}")
        sid = shot.get("id")
        if not isinstance(sid, str) or not ID_RE.match(sid):
            raise VisualError(f"{here}: id must be letters, digits, '_', '.' or '-' with no spaces")
        if sid in seen:
            raise VisualError(f"{here}: duplicate id {sid!r}")
        seen.add(sid)
        at = shot.get("at")
        if isinstance(at, bool) or not isinstance(at, (int, float)) or at < 0:
            raise VisualError(f"{here} ({sid}): at must be the seconds after the client joins, 0 or more")
        ignore = shot.get("ignore", [])
        if not isinstance(ignore, list) or not all(
            isinstance(r, list) and len(r) == 4 and all(isinstance(v, int) and not isinstance(v, bool) and v >= 0 for v in r)
            and r[2] > 0 and r[3] > 0 for r in ignore
        ):
            raise VisualError(f"{here} ({sid}): ignore must be a list of [x, y, width, height] in pixels")
        entry = {"id": sid, "feature": str(shot.get("feature", "")), "at": float(at), "ignore": ignore}
        if "threshold" in shot:
            entry["threshold"] = _fraction(shot["threshold"], f"{here} ({sid})")
        shots.append(entry)
    return {"threshold": threshold, "shots": shots}


def last_shot_at(spec: dict) -> float:
    return max(s["at"] for s in spec["shots"])


# --- capture -----------------------------------------------------------------------

VK_MENU = 0x12          # the Alt key
KEYEVENTF_KEYUP = 0x0002


def bring_to_front(user32, hwnd: int, pid: int, sleep: Callable[[float], None] = time.sleep) -> None:
    """Make hwnd the foreground window, or raise VisualError.

    The gate runs as a background process (an agent's shell or a pipe), and
    Windows' foreground lock refuses SetForegroundWindow from a process that
    did not get the last input event, so a plain call only flashes the
    taskbar button (SetForegroundWindow remarks:
    https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-setforegroundwindow).
    When the first call does not take, the gate sends one Alt press and
    release (keybd_event), the usual workaround that makes this process the
    sender of the last input event, and tries the switch once more. The tap
    goes to whichever window is in front at that moment, just before the
    client takes its place.
    """
    if user32.GetForegroundWindow() == hwnd:
        return
    user32.SetForegroundWindow(hwnd)
    sleep(0.5)  # let the window draw a frame on top
    if user32.GetForegroundWindow() != hwnd:
        user32.keybd_event(VK_MENU, 0, 0, 0)
        user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
        user32.SetForegroundWindow(hwnd)
        sleep(0.5)
    # Windows can still refuse the switch, so check it took.
    if user32.GetForegroundWindow() != hwnd:
        raise VisualError(
            f"the DayZ client window (PID {pid}) could not be brought to the front; "
            "click it and keep it uncovered while the gate runs"
        )


def capture_window(pid: int, out: Path) -> None:
    """Save the client area of the visible window of process `pid` as a PNG (Windows only).

    The window is brought to the front first, because the grab copies what is on
    screen. Raises VisualError when the process has no visible window or the
    window is minimized, or when Windows keeps another window in front (the grab
    would copy that window instead).
    """
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    try:  # physical pixels, so the rectangle matches what ImageGrab copies on a scaled display
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except OSError:
        user32.SetProcessDPIAware()

    found: list[tuple[int, int]] = []
    proc_pid = wintypes.DWORD()
    rect = wintypes.RECT()

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def each(hwnd, _):
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(proc_pid))
        if proc_pid.value == pid and user32.IsWindowVisible(hwnd) and user32.GetClientRect(hwnd, ctypes.byref(rect)):
            found.append((rect.right * rect.bottom, hwnd))
        return True

    user32.EnumWindows(each, 0)
    if not found:
        raise VisualError(f"DayZ client PID {pid} has no visible window")
    hwnd = max(found)[1]
    if user32.IsIconic(hwnd):
        raise VisualError(f"the DayZ client window (PID {pid}) is minimized")
    bring_to_front(user32, hwnd, pid)
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    origin = wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(origin))
    if rect.right <= 0 or rect.bottom <= 0:
        raise VisualError(f"the DayZ client window (PID {pid}) has no client area")
    _pil()
    from PIL import ImageGrab

    bbox = (origin.x, origin.y, origin.x + rect.right, origin.y + rect.bottom)
    ImageGrab.grab(bbox=bbox, all_screens=True).save(out)


class Capturer:
    """Called on every poll of the in-game session; takes each shot once its `at` second has passed."""

    def __init__(self, shots: list[dict], run_dir: Path, capture: Callable[[int, Path], None]):
        self.pending = sorted(shots, key=lambda s: s["at"])
        self.run_dir = run_dir
        self.capture = capture
        self.errors: dict[str, str] = {}

    def __call__(self, elapsed: Optional[float], client_pid: Optional[int]) -> None:
        while elapsed is not None and self.pending and self.pending[0]["at"] <= elapsed:
            shot = self.pending.pop(0)
            try:
                if client_pid is None:
                    raise VisualError("/dayz-launch-test printed no Client PID")
                self.run_dir.mkdir(parents=True, exist_ok=True)
                self.capture(client_pid, self.run_dir / f"{shot['id']}.png")
            except (VisualError, OSError) as e:
                self.errors[shot["id"]] = f"capture failed: {e}"

    def finish(self) -> None:
        """Shots the session ended before."""
        for shot in self.pending:
            self.errors[shot["id"]] = f"not captured: the session ended before {shot['at']:g} s after the client joined"
        self.pending = []


# --- compare -----------------------------------------------------------------------

def _yiq(r: int, g: int, b: int) -> tuple[float, float, float]:
    return (
        0.29889531 * r + 0.58662247 * g + 0.11448223 * b,
        0.59597799 * r - 0.27417610 * g - 0.32180189 * b,
        0.21147017 * r - 0.52261711 * g + 0.31114694 * b,
    )


def compare_images(
    baseline: Path,
    current: Path,
    diff_out: Path,
    threshold: float = DEFAULT_THRESHOLD,
    ignore: Optional[list[list[int]]] = None,
    tolerance: float = PIXEL_TOLERANCE,
    width: int = ANALYSIS_WIDTH,
) -> dict:
    """PASS or FAIL for one capture against its baseline, writing the diff image to `diff_out`."""
    Image = _pil()
    with Image.open(baseline) as b, Image.open(current) as c:
        base, cur = b.convert("RGB"), c.convert("RGB")
    result = {"status": FAIL, "ratio": None, "changed": 0, "compared": 0, "threshold": threshold, "diff": None, "reason": ""}
    if base.size != cur.size:
        result["reason"] = f"capture is {cur.width}x{cur.height}, baseline {base.width}x{base.height}"
        return result

    mask = Image.new("L", base.size, 255)
    for x, y, w, h in ignore or []:
        mask.paste(0, (x, y, x + w, y + h))
    small = (min(width, base.width), max(1, round(base.height * min(width, base.width) / base.width)))
    box = Image.Resampling.BOX
    pa, pb, pm = base.resize(small, box).tobytes(), cur.resize(small, box).tobytes(), mask.resize(small, box).tobytes()

    limit = tolerance * tolerance * MAX_YIQ_DELTA
    out = bytearray(len(pa))
    changed = compared = 0
    for i in range(len(pm)):
        j = i * 3
        r1, g1, b1, r2, g2, b2 = pa[j], pa[j + 1], pa[j + 2], pb[j], pb[j + 1], pb[j + 2]
        grey = 255 - (255 - (r1 * 77 + g1 * 150 + b1 * 29 >> 8)) // 4
        if pm[i] < 255:  # touches an ignored area
            out[j:j + 3] = bytes((grey // 3, grey // 3, 255))
            continue
        compared += 1
        if (r1, g1, b1) != (r2, g2, b2):
            y1, i1, q1 = _yiq(r1, g1, b1)
            y2, i2, q2 = _yiq(r2, g2, b2)
            if 0.5053 * (y1 - y2) ** 2 + 0.299 * (i1 - i2) ** 2 + 0.1957 * (q1 - q2) ** 2 > limit:
                changed += 1
                out[j:j + 3] = b"\xff\x00\x00"
                continue
        out[j:j + 3] = bytes((grey, grey, grey))

    Image.frombytes("RGB", small, bytes(out)).resize(base.size, Image.Resampling.NEAREST).save(diff_out)
    ratio = changed / compared if compared else 0.0
    result.update(ratio=ratio, changed=changed, compared=compared, diff=diff_out)
    if ratio > threshold:
        result["reason"] = f"{ratio:.2%} of pixels differ (threshold {threshold:.2%})"
    else:
        result["status"] = PASS
    return result


def shot_threshold(shot: dict, spec: dict, threshold: Optional[float] = None) -> float:
    """The shot's own threshold, else `threshold` (--threshold), else the shots file's, else DEFAULT_THRESHOLD."""
    if "threshold" in shot:
        return shot["threshold"]
    if threshold is not None:
        return threshold
    return spec["threshold"] if spec["threshold"] is not None else DEFAULT_THRESHOLD


def compare_run(spec: dict, run_dir: Path, base_dir: Path, threshold: Optional[float] = None,
                errors: Optional[dict[str, str]] = None) -> list[dict]:
    """One result per shot: PASS, FAIL, NEW (no baseline yet) or MISSING (no capture).

    The threshold is the shot's own, else `threshold` (the --threshold option),
    else the shots file's, else DEFAULT_THRESHOLD.
    """
    results = []
    for shot in spec["shots"]:
        sid = shot["id"]
        limit = shot_threshold(shot, spec, threshold)
        capture, baseline = run_dir / f"{sid}.png", base_dir / f"{sid}.png"
        entry = {"id": sid, "feature": shot["feature"], "status": MISSING, "ratio": None, "threshold": limit,
                 "capture": capture, "baseline": baseline, "diff": None, "reason": ""}
        if not capture.is_file():
            entry["capture"] = None
            entry["reason"] = (errors or {}).get(sid, f"no capture {capture.name} in {run_dir}")
        elif not baseline.is_file():
            entry["status"] = NEW
            entry["reason"] = "no baseline yet: look at the capture and accept it if it shows the expected look"
        else:
            r = compare_images(baseline, capture, run_dir / f"{sid}.diff.png", limit, shot["ignore"])
            entry.update(status=r["status"], ratio=r["ratio"], diff=r["diff"], reason=r["reason"])
        results.append(entry)
    return results


def backup_dir(base_dir: Path) -> Path:
    """Where accept() keeps each baseline it replaces, as <id>.<stamp>.png."""
    return base_dir / ".prev"


def accept(spec: dict, run_dir: Path, base_dir: Path, only: Optional[list[str]] = None,
           threshold: Optional[float] = None, replace_failed: bool = False) -> dict:
    """Copy captures from `run_dir` into the baseline folder.

    Returns {"accepted": [shot ids], "skipped": [shot ids with no capture in the run],
    "backups": {shot id: path of the old baseline}}. A shot named in `only` with no
    capture is an error; without `only`, shots with no capture are skipped and listed.
    Every baseline that gets replaced is first copied to baseline/.prev/<id>.<stamp>.png.
    A capture that FAILs against its current baseline (the same compare the gate
    runs, with the same threshold) is refused unless `replace_failed`, so a new
    look only becomes the expected one when someone asks for it; nothing is
    copied when any shot is refused.
    """
    ids = [s["id"] for s in spec["shots"]]
    unknown = sorted(set(only or []) - set(ids))
    if unknown:
        raise VisualError(f"not in the shots file: {unknown}")
    wanted = [s for s in spec["shots"] if not only or s["id"] in only]
    missing = [s["id"] for s in wanted if not (run_dir / f"{s['id']}.png").is_file()]
    if missing and only:
        raise VisualError(f"no capture in {run_dir} for {missing}")
    todo = [s for s in wanted if s["id"] not in missing]
    if not todo:
        raise VisualError(f"no captures in {run_dir} to accept")

    if not replace_failed:
        failed = []
        with tempfile.TemporaryDirectory() as scratch:
            for shot in todo:
                sid = shot["id"]
                if (base_dir / f"{sid}.png").is_file():
                    r = compare_images(base_dir / f"{sid}.png", run_dir / f"{sid}.png", Path(scratch) / f"{sid}.diff.png",
                                       shot_threshold(shot, spec, threshold), shot["ignore"])
                    if r["status"] == FAIL:
                        failed.append(f"{sid} ({r['reason']})")
        if failed:
            raise VisualError(
                f"these captures FAIL against their baseline: {', '.join(failed)}. Nothing was accepted. "
                "Look at each capture and its diff; if the new look is right, accept it with --shot <id> --replace-failed"
            )

    base_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
    accepted, backups = [], {}
    for shot in todo:
        sid = shot["id"]
        target = base_dir / f"{sid}.png"
        if target.is_file():
            backup = backup_dir(base_dir) / f"{sid}.{stamp}.png"
            backup.parent.mkdir(exist_ok=True)
            shutil.copy2(target, backup)
            backups[sid] = backup
        shutil.copy2(run_dir / f"{sid}.png", target)
        accepted.append(sid)
    return {"accepted": accepted, "skipped": missing, "backups": backups}
