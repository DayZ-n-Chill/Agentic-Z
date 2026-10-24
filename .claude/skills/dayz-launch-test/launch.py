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


_SKIP_DIRS = {".git", "addons", "keys"}  # same folders /dayz-lint skips (compared lowercased)
_CLASS_OR_BRACE = re.compile(r"\bclass\s+(\w+)[^;{}]*[;{]|[{}]")


def config_patches(text: str) -> tuple[set[str], list[str]]:
    """(CfgPatches class names, requiredAddons[] names) declared in one config.cpp.

    Vanilla configs use the same shape, e.g. P:\\DZ\\AI\\config.cpp:1-11
    (class CfgPatches > class DZ_AI > requiredAddons[] = {"DZ_Data"}).
    """
    text = h.strip_cpp_comments(text)
    required: list[str] = []
    # `+=` appends to the array in config syntax. No vanilla config.cpp under
    # P:\DZ\ uses it (a grep finds none), but a mod's may, and the names it
    # adds are required just the same.
    for block in re.findall(r"requiredAddons\s*\[\]\s*\+?=\s*\{([^}]*)\}", text):
        required += re.findall(r'"([^"]+)"', block)
    # Walk class and brace tokens with string literals blanked, so a brace
    # inside a value cannot shift the depth. Array braces push a None entry.
    stack: list[str | None] = []
    patches: set[str] = set()
    for m in _CLASS_OR_BRACE.finditer(re.sub(r'"[^"\n]*"', '""', text)):
        token = m.group(0)
        if token == "{":
            stack.append(None)
        elif token == "}":
            if stack:
                stack.pop()
        elif token.endswith("{"):
            if len(stack) == 1 and (stack[0] or "").lower() == "cfgpatches":
                patches.add(m.group(1))
            stack.append(m.group(1))
    return patches, required


def workspace_patches(mod_dir: Path) -> tuple[set[str], list[str]] | None:
    """CfgPatches names and requiredAddons of a source mod under workspace/, or None.

    None means unknown: no such folder, no config.cpp in it, or a prebuilt
    bundle (Addons/*.pbo) whose PBOs may provide their own requirements, the
    same exception /dayz-gate ingame makes. Every config.cpp in the mod is
    read, not only the root one, skipping .git, Addons and Keys.
    """
    if not mod_dir.is_dir():
        return None
    addons = mod_dir / "Addons"
    if addons.is_dir() and any(addons.glob("*.pbo")):
        return None
    configs = [
        p for p in sorted(mod_dir.rglob("config.cpp"))
        if not any(part.lower() in _SKIP_DIRS for part in p.relative_to(mod_dir).parts[:-1])
    ]
    if not configs:
        return None
    patches: set[str] = set()
    required: list[str] = []
    for cfg in configs:
        found, needs = config_patches(cfg.read_text(encoding="utf-8", errors="replace"))
        patches |= found
        required += [n for n in needs if n not in required]
    return patches, required


def missing_dependencies(
    modnames: list[str], server_only: list[str], project_dir: Path
) -> dict[str, list[str]]:
    """Per mod: non-vanilla requiredAddons that no mod loaded before it provides.

    Vanilla patches start with DZ_ and are always loaded. A shared mod can only
    rely on shared mods named before it (clients never load server-only mods);
    a server-only mod can rely on every shared mod and the server-only mods
    before it. A mod listed earlier whose CfgPatches cannot be read (a built
    mod such as @CF with no workspace/ source) may provide anything, so its
    presence satisfies the check, as --deps does for /dayz-gate ingame.
    Names are compared case-insensitively.
    """
    order = [(name, modnames[:i]) for i, name in enumerate(modnames)]
    order += [(name, modnames + server_only[:i]) for i, name in enumerate(server_only)]
    workspace = project_dir / "workspace"
    problems: dict[str, list[str]] = {}
    for name, before in order:
        facts = workspace_patches(workspace / name)
        if facts is None:
            continue
        provided = {p.lower() for p in facts[0]}
        unknown_provider = False
        for dep in before:
            dep_facts = workspace_patches(workspace / dep)
            if dep_facts is None:
                unknown_provider = True
                break
            provided |= {p.lower() for p in dep_facts[0]}
        if unknown_provider:
            continue
        missing = [r for r in facts[1] if not r.upper().startswith("DZ_") and r.lower() not in provided]
        if missing:
            problems[name] = missing
    return problems


