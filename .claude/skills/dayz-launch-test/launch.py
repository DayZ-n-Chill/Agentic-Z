"""dayz-launch-test: Launch a local DayZ Diag server + diag client for a built mod.

Verifies state and launches. Setup (mission copy, per-instance serverDZ.cfg,
profile dirs) is the responsibility of /dayz-add-server. This skill refuses to
run if the instance hasn't been added yet, or if the legacy workspace/_server/
layout still exists (delete it manually; that layout is no longer supported).

Always launches the server first per L2 conventions (DayZ cannot be tested
standalone). Both server and client run from DayZDiag_x64.exe with -filePatching.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

# REPO_ROOT = where this skill ships from (plugin or template clone).
# Project dir (where .server/ lives) is resolved at runtime from the
# /dayz-init project cache; see resolve_project_dir().
REPO_ROOT = Path(__file__).resolve().parents[3]
PREFLIGHT_DIR = REPO_ROOT / ".claude" / "skills" / "dayz-preflight"
PREFLIGHT = PREFLIGHT_DIR / "preflight.py"
DAYZ_INIT_DIR = REPO_ROOT / ".claude" / "skills" / "dayz-init"
P_DRIVE = Path("P:\\")
MODS_ROOT = P_DRIVE / "Mods"

# Per-clone client display preferences (windowed mode, resolution). Lives under
# <project>/.claude/local-memory/ so each clone of the template can have its
# own setup without affecting the repo. Created with sane defaults on first
# launch; the user can edit it freely afterward.
CLIENT_DISPLAY_PREFS_NAME = "dayz-client-display.json"
DEFAULT_CLIENT_DISPLAY: dict = {
    "windowed": True,
    "width": 1920,
    "height": 1080,
}

# Friendly map name -> mission template folder. Used by verify_instance_environment
# for display purposes; instance layout is flat so no template resolution needed.
KNOWN_MAPS: dict[str, str] = {
    "chernarus": "dayzOffline.chernarusplus",
    "livonia": "dayzOffline.enoch",
    "sakhal": "dayzOffline.sakhal",
}
DEFAULT_INSTANCE = "chernarus"

OK = "[OK]   "
WARN = "[WARN] "
FAIL = "[FAIL] "


def _load_module_from_path(name: str, path: Path):
    """Load a sibling-skill .py as a module by file path so static analyzers don't
    choke on a sys.path-based sibling import."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module at {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_preflight = _load_module_from_path("dayz_preflight_module", PREFLIGHT)
find_dayz_diag = _preflight.find_dayz_diag

# Reuse the project-root cache reader from /dayz-init so launch follows the same source of truth.
_dayz_init_state = _load_module_from_path("dayz_init_state_module", DAYZ_INIT_DIR / "state.py")
cached_project_root = _dayz_init_state.cached_project_root


def resolve_project_dir() -> Path:
    """Return the cached project root, or bail out pointing the user at /dayz-init."""
    project = cached_project_root()
    if project is None:
        print("error: no project cached.", file=sys.stderr)
        print("  Run /dayz-init to set up your DayZ environment and project.", file=sys.stderr)
        sys.exit(2)
    return project.resolve()


def gate_on_preflight() -> None:
    if not PREFLIGHT.exists():
        sys.exit(f"{FAIL} dayz-preflight skill not found at {PREFLIGHT.relative_to(REPO_ROOT)}")
    result = subprocess.run([sys.executable, str(PREFLIGHT)])
    if result.returncode != 0:
        sys.exit(result.returncode)


