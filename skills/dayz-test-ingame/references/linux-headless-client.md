# Testing the client side on Linux: a headless client and a self-reporting test mod

`linux-native-server.md` proves the server half of a mod. Anything a player drives (UI, input, what the client
sees after a server change, RPCs both ways) needs a real client. This page runs the retail client under Proton
without a monitor, joins it to a local native server, and lets a test mod report its own results.

**Measured** by bzed (the author of the dayz-dev-plugin client-testing harness) on Linux with the
1.30.164014.27 pre-release (then on the Experimental apps, 1024020) unless a line says otherwise; GE-Proton11-1, an AMD
GPU on Vulkan/RADV, sway 1.12. This page targets DayZ 1.30 or later.
The author re-tested the whole plugin on DayZ 1.30 stable (the author's report, 2026-11-13; build not recorded here).
These are measured tool and runtime results, not yet checked on `P:\`; the one vanilla script fact (godmode) is
cited inline and was re-opened on `P:\scripts\`.

Scripts: `skills/_shared/scripts/dayz-client-headless.sh`, `dayz-client-test.sh`, `dayz-mod-pack.sh`. Test mod:
`../assets/autotest-mod/`. This pairs the **retail** client with the **native** server. A `DayZDiag` client only
joins a `DayZDiag` server (`0x00020017`); that pairing, and the managed dayz-mcp cycle, are in
`skills/_shared/linux-proton.md` and in `linux.md` in this folder.

## What you need, and the ground rules

- A running, logged-in Steam that owns DayZ (the game talks to it), the client installed, a Proton tool,
  `sway` and `grim`.
- A server tree (`linux-native-server.md`) with the mods and their `.bikey`s; removing CF since it last ran is an observed storage breakage, while adding CF needing a wipe is an unisolated hypothesis — isolate first before rotating its `storage_1` (see `linux-native-server.md`, "Storage and CF").
- **One game at a time.** A Steam account runs one game, and a second client would fight the first over GPU,
  Wine prefix and Steam connection, including the user's own game: if they are playing, wait or ask. Servers
  can run side by side.
- `dayz-client-headless.sh status` lists running clients (exit 1 if there is one); `start` and
  `dayz-client-test.sh` refuse to start a second game. Never kill a game you did not start.
- **Stop the game as soon as you are done**: it holds the GPU, several GB of RAM, and shows the account as
  "playing DayZ". `dayz-client-test.sh` stops its client itself, also on failure, timeout or Ctrl-C.

## 1. The client without a display

```sh
S=skills/_shared/scripts/dayz-client-headless.sh
$S start /var/tmp/dzc -name=autotest "-mod=@9dd22c91;@MyMod" -connect=127.0.0.1 -port=$GAME
$S shot  /var/tmp/dzc /var/tmp/dzc/now.png
$S stop  /var/tmp/dzc                         # ends sway, which ends the game
```

It starts a headless sway (`WLR_BACKENDS=headless`, 1280x720) and runs inside it the chain Steam itself uses
(Steam Linux Runtime 4 `_v2-entry-point` → `proton run` → `DayZ_x64.exe`), so the game inherits that session's
display while the Steam API handshake still goes to the running Steam (measured). `steam -applaunch` would hand
the launch to the running Steam and land on your desktop (reasoned, not run). Also measured:

- `for_window [app_id="dayz_x64.exe"] fullscreen enable`, or the window is larger than the output and the
  screenshot is cropped;
- `-nolauncher -skipintro -window -nosplash -noPause`; `-connect=<ip> -port=<port>` joins with no clicks;
- `-name=<x>` shows in the server's admin log, the cheapest "client connected" check;
- DayZ's arguments go one per line into a file, because sway's parser would cut `-mod=@a;@b` at the `;`;
- `PROTON` (default `GE-Proton11-1`) and `STEAM_ROOT` select the Proton tool; `PROTON_ENABLE_WAYLAND=1` is set.
  `STEAM_ROOT` (default `~/.steam/debian-installation`) must be the library that holds the client; unlike
  `find-dayzserver.sh`, the client scripts do not search other library folders.

## 2. Mods on the client

The client loads mods by folder name from its install directory, so link them there (this writes a symlink
into the Steam directory; remove it when done):

```sh
ln -sfn "$PWD/build/@MyMod" "<library>/steamapps/common/DayZ/@MyMod"
```

- **Use the client-side names in the client's `-mod=`.** The server's `@CF` is the client's hashed
  `@9dd22c91 -> workshop/content/221100/1559212036` here (find yours with
  `ls -l <client dir> | grep <workshop id>`). A name that does not exist loads nothing, and the game still
  starts and even shows the "modded game" notice.
- **A wrong or missing client mod** gets the player kicked with
  `Client is missing a mod which is on the server. (<mod names>) (Missing PBO.)` in the server's output and
  logs. Read that before suspecting the network.
- Dependencies first (CF before the mods that need it); the reverse order was not tried.
- Keep `verifySignatures = 2` and every mod's `.bikey` in the tree's `keys/`; signed mods with their keys
  joined. An unsigned mod with signature checks on was not tried.
- **BattlEye**: a client started this way does not start BattlEye, so set `BattlEye = 0;` in the tree's
  `serverDZ.cfg`.

## 3. Tests that run on both sides and report back

Seeing the client connect proves little. `../assets/autotest-mod/` runs code on the server and on the client in
a known order and prints results an outside script can grep; it ran green on both builds above.

```
 server (drives)                               client (executes)
 wait until the player is connected, godmode on
 test N: ServerSetup(player)
 RPC AUTOTEST_RPC_RUN(name) ----------------->  ClientCheck()  (retried for up to 5 s while it returns false)
                              <---------------  RPC AUTOTEST_RPC_RESULT(name, passed, message)
 ServerCheck(player)
 Print("[AUTOTEST] PASS|FAIL name message")
 ...
 Print("[AUTOTEST] DONE passed=P failed=F")    <- the line an outside script waits for
```

- The server is the only driver; both sides load the same PBO, so only the test name (and optional per-test setup parameters, such as a created entity's network id) crosses the wire.
- One RPC out, one back per test; a 20 s timeout turns silence into `FAIL ... no answer from the client`, so a
  crashed or absent client fails the run instead of hanging it.
- Client checks retry every 500 ms for up to 5 s: replication lag does not flake, a state that never arrives
  still fails.
- Results go to the server's script log; the client prints `[AUTOTEST-CLIENT]` lines to its own.

**Adding a test.** A test is a class in `scripts/4_World/AutoTestCases.c` (`Name()`, `ServerSetup(player)`,
`ClientCheck(out msg)`, optional `ServerCheck(player, out msg)` and `NeedsDamage()`), registered in
`AutoTestRegistry.All()` in run order. To test your own mod, copy the addon into a separate test mod
(`@MyMod_Test`) that depends on yours, load it with `-mod=` on both sides, and keep it out of the release. The
mod name is also a script define (`#ifdef AutoTest`, visible in the `Module: ...; defines:` line).

**Godmode.** The runner records `player.GetAllowDamage()` before it first calls
`player.SetAllowDamage(false)` (`P:\scripts\3_game\entities\object.c:1191-1196`) [EXACT][CLAIM-OBJECT-ALLOWDAMAGE-130], sets godmode between tests, and restores the recorded value when the run
finishes, times out or is aborted; a test that overrides `NeedsDamage()` to `true` gets damage for itself
only. Results (`AUTOTEST_RPC_RESULT`) are accepted only from the identity of the player the run was
scheduled for; other senders are ignored with a `Print`. A server-side melee hit left health `100 -> 100`
and the same hit with damage allowed gave `100 -> 95` (both builds, measured by the author before this
change). Only the harness's own `ProcessDirectDamage` with `MeleeZombie` was tried, not real zombies,
animals, falls, hunger, thirst or cold. The sender-binding and restore change in the bundled `AutoTestRunner.c`
was checked by the offline script linter only, not run in game [EXACT][CLAIM-AUTOTEST-RUNNER-UNVERIFIED].

**Pitfalls found building it**:

- Pick RPC ids no other mod uses (the example uses 74010 and 74011; there is no registry).
- The runner starts 20 s after `InvokeOnConnect`, because the client is still loading.
- Several players need several clients; this runs one.

## 4. One command: start, wait, report, stop

```sh
skills/_shared/scripts/dayz-client-test.sh -t "$TREE" -s "@AutoTest" -c "@AutoTest" -o /var/tmp/run1
# [AUTOTEST] PASS client_has_player local player SurvivorM_Rolf
# [AUTOTEST] PASS server_item_synced Chemlight_Red replicated to the client
# [AUTOTEST] PASS godmode_blocks_damage  | server: health 100 -> 100
# [AUTOTEST] PASS damage_when_needed  | server: health 100 -> 95
# [AUTOTEST] DONE passed=4 failed=0
```

Free ports, server, headless client, wait for `DONE`, collect `[AUTOTEST]` lines, final screenshot, teardown. With
CF in the server's mod list pass `-m mpmissions/<mission>` (relative): CF resolves `$mission:`/`$storage:` from it.
Exit 0 = `DONE` seen and no `FAIL`; 1 = a failure or the timeout (default 300 s; a cold client start alone takes
about 60 s), which saves `timeout.png`. Build and sign the example first:
`dayz-mod-pack.sh -C <copy of assets/autotest-mod> keygen`, then `build`; link `build/@AutoTest` and
`keys/AutoTest.bikey` into the tree and `build/@AutoTest` into the client directory. The key is a test key: never
install it on a real server.

## 5. Reading what the client did

- Client script log: `<compatdata>/<221100|1024020>/pfx/drive_c/users/steamuser/AppData/Local/<DayZ|DayZ Exp>/script_<date>.log`
  (newest = current run): compile errors, `Print` output, `NULL pointer` traces.
- `crash_<date>.log` beside it holds a client-side script exception with its stack, so a mod can be checked for
  client exceptions without looking at the screen.
- Screenshots answer "is the HUD there", not pixel asserts.
- The server's `profiles/*.ADM` has `Player "<name>" is connecting` / `is connected` and the spawn position: the
  reliable join signal.
- The game's main thread is `enfMain` in `ps`, like the server; find it through `swaymsg -t get_tree` (`pid`) or
  just `stop` the session. `pkill -f DayZ_x64.exe` kills the shell running it (exit 144).

## Experimental (the next build, optional)

1.30 is stable, so the stable apps above are the default. Experimental has its own client (1024020, `DayZ Exp`), server (1042420), Wine prefix (`compatdata/1024020`) and
log folder (`AppData/Local/DayZ Exp/`), and its script log lines carry a timestamp prefix. It has **no Workshop of
its own**: subscribe through stable, link the items from `workshop/content/221100` into `steamapps/common/DayZ Exp`,
build the server tree from `find-dayzserver.sh -e`, and pass `-e` to the client scripts. Without `-e` they start
the stable client against the experimental server, which `forceSameBuild = 1` should reject (not run). The same
AutoTest PBO passed unchanged on 1.30.164014.27 with the stable Workshop's CF (`DONE passed=2 failed=0`).

## Expansion bundle: skip the spawn selector first

With the Expansion bundle (or DayZ-Expansion-Spawn-Selection, 2804241648) the client lands in the spawn selector,
where screenshots show the menu and item handling does not work. On a fresh server profile, before the client
joins (measured 1.30.164078.38: the client then joined straight into the world, HUD visible):

1. Start the server once, so Expansion writes its settings and the storage; stop it.
2. In `mpmissions/<mission>/expansion/settings/SpawnSettings.json` set `"EnableSpawnSelection": 0`.
3. Delete `mpmissions/<mission>/storage_1/players.db` (a stored character skips the fresh-spawn path).
4. Start the server again, then join.

Repeat it for every new server config that loads the bundle. The bundle already contains Spawn-Selection. The mod set
and its load order: `skills/dayz-mod-workflow/references/dayz-1-30-server-measured.md`, section 8; on the client use the
client-side folder names of the same mods.

## Not covered

gamescope and Xvfb (Xvfb has no DRI3 path, so DXVK presentation is in doubt), input injection, BattlEye-enabled
servers, several clients, Windows and macOS were not run.