def gate_on_dependencies(modnames: list[str], server_only: list[str], project_dir: Path) -> None:
    """Refuse a launch in which a mod's non-vanilla requiredAddons are not loaded first."""
    problems = missing_dependencies(modnames, server_only, project_dir)
    if not problems:
        return
    lines = [
        f"          - {name} requires {', '.join(needs)}" for name, needs in problems.items()
    ]
    first = next(iter(problems))
    sys.exit(
        f"{FAIL} Required addons are not provided by any mod loaded before the mod that needs them:\n"
        + "\n".join(lines) + "\n"
        "       Name the @mods under P:\\Mods\\ that ship them before the mod, in load order,\n"
        f"       for example: /dayz-launch-test CF {first}. Without them the mod fails to load in game."
    )


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
    # errors="replace": a cfg saved in ANSI with a non-ASCII hostname or password
    # still parses; only the ASCII template and allowFilePatching lines are read.
    cfg = cfg_path.read_text(encoding="utf-8", errors="replace") if cfg_path.is_file() else None
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
    server_mod_arg: str = "",
) -> list[str]:
    """Build the diagnostic server launch command.

    Uses DayZDiag_x64.exe with `-server` so client and server run the same
    diag binary; the retail client DayZ_x64.exe is the one that blocks
    `-filePatching` past the loading screen.

    Server-only mods go on `-serverMod=`, not `-mod=`: mods on `-mod=` are
    advertised to connecting clients.
    """
    cmd = [
        str(diag_exe),
        "-server",
        f"-config={cfg_path}",
        f"-profiles={profile_dir}",
        f"-mission={mission_path}",
        f"-mod={mod_arg}",
    ]
    if server_mod_arg:
        cmd.append(f"-serverMod={server_mod_arg}")
    cmd += ["-filePatching", f"-port={port}"]
    return cmd


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