def gate_on_old_layout(project_dir: Path) -> None:
    """Refuse to run if workspace/_server/ still exists. Forces explicit migration."""
    legacy_server_root = project_dir / "workspace" / "_server"
    if legacy_server_root.exists():
        sys.exit(
            f"{FAIL} Old layout detected at {legacy_server_root.relative_to(project_dir)}.\n"
            "       The server runtime moved from workspace/_server/ to .server/.\n"
            "       Delete the legacy folder manually; that layout is no longer supported."
        )


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
    """Returns the path to DayZDiag_x64.exe; required for filePatching to work.

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


def verify_instance_environment(instance: str, project_dir: Path) -> tuple[Path, Path, Path, Path]:
    """Verify .server/<instance>/ has serverDZ.cfg + mission/ + server-profiles/ + client-profiles/.

    Does NOT create anything (mission, cfg); that's /dayz-add-server's job.
    Hard-fails with a hint if the instance hasn't been added yet.

    Returns (cfg_path, server_profile_dir, mission_path, client_profile_dir).
    """
    server_root = project_dir / ".server"
    inst_dir = server_root / instance
    cfg_path = inst_dir / "serverDZ.cfg"
    server_profile_dir = inst_dir / "server-profiles"
    client_profile_dir = inst_dir / "client-profiles"

    missing = []
    if not cfg_path.exists():
        missing.append(f"server cfg: {cfg_path.relative_to(project_dir)}")

    # CRITICAL: -mission= must point at a path NAMED after the mission template
    # (e.g. dayzOffline.chernarusplus), not at "mission/". The engine resolves the
    # template name during the client connect handshake; pointing at "mission/"
    # means the client connects but never spawns the player. /dayz-add-server
    # creates a junction <template>/ -> mission/ so we can point at it here.
    template_dirs = [p for p in inst_dir.glob("dayzOffline.*") if p.is_dir()]
    if not template_dirs:
        # Fall back to mission/ for the missing-files error message; user will be
        # told to re-run /dayz-add-server which creates the junction.
        mission_path = inst_dir / "mission"
        if not mission_path.exists():
            missing.append(f"mission folder: {mission_path.relative_to(project_dir)}")
        else:
            missing.append(
                f"mission template junction (dayzOffline.<map>/ -> mission/): "
                f"missing in {inst_dir.relative_to(project_dir)}"
            )
    else:
        mission_path = template_dirs[0]

    if missing:
        details = "\n".join(f"          - {m}" for m in missing)
        sys.exit(
            f"{FAIL} Instance '{instance}' is not set up. Missing:\n{details}\n"
            f"       Run: python .claude/skills/dayz-add-server/add_server.py {instance}"
        )

    # Existing cfg: auto-append allowFilePatching=1 if missing (clients launch
    # with -filePatching; without this setting the server refuses connection,
    # error 0x00020005). This is the only mutation the launch skill performs.
    cfg = cfg_path.read_text(encoding="utf-8")
    if "allowFilePatching" not in cfg:
        cfg = cfg.rstrip() + "\nallowFilePatching = 1;\n"
        cfg_path.write_text(cfg, encoding="utf-8")
        print(f"{OK} Appended allowFilePatching = 1 to {cfg_path.relative_to(project_dir)}")

    server_profile_dir.mkdir(parents=True, exist_ok=True)
    client_profile_dir.mkdir(parents=True, exist_ok=True)
    print(f"{OK} Instance: {instance}")
    print(f"{OK} Instance dir: {inst_dir.relative_to(project_dir)}")
    return cfg_path, server_profile_dir, mission_path, client_profile_dir


def build_server_cmd(
    diag_exe: Path,
    mod_arg: str,
    port: int,
    cfg_path: Path,
    profile_dir: Path,
    mission_path: Path,
) -> list[str]:
    """Build the diagnostic server launch command.

    Uses DayZDiag_x64.exe with `-server`; both client and server must be diag
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


