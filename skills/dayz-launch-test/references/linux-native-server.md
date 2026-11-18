# Native Linux server tests

How to prove the server half of a mod on the native Linux `DayZServer` without dayz-mcp: where the server comes from, the private tree it runs from, ports, the launch line, and how to read whether the mod loaded, compiled and ran. A syntax check and a clean build do not show that the scripts compile, that a `modded class` or `override` is legal, or that the engine loaded them at all; a local dedicated server answers all three in about a minute with no client.

Measured with the native Linux `DayZServer` (Steam app 223350) on DayZ 1.30, and again in full on 1.30 stable; a build named in the text is where a detail was first seen. These are server and tool results, not checked on `P:\`; the vanilla script symbols under "Read the result" and "Code that needs players" are cited. The Windows server (`DayZServer_x64.exe`) takes the same parameters, but where the two differ the Windows rules in `README.md` and `/dayz-launch-test` win on Windows. The managed route with dayz-mcp is in `linux.md`; a real client is in `linux-headless-client.md`.

Scripts: `scripts/tools/dayz-linux/` (`find-dayzserver.sh`, `make-server-tree.sh`, `free-ports.sh`), tested by `scripts/tools/dayz-linux/test_linux_helpers.py`.

## Use the server Steam installed

Use the "DayZ Server" tool (app 223350) that the user's Steam installed: it is signed in, and Steam keeps it on the build a client must match. A separate `steamcmd` install cannot sign in anonymously (223350 needs an account that owns DayZ, with password and Steam Guard) and drifts from the client build unless you update it. Never install it for the user; ask them to install DayZ Server from the Library's Tools filter (or `steam steam://install/223350`) and wait until they confirm.

```sh
S=scripts/tools/dayz-linux
sh "$S/find-dayzserver.sh" -v     # install folder on stdout; buildid and StateFlags on stderr
sh "$S/find-dayzserver.sh" -w     # the DayZ client's workshop folder (content/221100)
sh "$S/find-dayzserver.sh" -e -v  # Experimental server 1042420 ("DayZ Server Exp", note the space)
```

It reads `libraryfolders.vdf` of every known Steam root and trusts `appmanifest_223350.acf`, not the `"apps"` list in `libraryfolders.vdf`, which can be stale. Exit 0 means found; a `StateFlags` other than 4 means Steam is still installing or updating, and the script warns.

| | Server | Client | Workshop items |
|---|---|---|---|
| Stable | 223350, `DayZServer` | 221100, `DayZ` | `workshop/content/221100` |
| Experimental | 1042420, `DayZ Server Exp` | 1024020, `DayZ Exp` | none of its own; the stable `content/221100` (`-e -w` falls back to it) |

Stable is the default since 1.30 is stable; Experimental carries the next build and is only for testing a mod ahead of that release. Experimental runs a diag build (`DEVELOPER`, `DIAG_DEVELOPER`, `BUILD_EXPERIMENTAL` in the `defines:` of the `Module:` log lines): `Error()` and `ErrorEx()` print as `Virtual Machine Exception`, and some `SCRIPT (E)` lines such as `Leaked 'BunkerBroadcastManager'` are vanilla noise, so compare against a vanilla run. On 1.30 Experimental a script compile error was followed by a segfault of the server, so a crash right after boot means reading `script_*.log` for `Can't compile` first.

## Build a tree outside the Steam install

Steam owns the install: an update or "Verify integrity" overwrites what you put there, and a server run from it writes `storage_1/` and core dumps into it. Run from a tree of your own that links into Steam:

```sh
TREE=$(sh "$S/make-server-tree.sh" /var/tmp/dzt)   # short path, outside Steam
```

| In the tree | What it is |
|---|---|
| `DayZServer`, `addons/`, `dta/`, ... | one symlink per top level entry of the install |
| `serverDZ.cfg` | a copy, yours to edit |
| `mpmissions/<mission>/` | a real folder of per-file symlinks, so `storage_1/` lands in the tree |
| `keys/`, `battleye/` | real folders of per-file symlinks; add your `.bikey` here |
| `profiles/` | for `-profiles=profiles` |

- To edit a file Steam provides, replace its symlink with a copy first: `cp --remove-destination "$(readlink "$TREE/mpmissions/<m>/init.c")" "$TREE/mpmissions/<m>/init.c"`.
- Run the script again after a Steam update; it refreshes the links and keeps your real files.
- The tree is disposable. Keep its path short: a deep path broke persistence with `File path exceeds max filename length. (291 > 280)` and no `spawnpoints.bin`.
- One tree per running server. A server locks its `profiles/` and the `storage_1/` of its mission; two servers on one tree collide, and the logs afterwards belong to neither.
- Run the trees one at a time anyway. A 1.30 server with the Expansion bundle used about 7.5 GB resident, and a pair plus forgotten leftovers pushed a large workstation to its memory limit. A boot takes about two minutes, so stop one server (by process id, below) before starting the next, and check `free -h` first if two must overlap.
- Since the first 1.30 patch an absolute `-profiles=` outside the tree works; keep `-profiles=profiles` anyway so each run's logs stay in its tree.

