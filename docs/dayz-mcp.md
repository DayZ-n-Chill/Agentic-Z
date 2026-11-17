# DayZ-MCP: the in-game half

Everything under `scripts/tools/` and in the offline checks ends at the same sentence: now go look in game. That step is the expensive one: a rebuild, a server, a client, a scenario set up by hand, several minutes per iteration. DayZ-MCP (its own repository, installed separately) is an MCP server that lets an agent take that step itself by driving a running DayZDiag server and client.

It is not part of this repo and nothing here starts it. DayZ-MCP is a third-party tool, not vanilla: the statements about the bridge on this page are not yet checked on `P:\`, and the tool list of the installed server is the authority for what it offers. The vanilla script citations were opened on `P:\`. The bridge protocol note, `skills/_shared/knowledge/mcp-bridge-protocol.md`, has the protocol, the safety invariants and the engine facts in full.

## What it offers

The exact tool count depends on the installed version; its tool list is the authority. `exec_enforce` is an escape hatch: off by default, behind an exact-match allowlist. The bridge protocol note lists the tools by group:

- a session lease, so two agents cannot fight over one game
- queries on player state
- world mutation: spawn, delete, animate, time, weather, inventory, teleport
- scene reads: raycast, surface query, object inspect, telemetry
- camera and capture
- vehicles: enter, engine, control, telemetry, trace
- lifecycle: `dayz_test_run` builds a mod, starts a diag server and client with it loaded, and waits for readiness; `dayz_test_stop` ends the run

The invariants that keep it safe: server-authoritative, one FIFO lease, fail-closed ingress, controls held by a deadman.

## Engine facts it cost in-game cycles to learn

The split is not by tool group, it is by peer.

- `vehicle_enter` seats a player on the server. Only `vehicle_get_in_client`, which makes the client take ownership, lets the agent actually drive.
- `SetThrottle` sets a future input value (`P:\scripts\3_game\vehicles\car.c:190-191`), and the engine's input simulation step replaces it. Set it inside an `OnInput` override after `super.OnInput(dt)`, which runs after every input simulation step and is where setters belong (`P:\scripts\3_game\vehicles\transport.c:346-349`). Calling `SetThrottle` from anywhere else never moves a car.
- `DEVELOPER` is not defined in DayZDiag; `DIAG_DEVELOPER` is. Vanilla guards its diag code with `#ifdef DIAG_DEVELOPER` (`P:\scripts\3_game\global\game.c:22`).
- Freecam freezes the simulation that is being measured.

## Install and wiring

Clone the DayZ-MCP repository into a folder named `dayz-mcp`, then run its installer:

```powershell
cd dayz-mcp\tools
.\install-mcp.ps1 -Register
```

The installer creates `tools\.venv-mcp` inside the clone and registers the server. The client wiring it writes has this shape. Copy it into the `.mcp.json` of the project that will use it and set `command` to that venv's `python.exe`:

```json
{
  "mcpServers": {
    "dayz-mcp": {
      "command": "<dayz-mcp>/tools/.venv-mcp/Scripts/python.exe",
      "args": ["-m", "dayz_mcp", "--client"],
      "env": {
        "MAX_MCP_OUTPUT_TOKENS": "75000"
      }
    }
  }
}
```

- Keep an example of this wiring under a name other than `.mcp.json` until the bridge is installed. Agents auto-start the servers declared in `.mcp.json`, and a failed launch on every session is worse than no config.
- `MAX_MCP_OUTPUT_TOKENS` raises the per-tool output cap so screenshots come back at a usable resolution. At the 25k default a frame lands around 580 px wide.

Two skills use the bridge: `dayz-mcp-verify`, and the managed runs in `dayz-test-ingame`, which start and stop the game with `dayz_test_run` and `dayz_test_stop`. The acceptance ladder of `dayz-mcp-verify` for a drivable vehicle is spawn, render, get in, drive, wheel direction. It can also open and close doors with `door_index` and open and click a mod's UI. Free player input (shooting, reloading, interactive inventory, vanilla menus), holding a door at a static pose, and continuous actions stay manual.

## What it is not

- Not a test framework. It drives the engine and reports; deciding what counts as a pass stays with the caller.
- Not fully headless. Some operations need a real client attached. That is DayZ's limit, not a design choice.
- Not hot-reloading. A live daemon serves the modules it loaded at start, so a newly added verb does not exist until it restarts.
- Not well tested with several clients, because one Steam account is one client.
