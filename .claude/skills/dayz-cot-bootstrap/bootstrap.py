"""dayz-cot-bootstrap: One-shot CF + COT admin bootstrap on a DayZ test server.

Two-pass workflow:
  1. Launch server + client with CF + COT + user mods. Wait for COT to write the
     per-player files under <profiles>/PermissionsFramework/Players/<id>.json
     and <profiles>/PermissionsFramework/Permissions/<id>.txt.
  2. Stop the server and client this script started. For each triggered
     player, add "admin" to the JSON's Roles and flip ' 0' -> ' 2' in that
     player's Permissions/<id>.txt. Relaunch.

The grant is strictly per-player. Roles/everyone.txt (and the rest of
Roles/*.txt) is never modified: flipping everyone.txt would grant every
connecting player full admin perms, which is unsafe even on a solo test box.

COT does not write its perm files until a player has loaded in, which is why
this can't be done as a one-time pre-launch edit.

Reuses the launch helpers from dayz-launch-test/launch.py.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
import skill_helpers as h  # noqa: E402

P_DRIVE = Path("P:\\")
MODS_ROOT = P_DRIVE / "Mods"

CF_MOD = "CF"
COT_MOD = "Community-Online-Tools"

DEFAULT_INSTANCE = "chernarus"
DEFAULT_PORT = 2302
DEFAULT_TIMEOUT = 600  # 10 minutes
STOP_TIMEOUT_S = 30
# How long to wait after pass 1 for the stopped server to release its UDP port.
PORT_RELEASE_TIMEOUT_S = 30

OK, WARN, FAIL = h.OK, h.WARN, h.FAIL

_launch = h.load_module("dayz_launch_test_module", h.SKILLS_DIR / "dayz-launch-test" / "launch.py")
verify_built_mods = _launch.verify_built_mods
resolve_diag_client = _launch.resolve_diag_client
verify_instance_environment = _launch.verify_instance_environment
build_server_cmd = _launch.build_server_cmd
build_client_cmd = _launch.build_client_cmd
read_client_display_prefs = _launch.read_client_display_prefs
wait_for_server_port = _launch.wait_for_server_port
SERVER_BIND_TIMEOUT_S = _launch.SERVER_BIND_TIMEOUT_S


def verify_cf_cot_subscribed() -> None:
    """CF and COT are external Steam Workshop mods. They must be subscribed
    (present at P:\\Mods\\@<name>\\Addons\\) before this skill can run."""
    for name in (CF_MOD, COT_MOD):
        addons = MODS_ROOT / f"@{name}" / "Addons"
        if not addons.exists() or not any(addons.glob("*.pbo")):
            sys.exit(
                f"{FAIL} '@{name}' is not subscribed in Steam Workshop.\n"
                f"       Expected PBOs at {addons}\n"
                f"       Subscribe via Steam: https://steamcommunity.com/sharedfiles/?appid=221100"
            )


def dedup_with_cf_cot(user_mods: list[str]) -> list[str]:
    """Prepend CF + COT to the mod chain, dropping duplicates the user passed.
    CF must load before COT, and both before user mods that may depend on them."""
    seen: set[str] = set()
    out: list[str] = []
    for name in (CF_MOD, COT_MOD, *user_mods):
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


# How long pass 1 waits, with the server still running, for COT to write each
# player's Permissions/<id>.txt after the Players JSON appeared.
PERMS_WAIT_S = 15


def snapshot_player_files(players_dir: Path) -> dict[str, float]:
    """Return {player_id: mtime} for all existing Players/*.json files.

    COT touches these files when a player connects, so the wait loop watches
    for new files (key not in snapshot) or a newer mtime (a player reconnecting
    on a re-run)."""
    if not players_dir.exists():
        return {}
    return {p.stem: p.stat().st_mtime for p in players_dir.glob("*.json")}


def wait_for_cot_player(players_dir: Path, baseline: dict[str, float], timeout_s: int,
                        session: list[subprocess.Popen]) -> list[Path]:
    """Poll players_dir for new or touched JSON files. Returns the files that
    triggered. An empty list means the wait failed, already reported as [FAIL]:
    the timeout ran out, or the server or client (session = [server, client])
    exited first, which ends the wait at once."""
    print(f"        Waiting up to {timeout_s}s for COT to register your character...")
    print(f"        (watching {players_dir})")
    sys.stdout.flush()
    deadline = time.time() + timeout_s
    last_dot = time.time()
    while time.time() < deadline:
        if players_dir.exists():
            triggered = [
                p for p in players_dir.glob("*.json")
                if p.stem not in baseline or p.stat().st_mtime > baseline[p.stem]
            ]
            if triggered:
                print()
                for p in triggered:
                    print(f"{OK} Detected player file: {p.name}")
                return triggered
        for label, proc in zip(("server", "client"), session):
            code = proc.poll()
            if code is not None:
                print()
                print(f"{FAIL} The {label} exited (code {code}) before COT registered a player.")
                return []
        if time.time() - last_dot > 5:
            print(".", end="", flush=True)
            last_dot = time.time()
        time.sleep(2)
    print()
    print(f"{FAIL} Timed out after {timeout_s}s waiting for COT to register a player.")
    return []


def stop_session(procs: list[subprocess.Popen]) -> None:
    """Terminate only the processes this script started; other DayZDiag
    instances on the machine are left alone."""
    for proc in procs:
        if proc.poll() is not None:
            continue
        proc.kill()
        try:
            proc.wait(timeout=STOP_TIMEOUT_S)
            print(f"{OK} Stopped PID {proc.pid}")
        except subprocess.TimeoutExpired:
            print(f"{WARN} PID {proc.pid} did not exit within {STOP_TIMEOUT_S}s; close it manually.")


def backup_file(path: Path) -> Path:
    """Copy path to <name>.bak beside it before an in-place edit, replacing any
    older backup. The .bak suffix keeps it out of the *.json / *.txt globs."""
    bak = path.with_name(path.name + ".bak")
    shutil.copy2(path, bak)
    return bak


def grant_admin_role(player_json: Path) -> bool | None:
    """Add 'admin' to the player's Roles list. Returns True if the file was
    modified, False if it already had the role, None if it could not be read
    or parsed (the grant failed)."""
    try:
        data = json.loads(player_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"{FAIL} Could not parse {player_json.name}: {e}")
        return None
    roles = data.get("Roles")
    if not isinstance(roles, list):
        roles = []
    if "admin" in roles:
        print(f"        {player_json.stem}: already admin (no change)")
        return False
    roles.append("admin")
    data["Roles"] = roles
    backup_file(player_json)
    # Match COT's own formatting (4-space indent, trailing newline).
    player_json.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")
    print(f"{OK} Granted admin to {player_json.stem}")
    return True


def flip_zeros_to_twos(perms_file: Path) -> int:
    """Replace every line ending in ' 0' with ' 2' in perms_file. Returns the
    number of lines changed. Keeps the space and line endings. Idempotent."""
    text = perms_file.read_text(encoding="utf-8")
    new_text, n = re.subn(r" 0(\r?\n|$)", r" 2\1", text)
    if n:
        backup_file(perms_file)
        perms_file.write_text(new_text, encoding="utf-8")
    return n


def wait_for_personal_perms(perms_file: Path, timeout_s: int) -> bool:
    """COT writes Permissions/<id>.txt around the same time as Players/<id>.json
    but not always simultaneously. Block briefly so we don't edit a file that
    hasn't been created yet."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if perms_file.exists() and perms_file.stat().st_size > 0:
            return True
        time.sleep(0.5)
    return False


def perms_file_for(profile_dir: Path, player_json: Path) -> Path:
    return profile_dir / "PermissionsFramework" / "Permissions" / f"{player_json.stem}.txt"


def wait_for_perms_files(profile_dir: Path, triggered: list[Path], timeout_s: int = PERMS_WAIT_S) -> None:
    """Wait for each triggered player's Permissions/<id>.txt while the pass-1
    server is still running: the server writes that file, so once it is stopped
    a file that came slightly after the JSON can never appear. A file still
    missing afterwards is reported by edit_permissions."""
    print("        Waiting for COT to write the personal permission file(s)...")
    sys.stdout.flush()
    for json_path in triggered:
        wait_for_personal_perms(perms_file_for(profile_dir, json_path), timeout_s)


def edit_permissions(profile_dir: Path, triggered: list[Path]) -> bool:
    """Per-player grant only. For each triggered player JSON, add 'admin' to
    its Roles[], then flip ' 0' -> ' 2' in the matching Permissions/<id>.txt.
    Roles/*.txt (including everyone.txt) is intentionally not touched.

    Returns True only when every player got both edits (or already had them)."""
    print()
    print("[Edit] Applying COT admin permissions (per-player only)...")
    ok = True
    for json_path in triggered:
        if grant_admin_role(json_path) is None:
            ok = False
        perms_file = perms_file_for(profile_dir, json_path)
        # wait_for_perms_files already waited while the server ran; the server
        # is stopped now, so only check that the file is there.
        if not (perms_file.exists() and perms_file.stat().st_size > 0):
            print(f"{FAIL} Personal perms file did not appear at {perms_file}")
            ok = False
            continue
        n = flip_zeros_to_twos(perms_file)
        if n > 0:
            print(f"{OK} {perms_file.name}: flipped {n} line(s) from 0 -> 2")
        else:
            print(f"        {perms_file.name}: no 0 entries (already permissive or empty)")
    return ok


def wait_for_port_release(port: int, timeout_s: int = PORT_RELEASE_TIMEOUT_S) -> bool:
    """Poll until UDP port is free again (a killed server can hold it for a few
    seconds). True once it is free, False if it is still taken at the deadline."""
    deadline = time.time() + timeout_s
    while True:
        if h.udp_port_free(port):
            return True
        if time.time() >= deadline:
            return False
        time.sleep(1)


def admin_players(players_dir: Path) -> list[str]:
    """Ids of Players/*.json files whose Roles already include 'admin'."""
    out = []
    for p in (sorted(players_dir.glob("*.json")) if players_dir.exists() else []):
        try:
            roles = json.loads(p.read_text(encoding="utf-8")).get("Roles")
        except (OSError, json.JSONDecodeError, AttributeError):
            continue
        if isinstance(roles, list) and "admin" in roles:
            out.append(p.stem)
    return out


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
) -> list[subprocess.Popen]:
    """Check the port is free, spawn server, wait for its port, then spawn the
    client. Returns both handles. Mirrors the /dayz-launch-test contract."""
    print(f"[{label}] Launching server + client...")
    h.gate_on_free_port(port)
    server_cmd = build_server_cmd(diag_exe, mod_arg, port, cfg_path, profile_dir, mission_path)
    client_cmd = build_client_cmd(diag_exe, mod_arg, port, client_diag_dir, display)

    game_dir = diag_exe.parent
    print(f"[Launch] Server: {' '.join(server_cmd)}")
    sys.stdout.flush()
    server_proc = subprocess.Popen(server_cmd, cwd=str(game_dir))
    print(f"{OK} Server PID: {server_proc.pid}")
    sys.stdout.flush()
    if not wait_for_server_port(port, server_proc, timeout_s=SERVER_BIND_TIMEOUT_S):
        stop_session([server_proc])
        sys.exit(f"{FAIL} Server did not bind UDP port {port} within {SERVER_BIND_TIMEOUT_S}s.")

    print()
    print(f"[Launch] Client: {' '.join(client_cmd)}")
    sys.stdout.flush()
    client_proc = subprocess.Popen(client_cmd, cwd=str(game_dir))
    print(f"{OK} Client PID: {client_proc.pid}")
    return [server_proc, client_proc]


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
    parser.add_argument(
        "--skip-pass1", action="store_true",
        help="Skip pass 1 and the edit, and go straight to the relaunch. For a rerun after "
             "pass 2 could not start; refuses unless a Players JSON already has the admin role.",
    )
    args = parser.parse_args()

    h.gate_on_preflight()
    print()
    project_dir = h.resolve_project_dir()
    print(f"{OK} Project: {project_dir}")

    verify_cf_cot_subscribed()
    print(f"{OK} @{CF_MOD} subscribed")
    print(f"{OK} @{COT_MOD} subscribed")

    full_mods = dedup_with_cf_cot(args.modnames)
    print(f"{OK} Mod chain: {' -> '.join(full_mods)}")
    verify_built_mods(full_mods)

    diag_exe = resolve_diag_client()
    cfg_path, profile_dir, mission_path, client_diag_dir = verify_instance_environment(
        args.server, project_dir
    )
    display = read_client_display_prefs(project_dir)

    mod_arg = ";".join(str(MODS_ROOT / f"@{name}") for name in full_mods)
    players_dir = profile_dir / "PermissionsFramework" / "Players"

    if args.skip_pass1:
        admins = admin_players(players_dir)
        if not admins:
            print(f"{FAIL} --skip-pass1: no Players JSON in {players_dir} has the admin role yet.")
            print("       Run without --skip-pass1 so pass 1 can create and edit the files.")
            return 1
        print(f"{OK} --skip-pass1: admin already granted to {', '.join(admins)}; skipping pass 1 and the edit.")
        return run_pass2(args, diag_exe, mod_arg, cfg_path, profile_dir, mission_path, client_diag_dir, display)

    # === Pass 1: launch and wait for COT to register the player ===
    print()
    print("[Pass 1/2] Booting so COT can generate permission files for your character.")
    baseline = snapshot_player_files(players_dir)
    if baseline:
        print(f"        ({len(baseline)} existing player file(s) - watching for new ones or mtime change)")
    session = launch_pair(
        diag_exe, mod_arg, args.port, cfg_path, profile_dir, mission_path,
        client_diag_dir, display, "Pass 1",
    )

    triggered = wait_for_cot_player(players_dir, baseline, args.timeout, session)
    if not triggered:
        print(f"       Check script.log and the server RPT in {profile_dir}\\,")
        print(f"       and the client's script.log in {client_diag_dir}\\.")
        print("       Stopping the pass-1 server and client before exiting...")
        stop_session(session)
        return 1

    wait_for_perms_files(profile_dir, triggered)

    # === Stop, edit, relaunch ===
    print()
    print("[Stop] Stopping the pass-1 server and client before editing perm files...")
    stop_session(session)
    # Give Windows a moment to release file handles on the JSON we're about to rewrite.
    time.sleep(2)

    if not edit_permissions(profile_dir, triggered):
        print(f"{FAIL} The admin grant did not complete, so pass 2 was skipped.")
        print(f"       Fix the files under {profile_dir / 'PermissionsFramework'} and rerun this skill.")
        return 1

    print()
    print(f"        Waiting up to {PORT_RELEASE_TIMEOUT_S}s for UDP port {args.port} to be released...")
    sys.stdout.flush()
    if not wait_for_port_release(args.port):
        print(f"{FAIL} UDP port {args.port} is still in use {PORT_RELEASE_TIMEOUT_S}s after pass 1 stopped.")
        print("       The permission edits are saved. Run /dayz-stop-test, then rerun this skill")
        print("       with --skip-pass1 to go straight to the relaunch.")
        return 1
    return run_pass2(args, diag_exe, mod_arg, cfg_path, profile_dir, mission_path, client_diag_dir, display)


def run_pass2(args, diag_exe, mod_arg, cfg_path, profile_dir, mission_path, client_diag_dir, display) -> int:
    """Relaunch server + client with the admin grant in place and print the summary."""
    print()
    print("[Pass 2/2] Relaunching with admin permissions applied.")
    server_proc, client_proc = launch_pair(
        diag_exe, mod_arg, args.port, cfg_path, profile_dir, mission_path,
        client_diag_dir, display, "Pass 2",
    )

    print()
    print(f"You are now COT admin on '{args.server}'. In game, press Y to open the COT menu (End turns COT on or off; both can be rebound in Controls).")
    print(f"  Server PID: {server_proc.pid}    Client PID: {client_proc.pid}")
    print(f"  Server logs: {profile_dir}")
    print(f"  Client logs: {client_diag_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