### Ports

Every server needs its own game, Steam query and RCon port. The defaults (2302, 2303, 2306) are what a real server, a local client or the last test run still holds, and a collision may not error: the server answers on the wrong socket or RCon silently stays down.

```sh
set -- $(sh "$S/free-ports.sh" 3); GAME=$1 QUERY=$2 RCON=$3   # free for UDP and TCP, 10 apart, no defaults
```

| Port | Where |
|---|---|
| game | `-port=$GAME` |
| Steam query | `steamQueryPort = $QUERY;` in the tree's `serverDZ.cfg` |
| RCon | `RConPort $RCON` in `$TREE/profiles/battleye/beserver_x64.cfg` |

- Insert `steamQueryPort` at the top, never with `echo >>`. The stock `serverDZ.cfg` ends with `};` and no newline, so an appended line becomes `};steamQueryPort = ...;`, a later `sed '/steamQueryPort/d'` deletes the brace too, and the server exits with `Missing '}'`:

  ```sh
  grep -q '^steamQueryPort' "$TREE/serverDZ.cfg" || sed -i '1i steamQueryPort = 0;' "$TREE/serverDZ.cfg"
  sed -i "s/^steamQueryPort = .*/steamQueryPort = $QUERY;/" "$TREE/serverDZ.cfg"
  ```

- The RCon seed lives in the profile folder. With `-profiles=profiles` the server reads `profiles/battleye/beserver_x64.cfg` once, writes `beserver_x64_active_<hex>.cfg` beside it and uses only that copy afterwards, so delete stale active copies before seeding, and use a random password:

  ```sh
  mkdir -p "$TREE/profiles/battleye"
  find "$TREE/profiles/battleye" -name 'beserver_x64_active_*.cfg' -delete
  printf 'RConPassword %s\nRestrictRCon 0\nRConPort %s\n' \
      "$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c10)" "$RCON" > "$TREE/profiles/battleye/beserver_x64.cfg"
  ```

### Mods are symlinks in the tree

```sh
ln -sfn "$PWD/build/@MyMod" "$TREE/@MyMod"           # your build: rebuild, rerun, no copy step
W=$(sh "$S/find-dayzserver.sh" -w)
grep -h '^name' "$W"/*/mod.cpp "$W"/*/meta.cpp        # find a mod's id by name
ln -sfn "$W/1559212036" "$TREE/@CF"                   # Community Framework
ln -sfn "$W/1559212036/keys/"*.bikey "$TREE/keys/"
```

Only subscribed items are in the workshop folder. If a mod is missing, ask the user to subscribe and start the launcher once; never `steamcmd +workshop_download_item` into Steam's folders.

### Storage and Community Framework

Community Framework (CF) writes extra data into every saved entity, and storage belongs to the mod set that wrote it (`build-and-storage-traps.md`, measured on Windows): adding CF to storage written without it crashed the server on read (`CF_ModStorageObject` ... `OnStoreLoad_CF`). On Linux:

- **Removing CF** (the first 1.30 patch): a tree booted once with `-mod=@CF` and then vanilla logged about 24,000 `Virtual Machine Exception`s during the Central Economy load, all `[EntityAI::OnStoreLoad] :: [WARNING] :: Scripted variables corrupted upon "PileOfWoodenPlanks". Entity will not be loaded correctly.` The server kept running, so a boot that "works" proves nothing: grep for `Scripted variables corrupted`.
- **Adding CF, a `CF_Trace` compile error** (cause not isolated): a boot died with `Unknown type 'CF_Trace'` and `Can't compile "Engine" script module`. That is a compile error of the Engine module, not the storage read crash, and the trees were rebuilt at the same time, so storage was not shown to be the cause. It reads like a CF and Expansion version conflict. Rotating storage does not fix a compile error, so isolate first (rebuild with the same storage kept, or copy the storage aside and retry). Rotate storage anyway when the mod set changed.

Never delete storage. With the processes stopped, rename it to a name that does not exist yet; deleting is only for a throwaway test tree you built:

```sh
mv "$TREE/mpmissions/<mission>/storage_1" "$TREE/mpmissions/<mission>/storage_1.<tag>"   # <tag> must not exist yet
```

## Run it headless

```sh
cd "$TREE" && ulimit -c 0 && timeout -k 15 60 ./DayZServer \
    -config=serverDZ.cfg -profiles=profiles \
    -servermod=@MyMod "-mod=@CF" -port=$GAME -nosplash -nopause -dologs
```

- **Mod paths relative to the tree.** Absolute `-servermod=` and `-mod=` paths are silently ignored: the engine probes the folder, loads no PBO and prints no error. Symlinks or `../` work; `-config` and `-profiles` take absolute paths. This is the reverse of the Windows rule in `README.md` ("Rules that hold on every route").
- **Relative `-mission=mpmissions/<name>`.** An absolute one leaves the 1.30 server without `init.c`'s `main` (`_shared/linux-proton.md`, "Pitfalls").
- **Run from the tree:** `addons/` and `mpmissions/` resolve against the working folder.
- **`ulimit -c 0`:** a crash writes a core file of up to about 5 GB into the working folder.
- **`timeout -k 15 60`:** the mission is up after about 10 seconds, then the server idles forever. A quiet log is not a slow server; it means your code did not run. Keep the `-k`: after `Termination successfully completed` the process can hang in Steam API threads until SIGKILL.
- `-mod=` is for mods the client loads too; a headless run still proves only the server side.

