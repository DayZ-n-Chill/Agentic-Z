"""dayz-cot-bootstrap: One-shot CF + COT admin bootstrap on a DayZ test server.

Two-pass workflow:
  1. Launch server + client with CF + COT + user mods. Wait for COT to write the
     per-player JSON under <profiles>/PermissionsFramework/Players/*.json.
  2. Kill the session, add "admin" role to the player JSON, flip 0 -> 2 in every
     Roles/*.txt file. Relaunch.

COT does not write its perm files until a player has loaded in, which is why
this can't be done as a one-time pre-launch edit.

Reuses helpers from dayz-launch-test/launch.py and dayz-preflight/preflight.py.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PREFLIGHT = REPO_ROOT / ".claude" / "skills" / "dayz-preflight" / "preflight.py"
LAUNCH_TEST = REPO_ROOT / ".claude" / "skills" / "dayz-launch-test" / "launch.py"
P_DRIVE = Path("P:\\")
MODS_ROOT = P_DRIVE / "Mods"

CF_MOD = "CF"
COT_MOD = "Community-Online-Tools"
DIAG_IMAGE_NAME = "DayZDiag_x64.exe"

DEFAULT_INSTANCE = "chernarus"
DEFAULT_PORT = 2302
DEFAULT_TIMEOUT = 600  # 10 minutes

OK = "[OK]   "
WARN = "[WARN] "
FAIL = "[FAIL] "


def _load(path: Path, alias: str):
    spec = importlib.util.spec_from_file_location(alias, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module at {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_preflight = _load(PREFLIGHT, "dayz_preflight_module")
_launch = _load(LAUNCH_TEST, "dayz_launch_test_module")

find_dayz_diag = _preflight.find_dayz_diag
read_current_project = _preflight.read_current_project
verify_built_mods = _launch.verify_built_mods
resolve_diag_client = _launch.resolve_diag_client
verify_instance_environment = _launch.verify_instance_environment
build_server_cmd = _launch.build_server_cmd
build_client_cmd = _launch.build_client_cmd
read_client_display_prefs = _launch.read_client_display_prefs
wait_for_server_port = _launch.wait_for_server_port


def gate_on_preflight() -> None:
    if not PREFLIGHT.exists():
        sys.exit(f"{FAIL} dayz-preflight skill not found at {PREFLIGHT.relative_to(REPO_ROOT)}")
    result = subprocess.run([sys.executable, str(PREFLIGHT)])
    if result.returncode != 0:
        sys.exit(result.returncode)


def verify_cf_cot_subscribed() -> None:
    """CF and COT are external Steam Workshop mods. They must be subscribed
    (i.e. present at P:\\Mods\\@<name>\\Addons\\) before this skill can run."""
    for name in (CF_MOD, COT_MOD):
        addons = MODS_ROOT / f"@{name}" / "Addons"
        if not addons.exists() or not any(addons.glob("*.pbo")):
            sys.exit(
                f"{FAIL} '@{name}' is not subscribed in Steam Workshop.\n"
                f"       Expected PBOs at {addons}\n"
                f"       Subscribe via Steam: https://steamcommunity.com/sharedfiles/?appid=221100"
            )


def dedup_with_cf_cot(user_mods: list[str]) -> list[str]:
    """Prepend CF + COT to the mod chain, removing any duplicates the user
    passed. Order matters: CF must come before COT, and both must come before
    user mods that may depend on them."""
    seen: set[str] = set()
    out: list[str] = []
    for name in (CF_MOD, COT_MOD, *user_mods):
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def snapshot_player_files(players_dir: Path) -> dict[str, float]:
    """Return {player_id: mtime} for all existing Players/*.json files.

    COT touches these files when a player connects, so the wait loop watches
    for new files (key not in snapshot) OR mtime advancing (existing player
    reconnecting on a re-run)."""
    if not players_dir.exists():
        return {}
    return {p.stem: p.stat().st_mtime for p in players_dir.glob("*.json")}


def wait_for_cot_player(players_dir: Path, baseline: dict[str, float], timeout_s: int) -> list[Path]:
    """Poll players_dir for new or touched JSON files. Returns the list of
    paths that triggered. Empty list means timeout."""
    print(f"        Waiting up to {timeout_s}s for COT to register your character...")
    print(f"        (watching {players_dir})")
    sys.stdout.flush()
    deadline = time.time() + timeout_s
    last_dot = time.time()
    while time.time() < deadline:
        if players_dir.exists():
            triggered: list[Path] = []
            for p in players_dir.glob("*.json"):
                pid = p.stem
                mtime = p.stat().st_mtime
                if pid not in baseline or mtime > baseline[pid]:
                    triggered.append(p)
            if triggered:
                print()
                for p in triggered:
                    print(f"{OK} Detected player file: {p.name}")
                return triggered
        if time.time() - last_dot > 5:
            print(".", end="", flush=True)
            last_dot = time.time()
        time.sleep(2)
    print()
    return []


def kill_diag_processes() -> int:
    """taskkill all DayZDiag_x64.exe. Returns count killed (best effort)."""
    result = subprocess.run(
        ["taskkill", "/IM", DIAG_IMAGE_NAME, "/F"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        killed = sum(1 for line in result.stdout.splitlines() if line.startswith("SUCCESS:"))
        word = "process" if killed == 1 else "processes"
        print(f"{OK} Killed {killed} {DIAG_IMAGE_NAME} {word}.")
        return killed
    if "not found" in (result.stderr or "").lower():
        print(f"{OK} No {DIAG_IMAGE_NAME} processes were running.")
        return 0
    print(f"{WARN} taskkill returned rc={result.returncode}")
    if result.stdout.strip():
        print(result.stdout)
    if result.stderr.strip():
        print(result.stderr)
    return 0


def grant_admin_role(player_json: Path) -> bool:
    """Insert 'admin' into the player's Roles list. Returns True if the file
    was modified, False if already had it."""
    try:
        data = json.loads(player_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"{WARN} Could not parse {player_json.name}: {e} — skipping")
        return False
    roles = data.get("Roles")
    if not isinstance(roles, list):
        roles = []
    if "admin" in roles:
        print(f"        {player_json.stem}: already admin (no change)")
        return False
    roles.append("admin")
    data["Roles"] = roles
    # Match COT's own formatting (4-space indent, trailing newline).
    player_json.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")
    print(f"{OK} Granted admin to {player_json.stem}")
    return True


def flip_zeros_to_twos(role_file: Path) -> int:
    """Replace every line ending in ' 0' with ' 2' in role_file. Returns the
    number of lines changed. Idempotent."""
    text = role_file.read_text(encoding="utf-8")
    new_text, n = re.subn(r" 0(\r?\n|$)", r" 2\1", text)
    if n == 0:
        return 0
    role_file.write_text(new_text, encoding="utf-8")
    return n


def edit_permissions(profile_dir: Path, triggered: list[Path]) -> None:
    """Apply the two edits per SKILL.md:
       1. Add 'admin' role to each triggered player's JSON.
       2. Flip ' 0' -> ' 2' in every Roles/*.txt file."""
    print()
    print("[Edit] Applying COT admin permissions...")
    for p in triggered:
        grant_admin_role(p)

    roles_dir = profile_dir / "PermissionsFramework" / "Roles"
    if not roles_dir.exists():
        print(f"{WARN} Roles dir missing at {roles_dir} — skipping role flip")
        return

    for role_file in sorted(roles_dir.glob("*.txt")):
        n = flip_zeros_to_twos(role_file)
        if n > 0:
            print(f"{OK} {role_file.name}: flipped {n} line(s) from 0 -> 2")
        else:
            print(f"        {role_file.name}: no 0 entries (already permissive or empty)")


def launch_pair(
    diag_exe: Path,
    mod_arg: str,
    port: int,
    cfg_path: Path,
    profile_dir: Path,
    mission_path: Path,
    client_diag_dir: Path,
    display: dict,
    label: str,
) -> tuple[subprocess.Popen, subprocess.Popen]:
    """Spawn server + client, returning both Popen handles. Mirrors the
    /dayz-launch-test contract."""
    print(f"[{label}] Launching server + client...")
    server_cmd = build_server_cmd(diag_exe, mod_arg, port, cfg_path, profile_dir, mission_path)
    client_cmd = build_client_cmd(diag_exe, mod_arg, port, client_diag_dir, display)

    game_dir = diag_exe.parent
    print(f"[Launch] Server: {' '.join(server_cmd)}")
    sys.stdout.flush()
    server_proc = subprocess.Popen(server_cmd, cwd=str(game_dir))
    print(f"{OK} Server PID: {server_proc.pid}")
    sys.stdout.flush()
    if not wait_for_server_port(port, server_proc, timeout_s=180):
        sys.exit(f"{FAIL} Server did not bind UDP port {port} within 180s.")

    print()
    print(f"[Launch] Client: {' '.join(client_cmd)}")
    sys.stdout.flush()
    client_proc = subprocess.Popen(client_cmd, cwd=str(game_dir))
    print(f"{OK} Client PID: {client_proc.pid}")
    return server_proc, client_proc


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap COT admin on a DayZ test server (two-pass: launch, wait, edit perms, relaunch)."
    )
    parser.add_argument(
        "modnames", nargs="*",
        help="User mod names already built (PBOs at P:\\Mods\\@<name>\\Addons\\). "
             "CF and Community-Online-Tools are auto-prepended.",
    )
    parser.add_argument(
        "--server", default=DEFAULT_INSTANCE,
        help=f"Server instance (default: {DEFAULT_INSTANCE}). Must be added via /dayz-add-server.",
    )
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT,
        help=f"Server port (default: {DEFAULT_PORT}).",
    )
    parser.add_argument(
        "--timeout", type=int, default=DEFAULT_TIMEOUT,
        help=f"Seconds to wait for COT to register your character on pass 1 (default: {DEFAULT_TIMEOUT}).",
    )
    args = parser.parse_args()

    gate_on_preflight()
    print()
    project_dir = read_current_project()
    print(f"{OK} Project: {project_dir}")

    verify_cf_cot_subscribed()
    print(f"{OK} @{CF_MOD} subscribed")
    print(f"{OK} @{COT_MOD} subscribed")

    full_mods = dedup_with_cf_cot(args.modnames)
    print(f"{OK} Mod chain: {' -> '.join(full_mods)}")
    verify_built_mods(full_mods)

    diag_exe = resolve_diag_client()
    cfg_path, profile_dir, mission_path, client_diag_dir = verify_instance_environment(
        project_dir, args.server
    )
    display = read_client_display_prefs()

    mod_arg = ";".join(str(MODS_ROOT / f"@{name}") for name in full_mods)
    players_dir = profile_dir / "PermissionsFramework" / "Players"

    # === Pass 1: launch and wait for COT to register the player ===
    print()
    print("[Pass 1/2] Booting so COT can generate permission files for your character.")
    baseline = snapshot_player_files(players_dir)
    if baseline:
        print(f"        ({len(baseline)} existing player file(s) — watching for new ones or mtime change)")
    launch_pair(
        diag_exe, mod_arg, args.port, cfg_path, profile_dir, mission_path,
        client_diag_dir, display, "Pass 1",
    )

    triggered = wait_for_cot_player(players_dir, baseline, args.timeout)
    if not triggered:
        print(f"{FAIL} Timed out after {args.timeout}s waiting for COT to register a player.")
        print(f"       Check the server RPT in {profile_dir}\\ for errors.")
        print(f"       Killing diag processes before exiting...")
        kill_diag_processes()
        return 1

    # === Kill, edit, relaunch ===
    print()
    print("[Stop] Killing pass-1 session before editing perm files...")
    kill_diag_processes()
    # Give Windows a moment to release file handles on the JSON we're about to rewrite.
    time.sleep(2)

    edit_permissions(profile_dir, triggered)

    print()
    print("[Pass 2/2] Relaunching with admin permissions applied.")
    server_proc, client_proc = launch_pair(
        diag_exe, mod_arg, args.port, cfg_path, profile_dir, mission_path,
        client_diag_dir, display, "Pass 2",
    )

    print()
    print(f"You are now COT admin on '{args.server}'. Open the COT menu in-game (default keybind: BACKSPACE).")
    print(f"  Server PID: {server_proc.pid}    Client PID: {client_proc.pid}")
    print(f"  Server logs: {profile_dir}")
    print(f"  Client logs: {client_diag_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
