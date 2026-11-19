"""dayz-testbridge MCP server: drive a running DayZ Diag test session through the AZ_TestBridge mod.

Tools (all blocking work runs in worker threads, as in dayz-rag):

  list_commands      the allowlist: every bridge command, its peer, arguments, bounds and outputs
  session_start      storage-free instance copy, bridge mod packed, server and client launched, both peers ready
  session_status     processes alive, hellos, last sequence numbers, new crash logs
  session_restart    orderly server shutdown (world saved), then server and client again with the same token
  session_restart_client  end only the client and start it again into the running server
  session_stop       always safe to call: eject, kill only this session's processes, remove the mod
  command            send one allowlisted command to its peer and return the result
  mark               save log offsets under a label and print MARK <label> on both peers
  logs_since         script log and RPT lines since a mark, with bridge errors and optional triage
  screenshot         capture the client window (PrintWindow, never the mouse or focus) to a PNG

Every failure raises; FastMCP returns it to the client as an error result.
Facts and limits: skills/dayz-launch-test/references/test-bridge.md.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import allowlist  # noqa: E402
import session  # noqa: E402
import window_capture  # noqa: E402  (skills/_shared, put on the path by session)

NAME_RE = re.compile(r"^[A-Za-z0-9][\w.-]{0,63}$")
CONFIRM_S = 10.0  # how long get_in and get_out wait for the server to agree


def _project() -> Path:
    return session.h.resolve_project_dir()


def _running_state(project: Path) -> dict:
    state = session.load_state(project)
    if state is None:
        raise RuntimeError("no test bridge session is running; call session_start first")
    return state


# --- implementations (plain functions, tested without MCP) -------------------------------

def list_commands_impl() -> dict:
    out = {}
    for name, spec in allowlist.COMMANDS.items():
        args = {}
        for arg_name, arg in spec.args.items():
            info = {"type": arg.kind, "required": arg.required}
            if not arg.required:
                info["default"] = arg.default
            if arg.lo is not None:
                info["min"], info["max"] = arg.lo, arg.hi
            if arg.choices:
                info["choices"] = list(arg.choices)
            args[arg_name] = info
        out[name] = {"peer": spec.peer, "args": args, "outputs": list(spec.outputs), "doc": spec.doc}
    return {"commands": out, "positions": "[x, y_up, z] in engine order; y above 2000 is refused as a swapped triplet",
            "spawn_limit": allowlist.MAX_SPAWNS}


def session_start_impl(mods: list[str], deps: list[str], server: str, port: int,
                       rt: Optional[session.Runtime] = None, allow_exec: bool = False) -> dict:
    return session.start(_project(), mods, deps, server, port, rt=rt, allow_exec=allow_exec)


def session_restart_impl(keep_storage: bool, rt: Optional[session.Runtime] = None) -> dict:
    return session.restart(_project(), keep_storage, rt)


def session_restart_client_impl(rt: Optional[session.Runtime] = None) -> dict:
    return session.restart_client(_project(), rt)


def session_status_impl(rt: Optional[session.Runtime] = None) -> dict:
    return session.status(_project(), rt)


def session_stop_impl(rt: Optional[session.Runtime] = None) -> dict:
    return session.stop(_project(), rt)


def command_impl(cmd: str, args: Optional[dict], peer: Optional[str], rt: Optional[session.Runtime] = None) -> dict:
    """One allowlisted command. get_in and get_out also wait for the server to agree on the seat."""
    rt = rt or session.real_runtime()
    project = _project()
    state = _running_state(project)
    b = session.bridge_of(project, state, rt)
    try:
        result = b.call(cmd, args, peer)
        if cmd in ("get_in", "get_out") and result.get("ok"):
            result["server"] = _confirm_seat(b, rt, seated=cmd == "get_in")
    finally:
        session.remember(project, state, b)
    return result


def _confirm_seat(b, rt: session.Runtime, seated: bool) -> dict:
    """The server's own view of the player, polled until it agrees with the client or CONFIRM_S passes."""
    deadline = rt.clock() + CONFIRM_S
    while True:
        state = b.call("player_state")
        data = state.get("data") or {}
        agrees = bool(data.get("in_vehicle")) == seated
        if agrees or rt.clock() >= deadline or not state.get("ok"):
            return {"agrees": agrees, "in_vehicle": bool(data.get("in_vehicle")), "seat": data.get("seat"),
                    "error": state.get("error", "")}
        rt.sleep(0.5)


