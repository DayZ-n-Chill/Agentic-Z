# dayz-mcp on Linux

The state of the dayz-mcp bridge on a Linux host, measured 2026-11-06. Everything else in this skill is the Windows workflow and stays valid there.

All of it is third-party tool behaviour measured in game sessions, not yet checked on `P:\`; none of it is a vanilla fact. The Linux setup for the game and DayZ Tools is in `skills/_shared/linux-proton.md`. The longer findings note behind this page is `skills/_shared/knowledge/linux-proton-findings.md`, section 9.

## What works

- **The `@DayZ_MCP` addon** works on the native Linux `DayZServer` and on `DayZDiag` under Proton, client and server. It was packed and signed with bzed's fork of armake2, now named dayzmake (https://github.com/bzed/dayzmake, use 1.0.0 or later; `dayzmake build addon <out>/addons/DayZ_MCP.pbo`, with the prefix taken from `$PBOPREFIX$`), and polled the daemon on `127.0.0.1` at about 1 Hz.
- **The Python side runs on Linux**: `--daemon` and `--client` with leases and the `session_*` tools, `dayz_test_run` with `mode=all`, `server` or `client` and `build=true`, `dayz_test_close` and `dayz_test_stop`.
- With `mode=all`, `bridge_status` reached `ready` with `server_bound_last_poll_age_s` and `client_bound_last_poll_age_s` set, about 34 s after `dayz_test_run` returned.

Linux host support was merged into dayz-mcp's `main` on 2026-11-14 (https://github.com/willy92wins/dayz-mcp/pull/411, the successor of a closed earlier pull request, #353). The managed-cycle observations above were measured on the `linux-port` branch on 2026-11-06, before that merge, and were not measured again on `main`. They do not verify a managed binarize of a mod with assets.

## Traps

- **`ready` can come before the join.** One run showed the client still on its loading screen at that moment. Wait for `is connected` in the server RPT before spawning at the player.
- **After a close with a player in the world, the client's exit metrics are not valid** (the `dayz-test-ingame` skill's Linux references have the detail).
- **A game started by hand polls as `LEGACY_UNBOUND`**: reads only, with mutations refused as `game_not_ready:reason=legacy_unbound`, and `bridge_status` also waits for a client peer. Start the game through `dayz_test_run`.
- **A managed client runs in a headless sway session.** When the logs show nothing, take a screenshot of it:

  ```sh
  WAYLAND_DISPLAY=$(cat <state>/DayZ_MCP/proton-clients/<session>/wayland-display) grim out.png
  ```

  That is how a modal dialog with code `0x00020017` was found.
- **Windows-only pieces**: the launcher script `dayz-test.ps1`, dayz-mcp's `install-mcp.ps1` and the native launcher.

## Not verified

Which bridge tools work in the world on Linux, beyond `bridge_status`, was not verified tool by tool.
