"""dayz-add-server: Set up a DayZ test server instance under .server/<instance>/.

Each instance is a self-contained test environment: mission copy, serverDZ.cfg,
server profile dir, client profile dir. Decoupled from map name so the user can
run multiple variants of the same map (chernarus, chernarus-hardcore, etc.).

This is the setup half of the local-test loop. /dayz-launch-test is the run
half and refuses to run for an instance that hasn't been added yet.

Refuses to run if the legacy workspace/_server/ folder still exists. Run
/dayz-migrate-server first.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

# REPO_ROOT = where this skill ships from (plugin or template clone).
# Project dir (where .server/ lives) is resolved at runtime from the
# /dayz-init project cache; see resolve_project_dir().
REPO_ROOT = Path(__file__).resolve().parents[3]
PREFLIGHT_DIR = REPO_ROOT / ".claude" / "skills" / "dayz-preflight"
PREFLIGHT = PREFLIGHT_DIR / "preflight.py"
DAYZ_INIT_DIR = REPO_ROOT / ".claude" / "skills" / "dayz-init"

KNOWN_MAPS: dict[str, str] = {
    "chernarus": "dayzOffline.chernarusplus",
    "livonia": "dayzOffline.enoch",
    "sakhal": "dayzOffline.sakhal",
}

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
find_dayz_server = _preflight.find_dayz_server

# Reuse the project-root cache reader from /dayz-init so add-server follows the same source of truth.
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
            "       Run: python .claude/skills/dayz-migrate-server/migrate.py"
        )


def resolve_map_name(instance: str, map_arg: str | None) -> str:
    """Pick the map alias for this instance.

    If --map was given, use it. Otherwise, if the instance name is itself a
    known map alias, use it as the map. Otherwise fail and force the user to
    be explicit, since we have no way to guess the mission template from a
    free-form name like 'my-test-server'.
    """
    if map_arg:
        return map_arg
    if instance in KNOWN_MAPS:
        return instance
    sys.exit(
        f"{FAIL} '{instance}' is not a known map alias and --map was not given.\n"
        f"       Specify --map (one of: {', '.join(KNOWN_MAPS)}, or a custom\n"
        "       mission folder name like dayzOffline.namalsk)."
    )


def resolve_mission_template(map_name: str) -> str:
    return KNOWN_MAPS.get(map_name, map_name)


def ensure_mission(template: str, mission_dir: Path, refresh: bool, project_dir: Path) -> None:
    """Ensure <instance>/mission/ exists, copied from DayZ Server install.

    Folder is named `mission/` regardless of template (the launcher pins the
    path explicitly via -mission=<abspath>, so the engine doesn't care).
    """
    already_present = mission_dir.exists() and any(mission_dir.iterdir())

    if already_present and not refresh:
        print(f"{OK} Mission already present: {mission_dir.relative_to(project_dir)}")
        return

    server_root = find_dayz_server()
    if server_root is None:
        sys.exit(
            f"{FAIL} DayZ Server install not found.\n"
            "       Required to copy mission templates. Install via Steam (Tools section,\n"
            "       free, appid 223350), or manually populate\n"
            f"       {mission_dir.relative_to(project_dir)} with mission content."
        )

    src = server_root / "mpmissions" / template
    if not src.exists():
        available = []
        mp = server_root / "mpmissions"
        if mp.exists():
            available = sorted(p.name for p in mp.iterdir() if p.is_dir())
        avail_str = "\n".join(f"          {n}" for n in available) or "          (none)"
        sys.exit(
            f"{FAIL} Mission template '{template}' not found in DayZ Server install at\n"
            f"       {src}\n"
            f"       Available templates in DayZ Server's mpmissions/:\n{avail_str}"
        )

    mission_dir.parent.mkdir(parents=True, exist_ok=True)
    if mission_dir.exists():
        shutil.rmtree(mission_dir)
        action = "Refreshed"
    else:
        action = "Copied"
    shutil.copytree(src, mission_dir)
    print(f"{OK} {action} {mission_dir.relative_to(project_dir)}  (from DayZ Server install)")


def setup_instance_dir(instance: str, template: str, project_dir: Path) -> None:
    """Ensure .server/<instance>/ has serverDZ.cfg + server-profiles/ + client-profiles/
    + profiles/ + a junction named after the mission template pointing at mission/.

    The mission-template junction is REQUIRED for the client-spawn handshake. The
    engine resolves the template name (e.g. dayzOffline.chernarusplus) relative to
    the instance dir during connect; without it the world loads but the player
    never spawns.
    """
    server_root = project_dir / ".server"
    inst_dir = server_root / instance
    server_profiles = inst_dir / "server-profiles"
    client_profiles = inst_dir / "client-profiles"
    profiles = inst_dir / "profiles"  # BattlEye/extended-controls dir
    server_profiles.mkdir(parents=True, exist_ok=True)
    client_profiles.mkdir(parents=True, exist_ok=True)
    profiles.mkdir(parents=True, exist_ok=True)
    # Top-level shared client diag logs (matches PonyWalkman convention)
    (server_root / "!ClientDiagLogs").mkdir(parents=True, exist_ok=True)

    cfg_path = inst_dir / "serverDZ.cfg"
    if not cfg_path.exists():
        cfg_path.write_text(default_server_cfg(instance, template), encoding="utf-8")
        print(f"{OK} Wrote default {cfg_path.relative_to(project_dir)}")
    else:
        cfg = cfg_path.read_text(encoding="utf-8")
        if "allowFilePatching" not in cfg:
            cfg = cfg.rstrip() + "\nallowFilePatching = 1;\n"
            cfg_path.write_text(cfg, encoding="utf-8")
            print(f"{OK} Appended allowFilePatching = 1 to {cfg_path.relative_to(project_dir)}")
        else:
            print(f"{OK} {cfg_path.relative_to(project_dir)} unchanged (already configured)")

    # Mission template junction: dayzOffline.<map> -> mission/. The engine looks
    # for the template by name during the connect handshake; missing this causes
    # client spawn to hang indefinitely (world loads, player entity created, but
    # the player never renders into the world).
    mission_dir = inst_dir / "mission"
    template_junction = inst_dir / template
    if mission_dir.exists() and not template_junction.exists():
        import subprocess
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(template_junction), str(mission_dir)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"{OK} Junction {template_junction.name}/ -> mission/ (template handshake)")
        else:
            print(f"{FAIL} Could not create template junction: {result.stderr.strip()}")

    print(f"{OK} {server_profiles.relative_to(project_dir)} ready")
    print(f"{OK} {client_profiles.relative_to(project_dir)} ready")


def default_server_cfg(instance: str, template: str) -> str:
    # Six-char shardId required by engine; truncate/pad instance name.
    shard = (instance + "shard")[:6].lower()
    return dedent(
        f"""\
        hostname = "Local Test ({instance})";   // Server name
        password = "";                          // Password to connect to the server
        passwordAdmin = "";                     // Password to become a server admin

        description = "Agentic-Z local diag test instance";   // Description shown in browser

        enableWhitelist = 0;                    // Enable/disable whitelist (value 0-1)

        maxPlayers = 4;                         // Maximum amount of players (local test)

        verifySignatures = 0;                   // Verifies .pbos against .bisign files (only 2 is supported)
        forceSameBuild = 0;                     // 0 for diag-mode mod testing (client/server diag may mismatch)
        allowFilePatching = 1;                  // Required; clients launch with -filePatching

        disableVoN = 0;                         // Enable/disable voice over network (value 0-1)
        vonCodecQuality = 20;                   // VoN codec quality (values 0-30)

        shardId = "{shard}";   // Six alphanumeric chars for the private shard

        disable3rdPerson = 0;                   // Toggles the 3rd person view (value 0-1)
        disableCrosshair = 0;                   // Toggles the cross-hair (value 0-1)

        disablePersonalLight = 1;               // Disables personal light for all connected clients
        lightingConfig = 0;                     // 0 for brighter night, 1 for darker night

        serverTime = "SystemTime";              // Initial in-game time. "SystemTime" or "YYYY/MM/DD/HH/MM"
        serverTimeAcceleration = 12;            // Day time multiplier (0-24)
        serverNightTimeAcceleration = 1;        // Night time multiplier (0.1-64), stacks with serverTimeAcceleration
        serverTimePersistent = 0;               // Persist server time across restarts (value 0-1)

        guaranteedUpdates = 1;                  // Communication protocol; use only 1

        loginQueueConcurrentPlayers = 5;        // Concurrent players processed during login
        loginQueueMaxPlayers = 500;             // Max players in login queue

        instanceId = 1;                         // Server instance id (storage folder selector)

        storageAutoFix = 1;                     // Replace corrupted persistence files with empty ones (value 0-1)

        persistent = 0;                         // Persistent world state (0 for fresh test sessions)

        class Missions
        {{
            class DayZ
            {{
                template = "{template}";   // Mission to load on server startup
            }};
        }};
        """
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Set up a DayZ test server instance under .server/<instance>/.")
    parser.add_argument(
        "instance",
        help=(
            "Free-form instance name (becomes .server/<instance>/). If the name "
            f"matches a known map alias ({', '.join(KNOWN_MAPS)}), --map defaults "
            "to that map; otherwise --map is required."
        ),
    )
    parser.add_argument(
        "--map",
        dest="map_arg",
        default=None,
        help=(
            f"Map alias (one of: {', '.join(KNOWN_MAPS)}) or full mission template "
            "folder name (e.g. dayzOffline.namalsk). Defaults to <instance> when "
            "<instance> is itself a known alias."
        ),
    )
    parser.add_argument(
        "--refresh-mission",
        action="store_true",
        help="Re-copy the mission folder from DayZ Server install, overwriting local edits.",
    )
    args = parser.parse_args()

    project_dir = resolve_project_dir()
    gate_on_preflight()
    print()
    print(f"{OK} Project: {project_dir}")
    gate_on_old_layout(project_dir)

    map_name = resolve_map_name(args.instance, args.map_arg)
    template = resolve_mission_template(map_name)
    print(f"{OK} Instance: {args.instance}  (map: {map_name}, mission: {template})")

    server_root = project_dir / ".server"
    inst_dir = server_root / args.instance
    mission_dir = inst_dir / "mission"

    ensure_mission(template, mission_dir, refresh=args.refresh_mission, project_dir=project_dir)
    setup_instance_dir(args.instance, template, project_dir)

    print()
    print(f"Instance '{args.instance}' is ready. Next:")
    print(f"  /dayz-build-pbo <ModName>")
    print(f"  /dayz-launch-test <ModName> --server {args.instance}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