def mark_impl(label: str, rt: Optional[session.Runtime] = None) -> dict:
    allowlist.check_arg("mark", "label", allowlist.COMMANDS["mark"].args["label"], label)
    return session.mark(_project(), label, rt)


def logs_since_impl(mark: str, peers: Optional[list[str]], kinds: Optional[list[str]], regex: Optional[str],
                    triage: bool, limit: int = 500) -> dict:
    kinds_t = tuple(kinds) if kinds else session.logs.KINDS
    bad = set(kinds_t) - set(session.logs.KINDS)
    if bad:
        raise ValueError(f"kinds must be script and/or rpt, got {sorted(bad)}")
    if peers and set(peers) - {"server", "client"}:
        raise ValueError("peers must be server and/or client")
    if limit < 1:
        raise ValueError("limit must be 1 or more")
    if regex:
        re.compile(regex)
    out = session.logs_since(_project(), mark, peers, kinds_t, regex, triage)
    total = len(out["lines"])
    out["lines"] = out["lines"][-limit:]
    out["total"] = total
    return out


def screenshot_impl(name: str, crop: Optional[list[int]] = None, capture=None) -> dict:
    """Capture the client window to output/testbridge/<token>/<name>.png."""
    if not NAME_RE.match(name):
        raise ValueError("name must be letters, digits, '_', '.' or '-' with no spaces")
    if crop is not None and (len(crop) != 4 or any(not isinstance(v, int) or v < 0 for v in crop) or crop[2] == 0 or crop[3] == 0):
        raise ValueError("crop is [x, y, width, height] in whole pixels")
    project = _project()
    state = _running_state(project)
    pid = state["pids"].get("client")
    out = project / "output" / "testbridge" / state["token"] / f"{name}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    capture = capture or window_capture.capture_window
    try:
        size = capture(pid, out, tuple(crop) if crop else None)
    except window_capture.CaptureError as e:
        # A black or missing frame is a failed capture, not a verdict on the mod (screenshots-and-cameras.md).
        return {"ok": False, "all_black": "all black" in str(e), "error": str(e), "path": None}
    # A stale picture: the same bytes as the previous capture of this session, which a
    # live game window almost never gives twice (test-bridge.md, "Measured").
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    fresh = session.load_state(project) or state
    stale = digest == fresh.get("last_shot_sha")
    fresh["last_shot_sha"] = digest
    session.save_state(project, fresh)
    return {"ok": not stale, "all_black": False, "same_as_previous": stale, "path": str(out),
            "width": size[0], "height": size[1],
            **({"error": "stale: byte for byte the previous capture; wait and capture again"} if stale else {})}


# --- the MCP app -----------------------------------------------------------------------------