def read_client_display_prefs(project_dir: Path) -> dict:
    """Read client display preferences (windowed/resolution) from local-memory.

    Creates the file with DEFAULT_CLIENT_DISPLAY (1080p windowed) on first run.
    Per-clone, gitignored; the user's monitor setup doesn't belong in the repo.

    The file is JSON so the user can edit it without running any skill:
        {"windowed": true, "width": 1920, "height": 1080}
    """
    local_memory = project_dir / ".claude" / "local-memory"
    prefs_path = local_memory / CLIENT_DISPLAY_PREFS_NAME
    if prefs_path.exists():
        try:
            return json.loads(prefs_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print(f"{WARN} Could not parse {prefs_path.relative_to(project_dir)}: {e}")
            print(f"{WARN} Falling back to defaults: {DEFAULT_CLIENT_DISPLAY}")
            return dict(DEFAULT_CLIENT_DISPLAY)
    local_memory.mkdir(parents=True, exist_ok=True)
    prefs_path.write_text(
        json.dumps(DEFAULT_CLIENT_DISPLAY, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"{OK} Wrote default client display prefs to "
        f"{prefs_path.relative_to(project_dir)}"
    )
    return dict(DEFAULT_CLIENT_DISPLAY)


def wait_for_server_port(port: int, server_proc: subprocess.Popen, timeout_s: int = 180) -> bool:
    """Poll UDP port `port` until the DayZ server binds to it. Returns True if
    the port is bound within `timeout_s` seconds (i.e. the server is listening
    and ready for clients), False if it gives up.

    DayZ servers can take 30+ seconds to fully init (mission load, mod load,
    persistence init) before binding the network port. The previous fixed-5s
    sleep was way too short. We poll instead so the client launches as soon
    as the server is actually ready, while still capping at 3 minutes.

    The server's UDP query port is `port + 1` (e.g. 2303 when -port=2302).
    Some DayZ versions also bind UDP port directly. We try the steam query
    port first (more reliable signal of "ready") then the game port.
    """
    print(f"        Waiting up to {timeout_s}s for server port {port} to come up...")
    sys.stdout.flush()
    deadline = time.time() + timeout_s
    last_dot = time.time()
    query_port = port + 1
    while time.time() < deadline:
        if server_proc.poll() is not None:
            print(f"\n{FAIL} Server process exited unexpectedly (rc={server_proc.returncode}).")
            return False
        for probe_port in (query_port, port):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.settimeout(0.5)
                    s.sendto(b"\xFF\xFF\xFF\xFFTSource Engine Query\x00", ("127.0.0.1", probe_port))
                    s.recvfrom(2048)
                    print(f"\n{OK} Server is listening on port {probe_port}")
                    return True
            except (socket.timeout, OSError):
                pass
        if time.time() - last_dot > 5:
            print(".", end="", flush=True)
            last_dot = time.time()
        time.sleep(1)
    print()
    return False


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
        "--server",
        default=DEFAULT_INSTANCE,
        help=(
            f"Server instance to launch on (default: {DEFAULT_INSTANCE}). "
            "Must have been added via /dayz-add-server."
        ),
    )
    parser.add_argument("--port", type=int, default=2302, help="Server port (default: 2302).")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resolved commands without launching anything.",
    )
    args = parser.parse_args()

    project_dir = resolve_project_dir()
    gate_on_preflight()
    print()
    print(f"{OK} Project: {project_dir}")
    gate_on_old_layout(project_dir)
    verify_built_mods(args.modnames)
    diag_exe = resolve_diag_client()
    cfg_path, server_profile_dir, mission_path, client_profile_dir = verify_instance_environment(
        args.server, project_dir
    )

    display = read_client_display_prefs(project_dir)

    # Absolute mod paths so the engine resolves -mod=<arg> correctly regardless
    # of the working directory the subprocess inherits.
    mod_arg = ";".join(str(MODS_ROOT / f"@{name}") for name in args.modnames)
    server_cmd = build_server_cmd(
        diag_exe, mod_arg, args.port, cfg_path, server_profile_dir, mission_path
    )
    client_cmd = build_client_cmd(diag_exe, mod_arg, args.port, client_profile_dir, display)

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
    sys.stdout.flush()
    if not wait_for_server_port(args.port, server_proc, timeout_s=180):
        print(f"{FAIL} Server did not bind to port {args.port} within 180s.")
        print(f"       Check the server RPT in {profile_dir}\\ for errors.")
        return 1

    print()
    print(f"[Launch] Client: {' '.join(client_cmd)}")
    sys.stdout.flush()
    client_proc = subprocess.Popen(client_cmd)
    print(f"{OK} Client PID: {client_proc.pid}")

    print()
    print("Both running. Close the windows manually to stop.")
    print(f"  Server PID: {server_proc.pid}    Client PID: {client_proc.pid}")
    print(f"  Server logs: {server_profile_dir.relative_to(project_dir)}")
    print(f"  Client logs: {client_profile_dir.relative_to(project_dir)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
