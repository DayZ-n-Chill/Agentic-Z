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
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
import skill_helpers as h  # noqa: E402

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

DEFAULT_INSTANCE = "chernarus"

OK, WARN, FAIL = h.OK, h.WARN, h.FAIL
SERVER_BIND_TIMEOUT_S = 180

find_dayz_diag = h.preflight.find_dayz_diag


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
                f"       Run: /dayz-build-pbo {name}"
            )
        pbos = sorted(addons_dir.glob("*.pbo"))
        if not pbos:
            sys.exit(
                f"{FAIL} Mod '{name}' has no .pbo files in {addons_dir}\n"
                f"       Run: /dayz-build-pbo {name}"
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


def read_cfg_template(cfg_text: str) -> str | None:
    """The mission template named by `template = "...";` in serverDZ.cfg, or None."""
    match = re.search(r'\btemplate\s*=\s*"([^"]+)"', cfg_text)
    return match.group(1) if match else None


def verify_instance_environment(
    instance: str, project_dir: Path, dry_run: bool = False
) -> tuple[Path, Path, Path, Path]:
    """Verify .server/<instance>/ was set up by /dayz-add-server.

    Checks serverDZ.cfg exists, names a mission template and has an active
    `allowFilePatching = 1;` line (missing, commented out or any other value
    counts as missing), and that the <template>/ junction to mission/ exists.
    Hard-fails with a hint to run /dayz-add-server if anything is missing.

    Outside --dry-run it ensures the two profile dirs exist; with dry_run it
    changes nothing.

    Returns (cfg_path, server_profile_dir, mission_path, client_profile_dir).
    server_profile_dir is per-instance .server/<instance>/Profiles/.
    client_profile_dir is shared top-level .server/!ClientDiagLogs/.
    """
    server_root = project_dir / ".server"
    inst_dir = server_root / instance
    cfg_path = inst_dir / "serverDZ.cfg"
    server_profile_dir = inst_dir / "Profiles"
    client_profile_dir = server_root / "!ClientDiagLogs"
    mission_dir = inst_dir / "mission"

    missing = []
    cfg = cfg_path.read_text(encoding="utf-8") if cfg_path.is_file() else None
    template = read_cfg_template(cfg) if cfg is not None else None
    if cfg is None:
        missing.append(f"server cfg: {cfg_path.relative_to(project_dir)}")
    else:
        if template is None:
            missing.append(f'template = "..."; line in {cfg_path.relative_to(project_dir)}')
        # Clients launch with -filePatching; without allowFilePatching = 1 the
        # server refuses the connection (error 0x00020005).
        setting = h.file_patching_setting(cfg)
        if setting is None or setting.group(1) != "1":
            missing.append(f"allowFilePatching = 1; in {cfg_path.relative_to(project_dir)}")
    if not mission_dir.exists():
        missing.append(f"mission folder: {mission_dir.relative_to(project_dir)}")

    # -mission= must point at a path NAMED after the mission template the cfg
    # loads (e.g. dayzOffline.chernarusplus), not at "mission/": the engine
    # resolves the template name during the client connect handshake, and
    # without it the client connects but never spawns. /dayz-add-server creates
    # the <template>/ -> mission/ junction.
    mission_path = inst_dir / template if template else mission_dir
    if template and mission_dir.exists() and not mission_path.is_dir():
        missing.append(
            f"mission template junction ({template}/ -> mission/) in {inst_dir.relative_to(project_dir)}"
        )

    if missing:
        details = "\n".join(f"          - {m}" for m in missing)
        sys.exit(
            f"{FAIL} Instance '{instance}' is not set up. Missing:\n{details}\n"
            f"       Run: /dayz-add-server {instance}"
        )

    if not dry_run:
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


def display_prefs_problem(prefs) -> str | None:
    """Why parsed display prefs are unusable, or None when they are fine.

    Valid JSON can still have the wrong shape (a list, "width": "1920"), which
    would crash on .get() or put a bad value on the client command line.
    """
    if not isinstance(prefs, dict):
        return f"expected a JSON object, got {type(prefs).__name__}"
    if "windowed" in prefs and not isinstance(prefs["windowed"], bool):
        return '"windowed" must be true or false'
    for key in ("width", "height"):
        if key in prefs:
            value = prefs[key]
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                return f'"{key}" must be a positive whole number'
    return None


def read_client_display_prefs(project_dir: Path, create: bool = True) -> dict:
    """Read client display preferences (windowed/resolution) from local-memory.

    Creates the file with DEFAULT_CLIENT_DISPLAY (1080p windowed) on first run,
    unless create is False (--dry-run), which just returns the defaults.
    Per-clone, gitignored; the user's monitor setup doesn't belong in the repo.

    The file is JSON so the user can edit it without running any skill:
        {"windowed": true, "width": 1920, "height": 1080}
    """
    local_memory = project_dir / ".claude" / "local-memory"
    prefs_path = local_memory / CLIENT_DISPLAY_PREFS_NAME
    if prefs_path.exists():
        try:
            prefs = json.loads(prefs_path.read_text(encoding="utf-8"))
            problem = display_prefs_problem(prefs)
        except (json.JSONDecodeError, OSError) as e:
            problem = str(e)
        if problem is None:
            return prefs
        print(f"{WARN} Could not use {prefs_path.relative_to(project_dir)}: {problem}")
        print(f"{WARN} Falling back to defaults: {DEFAULT_CLIENT_DISPLAY}")
        return dict(DEFAULT_CLIENT_DISPLAY)
    if not create:
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
    """Wait until the DayZ server has bound UDP `port`. Returns True when bound
    within `timeout_s`, False if it gives up.

    Detection: h.udp_port_free tries to bind the same UDP port (and always
    closes its socket). If that bind fails, the server is holding the port;
    we're good. If it succeeds, the server hasn't bound yet, so retry.

    DayZ does not respond to Source Engine Query on the game port, so packet-
    based probes don't work. Bind-collision is the reliable signal.

    DayZ servers can take 30+ seconds to fully init (mission load, mod load,
    persistence init) before binding the network port; previous fixed-5s
    sleep was way too short.
    """
    print(f"        Waiting up to {timeout_s}s for server to bind UDP port {port}...")
    sys.stdout.flush()
    deadline = time.time() + timeout_s
    last_dot = time.time()
    while time.time() < deadline:
        if server_proc.poll() is not None:
            print(f"\n{FAIL} Server process exited unexpectedly (rc={server_proc.returncode}).")
            return False
        if not h.udp_port_free(port):
            print(f"\n{OK} Server has bound UDP port {port}")
            return True
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

    `-profiles=<client_profile>` points the client at our shared
    .server/!ClientDiagLogs/ dir (RPT, BattlEye/, player profile, script logs)
    rather than the default location next to the exe (which would clutter the
    DayZ game install dir).

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

    project_dir = h.resolve_project_dir()
    h.gate_on_preflight()
    print()
    print(f"{OK} Project: {project_dir}")
    gate_on_old_layout(project_dir)
    verify_built_mods(args.modnames)
    diag_exe = resolve_diag_client()
    cfg_path, server_profile_dir, mission_path, client_profile_dir = verify_instance_environment(
        args.server, project_dir, dry_run=args.dry_run
    )

    display = read_client_display_prefs(project_dir, create=not args.dry_run)

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

    # A server already on this port would make the new one fail to bind, and
    # wait_for_server_port would mistake the old server for the new one.
    h.gate_on_free_port(args.port)

    print()
    print(f"[Launch] Server: {' '.join(server_cmd)}")
    sys.stdout.flush()
    server_proc = subprocess.Popen(server_cmd)
    print(f"{OK} Server PID: {server_proc.pid}")
    sys.stdout.flush()
    if not wait_for_server_port(args.port, server_proc, timeout_s=SERVER_BIND_TIMEOUT_S):
        if server_proc.poll() is None:
            server_proc.kill()
            print(f"{FAIL} Server did not bind to port {args.port} within {SERVER_BIND_TIMEOUT_S}s; killed it.")
        print(f"       Check the server RPT in {server_profile_dir}\\ for errors.")
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