def wait_for_server_port(
    port: int, server_proc: subprocess.Popen, timeout_s: int = SERVER_BIND_TIMEOUT_S
) -> bool:
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

    Ctrl+C during the wait kills the server it was waiting on and exits 130,
    so no detached server is left holding the port for the next launch.
    """
    print(f"        Waiting up to {timeout_s}s for server to bind UDP port {port}...")
    sys.stdout.flush()
    deadline = time.time() + timeout_s
    last_dot = time.time()
    try:
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
    except KeyboardInterrupt:
        if server_proc.poll() is None:
            server_proc.kill()
        print(f"\n{FAIL} Interrupted while waiting for the server; killed it (PID {server_proc.pid}).")
        sys.exit(130)
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


def port(value: str) -> int:
    """argparse type for --port: a whole number from 1 to 65535."""
    n = int(value)
    if not 1 <= n <= 65535:
        raise argparse.ArgumentTypeError("port must be 1-65535")
    return n


_PATH_CHARS = '/\\:*?"<>|'


def mod_name(value: str) -> str:
    """argparse type for a mod name: the folder after @ under P:\\Mods\\.

    A leading @ is dropped, so CF and @CF name the same mod.
    """
    name = value[1:] if value.startswith("@") else value
    if name in ("", ".", "..") or any(c in name for c in _PATH_CHARS):
        raise argparse.ArgumentTypeError(
            f"'{value}' is not a mod name: use the folder name after @ under P:\\Mods\\ "
            "(no path separators, drive letters or '..')"
        )
    return name


def instance_name(value: str) -> str:
    """argparse type for --server: one folder name directly under .server/."""
    if value in ("", ".", "..") or any(c in value for c in _PATH_CHARS):
        raise argparse.ArgumentTypeError(
            f"'{value}' is not an instance name: use a single folder name under .server/ "
            "(no path separators, drive letters or '..')"
        )
    if value.startswith("!"):
        raise argparse.ArgumentTypeError(
            f"'{value}' is not an instance: names starting with '!' are shared .server folders "
            "such as !ClientDiagLogs"
        )
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Launch local DayZ server + client with one or more built mods."
    )
    parser.add_argument(
        "modnames", nargs="+", type=mod_name,
        help="Mod names loaded on both client and server, dependencies first (PBO must exist).",
    )
    # One name per --server-only flag. With nargs="+" it swallowed every name
    # after it, so `CF --server-only Srv MyMod` silently left MyMod off the client.
    parser.add_argument(
        "--server-only",
        action="append",
        default=[],
        type=mod_name,
        metavar="MODNAME",
        help=(
            "A mod loaded on the server only, never the client (PBO must exist). "
            "Repeat the flag for each one. For server-side mods that exit on purpose "
            "when loaded client-side."
        ),
    )
    parser.add_argument(
        "--server",
        default=DEFAULT_INSTANCE,
        type=instance_name,
        help=(
            f"Server instance to launch on (default: {DEFAULT_INSTANCE}). "
            "Must have been added via /dayz-add-server."
        ),
    )
    parser.add_argument("--port", type=port, default=2302, help="Server port (default: 2302).")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resolved commands without launching anything.",
    )
    args, extra = parser.parse_known_args()
    # argparse does not add a name that follows an option to the shared mods;
    # refuse it rather than guess whether it was meant shared or server-only.
    if extra:
        parser.error(
            f"unexpected arguments: {' '.join(extra)}. Put every shared mod name first, "
            "then the options, and give --server-only once per server-only mod, "
            "for example: CF MyMod --server-only Srv1 --server-only Srv2"
        )
    # Windows folder names ignore case, so CF and cf are the same @CF folder.
    # A mod on -mod= is advertised to clients, so one named both ways would
    # break the reason --server-only exists; one named twice lands twice.
    shared = {name.casefold() for name in args.modnames}
    both = [name for name in args.server_only if name.casefold() in shared]
    if both:
        parser.error(f"mod named both as shared and --server-only: {', '.join(both)}")
    seen: set[str] = set()
    dupes = []
    for name in args.modnames + args.server_only:
        if name.casefold() in seen:
            dupes.append(name)
        seen.add(name.casefold())
    if dupes:
        parser.error(f"mod named more than once: {', '.join(dupes)}")

    project_dir = h.resolve_project_dir()
    h.gate_on_preflight()
    print()
    print(f"{OK} Project: {project_dir}")
    gate_on_old_layout(project_dir)
    verify_built_mods(args.modnames + args.server_only)
    gate_on_dependencies(args.modnames, args.server_only, project_dir)
    diag_exe = resolve_diag_client()
    cfg_path, server_profile_dir, mission_path, client_profile_dir = verify_instance_environment(
        args.server, project_dir, dry_run=args.dry_run
    )

    display = read_client_display_prefs(project_dir, create=not args.dry_run)

    # Absolute mod paths so the engine resolves -mod=<arg> correctly regardless
    # of the working directory the subprocess inherits. Server-only mods go on
    # -serverMod= and stay off the client: some call RequestExit when they find
    # themselves client-side.
    client_mod_arg = ";".join(str(MODS_ROOT / f"@{name}") for name in args.modnames)
    server_mod_arg = ";".join(str(MODS_ROOT / f"@{name}") for name in args.server_only)
    server_cmd = build_server_cmd(
        diag_exe, client_mod_arg, args.port, cfg_path, server_profile_dir, mission_path,
        server_mod_arg=server_mod_arg,
    )
    client_cmd = build_client_cmd(diag_exe, client_mod_arg, args.port, client_profile_dir, display)

    # Printed with list2cmdline, the same quoting Popen applies on Windows, so a
    # path with spaces (Program Files, a project under 'DayZ n Chill') pastes as is.
    if args.dry_run:
        print()
        print(f"[DRY-RUN] Server cmd: {subprocess.list2cmdline(server_cmd)}")
        print(f"[DRY-RUN] Client cmd: {subprocess.list2cmdline(client_cmd)}")
        return 0

    # A server already on this port would make the new one fail to bind, and
    # wait_for_server_port would mistake the old server for the new one.
    h.gate_on_free_port(args.port)
    h.gate_on_steam()

    print()
    print(f"[Launch] Server: {subprocess.list2cmdline(server_cmd)}")
    sys.stdout.flush()
    # Detached (shared DETACH_FLAGS) so closing or killing the agent's shell
    # does not take the server and client down with it.
    try:
        server_proc = subprocess.Popen(server_cmd, close_fds=True, creationflags=h.DETACH_FLAGS)
    except OSError as err:
        print(f"{FAIL} Failed to spawn DayZDiag_x64.exe: {err}")
        return 1
    print(f"{OK} Server PID: {server_proc.pid}")
    sys.stdout.flush()
    if not wait_for_server_port(args.port, server_proc, timeout_s=SERVER_BIND_TIMEOUT_S):
        if server_proc.poll() is None:
            server_proc.kill()
            print(f"{FAIL} Server did not bind to port {args.port} within {SERVER_BIND_TIMEOUT_S}s; killed it.")
        print(f"       Check the server RPT in {server_profile_dir}\\ for errors.")
        return 1

    print()
    print(f"[Launch] Client: {subprocess.list2cmdline(client_cmd)}")
    sys.stdout.flush()
    try:
        client_proc = subprocess.Popen(client_cmd, close_fds=True, creationflags=h.DETACH_FLAGS)
    except OSError as err:
        # Don't leave a server running with no client to use it.
        server_proc.kill()
        print(f"{FAIL} Failed to spawn DayZDiag_x64.exe: {err}")
        return 1
    print(f"{OK} Client PID: {client_proc.pid}")

    print()
    print("Both running. Close the windows manually to stop.")
    print(f"  Server PID: {server_proc.pid}    Client PID: {client_proc.pid}")
    print(f"  Server logs: {server_profile_dir.relative_to(project_dir)}")
    print(f"  Client logs: {client_profile_dir.relative_to(project_dir)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
