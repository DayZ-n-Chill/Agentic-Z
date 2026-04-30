"""dayz-launch-test: Launch a local DayZ Diag server + diag client for a built mod.

Verifies state and launches. Setup (mission copy, per-map serverDZ.cfg, profiles/)
is the responsibility of /dayz-add-map — this skill refuses to run if the map
hasn't been set up yet.

Always launches the server first per L2 conventions — DayZ cannot be tested
standalone. Both server and client run from DayZDiag_x64.exe with -filePatching.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKSPACE = REPO_ROOT / "workspace"
PREFLIGHT_DIR = REPO_ROOT / ".claude" / "skills" / "dayz-preflight"
PREFLIGHT = PREFLIGHT_DIR / "preflight.py"
P_DRIVE = Path("P:\\")
MODS_ROOT = P_DRIVE / "Mods"
SERVER_ROOT = WORKSPACE / "_server"
MISSIONS_DIR = SERVER_ROOT / "missions"
MAPS_DIR = SERVER_ROOT / "maps"
CLIENT_DIAG_LOGS = SERVER_ROOT / "!ClientDiagLogs"

# Per-clone client display preferences (windowed mode, resolution). Lives under
# .claude/local-memory/ so each clone of the template can have its own setup
# without affecting the repo. Created with sane defaults on first launch; the
# user can edit it freely afterward.
LOCAL_MEMORY = REPO_ROOT / ".claude" / "local-memory"
CLIENT_DISPLAY_PREFS = LOCAL_MEMORY / "dayz-client-display.json"
DEFAULT_CLIENT_DISPLAY: dict = {
    "windowed": True,
    "width": 1920,
    "height": 1080,
}

# Friendly map name -> mission template folder under MISSIONS_DIR. Mirrors the
# table in dayz-add-map; both skills must agree.
KNOWN_MAPS: dict[str, str] = {
    "chernarus": "dayzOffline.chernarusplus",
    "livonia": "dayzOffline.enoch",
    "sakhal": "dayzOffline.sakhal",
}
DEFAULT_MAP = "chernarus"

OK = "[OK]   "
WARN = "[WARN] "
FAIL = "[FAIL] "


def _load_preflight_module():
    """Load preflight.py by file path so static analyzers don't choke on a
    sys.path-based sibling import (preflight lives in dayz-preflight/, a sibling
    skill folder)."""
    spec = importlib.util.spec_from_file_location("dayz_preflight_module", PREFLIGHT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load preflight module at {PREFLIGHT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_preflight = _load_preflight_module()
find_dayz_diag = _preflight.find_dayz_diag


def gate_on_preflight() -> None:
    if not PREFLIGHT.exists():
        sys.exit(f"{FAIL} dayz-preflight skill not found at {PREFLIGHT.relative_to(REPO_ROOT)}")
    result = subprocess.run([sys.executable, str(PREFLIGHT)])
    if result.returncode != 0:
        sys.exit(result.returncode)


def verify_built_mods(modnames: list[str]) -> None:
    """Confirm each mod has at least one .pbo under @<ModName>/Addons/.

    Most scaffolded mods produce a single <ModName>.pbo, but some mods
    (multi-PBO layouts like Colorful-UI's GUI/ + Scripts/ split) ship
    multiple .pbo files. We accept any .pbo in the Addons folder rather
    than requiring the file be named after the mod.
    """
    for name in modnames:
        addons_dir = MODS_ROOT / f"@{name}" / "Addons"
        if not addons_dir.exists():
            sys.exit(
                f"{FAIL} Mod '{name}' has no Addons folder at {addons_dir}\n"
                f"       Run: python .claude/skills/dayz-build-pbo/build.py {name}"
            )
        pbos = sorted(addons_dir.glob("*.pbo"))
        if not pbos:
            sys.exit(
                f"{FAIL} Mod '{name}' has no .pbo files in {addons_dir}\n"
                f"       Run: python .claude/skills/dayz-build-pbo/build.py {name}"
            )
        if len(pbos) == 1:
            print(f"{OK} {name} PBO present: {pbos[0]}")
        else:
            print(f"{OK} {name} ({len(pbos)} PBOs): {', '.join(p.name for p in pbos)}")


def resolve_diag_client() -> Path:
    """Returns the path to DayZDiag_x64.exe — required for filePatching to work.

    Retail DayZ_x64.exe blocks past the loading screen with -filePatching enabled,
    so mod testing always uses the diag build.
    """
    diag = find_dayz_diag()
    if diag is None:
        sys.exit(
            f"{FAIL} DayZDiag_x64.exe not found.\n"
            "       DayZ Diag is the diagnostic client required for mod development\n"
            "       (retail DayZ_x64.exe doesn't allow filePatching past the loading screen).\n"
            "       Lives in the DayZ game install dir alongside DayZ_x64.exe.\n"
            "       Set DAYZ_DIAG_PATH or verify your DayZ install is up to date."
        )
    print(f"{OK} Diag client: {diag}")
    return diag


def resolve_mission_template(map_name: str) -> str:
    """Map a user-friendly map name to its mission template folder name.

    Known names get their canonical mapping. Unknown names pass through, so
    custom missions can be referenced by their actual folder name (e.g.
    --map dayzOffline.namalsk).
    """
    return KNOWN_MAPS.get(map_name, map_name)


def verify_map_environment(map_name: str) -> tuple[Path, Path, Path]:
    """Verify workspace/_server/maps/<map>/ exists with serverDZ.cfg + profiles/,
    and that the mission template folder is present under workspace/_server/missions/.

    Does NOT create anything — that's /dayz-add-map's job. Hard-fails with a hint
    if state is missing.

    Returns (cfg_path, profile_dir, mission_path).
    """
    template = resolve_mission_template(map_name)
    mission_path = MISSIONS_DIR / template
    map_dir = MAPS_DIR / map_name
    cfg_path = map_dir / "serverDZ.cfg"
    profile_dir = map_dir / "profiles"

    missing = []
    if not mission_path.exists():
        missing.append(f"mission folder: {mission_path.relative_to(REPO_ROOT)}")
    if not cfg_path.exists():
        missing.append(f"server cfg: {cfg_path.relative_to(REPO_ROOT)}")
    if missing:
        details = "\n".join(f"          - {m}" for m in missing)
        sys.exit(
            f"{FAIL} Map '{map_name}' is not set up. Missing:\n{details}\n"
            f"       Run: python .claude/skills/dayz-add-map/add_map.py {map_name}"
        )

    # Existing cfg — auto-append allowFilePatching=1 if missing (clients launch
    # with -filePatching; without this setting the server refuses connection,
    # error 0x00020005). This is the only mutation the launch skill performs.
    cfg = cfg_path.read_text(encoding="utf-8")
    if "allowFilePatching" not in cfg:
        cfg = cfg.rstrip() + "\nallowFilePatching = 1;\n"
        cfg_path.write_text(cfg, encoding="utf-8")
        print(f"{OK} Appended allowFilePatching = 1 to {cfg_path.relative_to(REPO_ROOT)}")

    profile_dir.mkdir(parents=True, exist_ok=True)
    print(f"{OK} Map: {map_name}  (mission: {template})")
    print(f"{OK} Map dir: {map_dir.relative_to(REPO_ROOT)}")
    return cfg_path, profile_dir, mission_path


def build_server_cmd(
    diag_exe: Path,
    mod_arg: str,
    port: int,
    cfg_path: Path,
    profile_dir: Path,
    mission_path: Path,
) -> list[str]:
    """Build the diagnostic server launch command.

    Uses DayZDiag_x64.exe with `-server` — both client and server must be diag
    for `-filePatching` to work end-to-end. The retail DayZServer_x64.exe also
    blocks filePatching past the loading screen, same as retail DayZ_x64.exe.
    """
    return [
        str(diag_exe),
        "-server",
        f"-config={cfg_path}",
        f"-profiles={profile_dir}",
        f"-mission={mission_path}",
        f"-mod={mod_arg}",
        "-filePatching",
        f"-port={port}",
    ]


def read_client_display_prefs() -> dict:
    """Read client display preferences (windowed/resolution) from local-memory.

    Creates the file with DEFAULT_CLIENT_DISPLAY (1080p windowed) on first run.
    Per-clone, gitignored — the user's monitor setup doesn't belong in the repo.

    The file is JSON so the user can edit it without running any skill:
        {"windowed": true, "width": 1920, "height": 1080}
    """
    if CLIENT_DISPLAY_PREFS.exists():
        try:
            return json.loads(CLIENT_DISPLAY_PREFS.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print(f"{WARN} Could not parse {CLIENT_DISPLAY_PREFS.relative_to(REPO_ROOT)}: {e}")
            print(f"{WARN} Falling back to defaults: {DEFAULT_CLIENT_DISPLAY}")
            return dict(DEFAULT_CLIENT_DISPLAY)
    LOCAL_MEMORY.mkdir(parents=True, exist_ok=True)
    CLIENT_DISPLAY_PREFS.write_text(
        json.dumps(DEFAULT_CLIENT_DISPLAY, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"{OK} Wrote default client display prefs to "
        f"{CLIENT_DISPLAY_PREFS.relative_to(REPO_ROOT)}"
    )
    return dict(DEFAULT_CLIENT_DISPLAY)


def build_client_cmd(
    diag_exe: Path, mod_arg: str, port: int, client_profile: Path, display: dict
) -> list[str]:
    """Build the diagnostic client launch command.

    Uses DayZDiag_x64.exe (not retail DayZ_x64.exe) so -filePatching actually
    lets the player into the world.

    `-profiles=<client_profile>` points client-side diag artifacts
    (!ClientDiagLogs/, BattlEye/, player profile, script logs) at our workspace
    root rather than the default location next to the exe (which would clutter
    the DayZ game install dir).

    `-window` + `-x=<W> -y=<H>` honor the user's display prefs (default 1080p
    windowed) so the game doesn't grab fullscreen on ultra-wide monitors.
    """
    cmd = [
        str(diag_exe),
        f"-profiles={client_profile}",
        f"-mod={mod_arg}",
        "-connect=127.0.0.1",
        f"-port={port}",
        "-filePatching",
    ]
    if display.get("windowed"):
        cmd.append("-window")
    width = display.get("width")
    height = display.get("height")
    if width:
        cmd.append(f"-x={width}")
    if height:
        cmd.append(f"-y={height}")
    return cmd


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Launch local DayZ server + client with one or more built mods."
    )
    parser.add_argument("modnames", nargs="+", help="Mod names already built (PBO must exist).")
    parser.add_argument(
        "--map",
        default=DEFAULT_MAP,
        help=(
            f"Map to test on (default: {DEFAULT_MAP}). Known aliases: "
            f"{', '.join(KNOWN_MAPS)}. Custom missions: pass the mission folder "
            "name (e.g. dayzOffline.namalsk)."
        ),
    )
    parser.add_argument("--port", type=int, default=2302, help="Server port (default: 2302).")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resolved commands without launching anything.",
    )
    args = parser.parse_args()

    gate_on_preflight()
    print()
    verify_built_mods(args.modnames)
    diag_exe = resolve_diag_client()
    cfg_path, profile_dir, mission_path = verify_map_environment(args.map)

    # Client profile is workspace/_server/!ClientDiagLogs/ — diag artifacts
    # (Users/, DataCache/, BattlEye/, RPT, script logs) get contained inside this
    # one folder rather than spread across the _server root or polluting the DayZ
    # game install dir.
    CLIENT_DIAG_LOGS.mkdir(parents=True, exist_ok=True)
    client_profile = CLIENT_DIAG_LOGS

    display = read_client_display_prefs()

    # Absolute mod paths — the engine resolves -mod=<arg> relative to its CWD
    # (Bash's CWD when subprocess.Popen inherits), so a bare "@Sandbox" looks
    # for <repo-root>/@Sandbox which doesn't exist. Always pass the full path
    # via the P:\Mods junction so the engine actually finds the PBO.
    mod_arg = ";".join(str(MODS_ROOT / f"@{name}") for name in args.modnames)
    server_cmd = build_server_cmd(
        diag_exe, mod_arg, args.port, cfg_path, profile_dir, mission_path
    )
    client_cmd = build_client_cmd(diag_exe, mod_arg, args.port, client_profile, display)

    if args.dry_run:
        print()
        print(f"[DRY-RUN] Server cmd: {' '.join(server_cmd)}")
        print(f"[DRY-RUN] Client cmd: {' '.join(client_cmd)}")
        return 0

    print()
    print(f"[Launch] Server: {' '.join(server_cmd)}")
    sys.stdout.flush()
    server_proc = subprocess.Popen(server_cmd)
    print(f"{OK} Server PID: {server_proc.pid}")
    print("        Waiting 5s for server to start listening...")
    sys.stdout.flush()
    time.sleep(5)

    print()
    print(f"[Launch] Client: {' '.join(client_cmd)}")
    sys.stdout.flush()
    client_proc = subprocess.Popen(client_cmd)
    print(f"{OK} Client PID: {client_proc.pid}")

    print()
    print("Both running. Close the windows manually to stop.")
    print(f"  Server PID: {server_proc.pid}    Client PID: {client_proc.pid}")
    print(f"  Logs: {profile_dir.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
