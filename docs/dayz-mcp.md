# DayZ-MCP: the in-game half

Everything under `scripts/tools/` and in the offline checks ends at the same sentence: now go look in game. That step is the expensive one: a rebuild, a server, a client, a scenario set up by hand, several minutes per iteration. DayZ-MCP (<https://github.com/willy92wins/dayz-mcp>, its own repository, installed separately) is an MCP server that lets an agent take that step itself by driving a running DayZDiag server and client.

It is not part of this repo and nothing here starts it. This page came in with the DayZ Modding Knowledge Pack import; the statements about the bridge are the Knowledge Pack's and were not re-measured during the import. The bridge protocol note, `skills/_shared/knowledge/mcp-bridge-protocol.md`, has the protocol, the safety invariants and the engine facts in full.

## What it offers

75 tools, plus `exec_enforce` when an allowlist is configured. `exec_enforce` is an escape hatch: off by default, behind an exact-match allowlist. The tools group into:

- a session lease, so two agents cannot fight over one game
- queries on player state
- world mutation: spawn, delete, animate, time, weather, inventory, teleport
- scene reads: raycast, surface query, object inspect, telemetry
- camera and capture
- vehicles: enter, engine, control, telemetry, trace
- weapons
- actions and input
- UI
- knowledge
- playbooks
- the pipeline inbox
- lifecycle: `dayz_test_run` builds a mod, starts a diag server and client with it loaded, and waits for readiness; `dayz_test_stop` ends the run

The invariants that keep it safe: server-authoritative, one FIFO lease, fail-closed ingress, controls held by a deadman.

## Engine facts it cost in-game cycles to learn

The split is not by tool group, it is by peer.

- `vehicle_enter` seats a player on the server. Only `vehicle_get_in_client`, which makes the client take ownership, lets the agent actually drive.
- `SetThrottle` sets a future input value (`P:\scripts\3_game\vehicles\car.c:190-191`), and `CarScript.OnInput` (`P:\scripts\4_world\entities\vehicles\carscript.c:1041`) then overwrites it. Calling `SetThrottle` alone never moves a car.
- `DEVELOPER` is not defined in DayZDiag; `DIAG_DEVELOPER` is. Vanilla guards its diag code with `#ifdef DIAG_DEVELOPER` (`P:\scripts\3_game\global\game.c:22`).
- Freecam freezes the simulation that is being measured.

## Install and wiring

```powershell
git clone https://github.com/willy92wins/dayz-mcp
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

The skill that uses the bridge is the Knowledge Pack's `dayz-mcp-verify`. Its acceptance ladder for a drivable vehicle is spawn, render, get in, drive, wheel direction. Player UI, door interaction, inventory use and firing stay manual.

## What it is not

- Not a test framework. It drives the engine and reports; deciding what counts as a pass stays with the caller.
- Not fully headless. Some operations need a real client attached. That is DayZ's limit, not a design choice.
- Not hot-reloading. A live daemon serves the modules it loaded at start, so a newly added verb does not exist until it restarts.
- Not well tested with several clients, because one Steam account is one client.