def build_app():
    """The FastMCP app. Raises ImportError when the mcp package is missing."""
    import anyio
    from mcp.server.fastmcp import FastMCP
    from mcp.types import ToolAnnotations

    mcp = FastMCP("dayz-testbridge")
    read_only = ToolAnnotations(readOnlyHint=True, openWorldHint=False)
    acts = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False)

    @mcp.tool(annotations=read_only)
    async def list_commands() -> dict:
        """Every command the bridge accepts: peer (server, client or both), arguments with types,
        defaults and bounds, and the outputs each returns. Read this before calling `command`."""
        return list_commands_impl()

    @mcp.tool(annotations=acts)
    async def session_start(mods: Optional[list[str]] = None, deps: Optional[list[str]] = None, server: str = "chernarus",
                            port: int = 2302, allow_exec: bool = False) -> dict:
        """Start a test session: copy .server/<server>/ to <server>-bridge without storage, pack the
        AZ_TestBridge mod, launch the DayZ Diag server and client with `deps` then `mods` (built PBOs
        under P:\\Mods\\; empty for vanilla), wait until both peers answer with the player loaded,
        and close the pause menu. Refuses while any DayZDiag_x64.exe this tool did not start runs.
        Takes up to about 5 minutes. Always call session_stop when done. allow_exec=true turns on the
        exec command (any Enforce Script) for this session only; every code string is logged."""
        return await anyio.to_thread.run_sync(lambda: session_start_impl(mods or [], deps or [], server, port, None, allow_exec))

    @mcp.tool(annotations=read_only)
    async def session_status() -> dict:
        """Whether this tool's session runs: both processes alive, both hellos, the last
        sequence number per peer, new crash logs, and the -mod= line of the run."""
        return await anyio.to_thread.run_sync(session_status_impl)

    @mcp.tool(annotations=acts)
    async def session_stop() -> dict:
        """Stop the session this tool started: get the player out of a car, end only its own two
        processes, remove @AZ_TestBridge and close the token folders. Safe to call after a failure."""
        return await anyio.to_thread.run_sync(session_stop_impl)

    @mcp.tool(annotations=acts)
    async def session_restart(keep_storage: bool = True) -> dict:
        """Shut the server down in order (it saves its world), then start server and client again
        with the same mods and token. keep_storage=true keeps what this session's server saved, so a
        mod's saved data can be checked after a restart; false starts from a fresh storage-free copy.
        Reports whether the shutdown was graceful. Takes a few minutes."""
        return await anyio.to_thread.run_sync(session_restart_impl, keep_storage)

    @mcp.tool(annotations=acts)
    async def session_restart_client() -> dict:
        """End only this session's client and start it again into the running server: for a frozen
        picture, a client bound to its first car, or get_in failing again and again."""
        return await anyio.to_thread.run_sync(session_restart_client_impl)

    @mcp.tool(annotations=acts)
    async def command(cmd: str, args: Optional[dict] = None, peer: Optional[str] = None) -> dict:
        """Send one allowlisted command (see list_commands) and return {seq, ok, error, peer,
        game_time_ms, data}. `peer` is needed only for commands that run on both (ping, mark,
        vehicle_state, exec). Positions are [x, y_up, z]. ok=false with an error code is the game's
        answer (for example not_driver, vehicle_has_crew, spawn_failed); a raised error is the tool."""
        return await anyio.to_thread.run_sync(command_impl, cmd, args, peer)

    @mcp.tool(annotations=acts)
    async def mark(label: str) -> dict:
        """Save the current end of every log under `label` and print [AZ-BRIDGE] MARK <label> on
        both peers. logs_since(label) then reads only what came after."""
        return await anyio.to_thread.run_sync(mark_impl, label)

    @mcp.tool(annotations=read_only)
    async def logs_since(mark: str = "", peers: Optional[list[str]] = None, kinds: Optional[list[str]] = None,
                         regex: Optional[str] = None, triage: bool = False, limit: int = 500) -> dict:
        """Script log (`script`) and RPT (`rpt`) lines of the server and client written since `mark`
        (empty: since the session started), each with peer, file and line number; the last `limit`
        lines (1 or more) are returned with the total. Lists [AZ-BRIDGE] ERROR lines apart. triage=true tags
        each line with its /dayz-gate category."""
        return await anyio.to_thread.run_sync(logs_since_impl, mark, peers, kinds, regex, triage, limit)

    @mcp.tool(annotations=acts)
    async def screenshot(name: str, crop: Optional[list[int]] = None) -> dict:
        """Capture the DayZ client window from outside the game (PrintWindow: never moves the mouse
        or brings the window to the front) to output/testbridge/<token>/<name>.png. crop is
        [x, y, width, height]. A black frame or a minimized or locked desktop is a failed capture
        (ok=false), not a mod failure."""
        return await anyio.to_thread.run_sync(screenshot_impl, name, crop)

    return mcp


def main() -> int:
    try:
        mcp = build_app()
    except ImportError as e:
        print(f"dayz-testbridge needs the mcp package: pip install -r \"{HERE / 'requirements.txt'}\" ({e})",
              file=sys.stderr)
        return 1
    mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