### Listing and stopping test servers

`pkill -x DayZServer` and `pgrep -x DayZServer` do not match a running Linux server: it renames itself (`enfMain` in the comm column), and their silent no-match looks exactly like "nothing running" while several 7.5 GB servers keep going. List by command line and kill by process id:

```sh
ps aux | grep "[D]ayZServer"     # the [D] keeps grep itself out
kill <pid>
```

- Never `pkill -f DayZServer` in the same command line: the pattern matches the shell running it, which kills itself (exit 144).
- A server started as a background child of an agent's shell can be reaped when that shell ends. Start one that must outlive the tool call with `setsid nohup ./DayZServer ... >server.log 2>&1 &` and keep its process id.
- Other DayZ servers on the machine are not yours: check the `ps` arguments (tree, ports) first.

## Read the result

`$TREE/profiles` gets `script_<date>.log`, `DayZServer_<date>.RPT` and `error.log`.

```sh
grep -h 'Module: Game; loaded' "$TREE"/profiles/script_*.log   # files per script module
grep -h 'SCRIPT.*(E)' "$TREE"/profiles/script_*.log            # compile errors
grep -h 'MyMod' "$TREE"/profiles/script_*.log                  # your own Print lines
```

1. **Did the scripts load at all?** Boot once without the mod for a vanilla baseline (440 Game module files on 1.30 Experimental; take your own on the build you test). Compare each script module the mod adds files to (3_Game, 4_World, 5_Mission, ...) with that baseline: an unchanged count in a module where the mod has files means its scripts were not loaded there (a mod with only 4_World and 5_Mission files leaves the Game count unchanged, as it should). The count is only an indicator: a rise can come from other mods. Silent causes seen:
   - the PBO at the mod folder root (`@MyMod/MyMod.pbo`) instead of `@MyMod/addons/MyMod.pbo`: ignored, while the folder still shows in the `ANIMATION (E): Can't load @MyMod/...` pass, which is not loading (`/dayz-build-pbo` deploys to `@<ModName>\Addons\`);
   - an absolute mod path (above);
   - on 1.30, backslashes in the `CfgMods` script module paths (`files[] = {"MyMod\scripts\4_World"}`): the defines appear, no script compiles, no error (`dayz-1-30-server-measured.md`, "Script module paths need forward slashes");
   - a PBO without the prefix its `config.cpp` script paths expect, or inner names that repeat the prefix (`MyMod\MyMod\config.cpp`): pack from inside the addon folder.

   When a `modded class` or `override` silently does nothing, put a deliberate syntax error in one of the mod's scripts and boot once. A clean boot means the file was never compiled and the mod is not loading; a compile error means it is. Prove the scripts are in the compile set before theorising about override order or API misuse.
2. **Did they compile?** `SCRIPT    (E)` lines are compile errors. The tag is space padded, so the literal `SCRIPT (E)` never matches; grep `SCRIPT.*(E)`.
3. **Did your code run?** A `Print("MyMod: loaded ...")` in a mission or init hook is the cheapest proof.

Only a boot catches engine classes that cannot be `modded` (for example `DayZPlayerInventory`, declared at `P:\scripts\4_world\systems\inventory\dayzplayerinventory.c:147`), proto native methods that cannot be overridden (for example `SendSyncJuncture`, `P:\scripts\3_game\dayzplayer.c:1303`), and wrong override signatures. A server that "works" proves nothing about load order either: `dayz-1-30-server-measured.md`, "Mod load order is not the `-mod` order".

## Code that needs players

Without a client, player driven hooks (actions, inventory, damage, vitals) never fire. Drive them from a scratch copy of the mod with a debug call: `g_Game.CreatePlayer(null, "SurvivorM_Mirek", pos, 0, "NONE")` (signature at `P:\scripts\3_game\global\game.c:332`), then `GetHumanInventory().CreateInHands(...)` (`P:\scripts\3_game\systems\inventory\humaninventory.c:44`), then the method under test. Such a player has no `PlayerIdentity`, so code that filters on `GetIdentity()` skips it; mark those runs partial. For a real client (UI, replication, RPCs both ways) see `linux-headless-client.md`.

## On Windows (not verified)

The Steam root is `HKCU\Software\Valve\Steam` `SteamPath`; `libraryfolders.vdf` and the manifests have the same format; the binary is `DayZServer_x64.exe`; stop it with `Stop-Process`. `make-server-tree.sh` is POSIX sh; the same tree on Windows would use `New-Item -ItemType SymbolicLink` or `mklink /J`. On Windows the managed route in `managed-launcher.md` is the measured one.
