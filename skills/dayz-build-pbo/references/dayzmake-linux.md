# Building and publishing on Linux

How to build, sign and publish a mod on Linux without DayZ Tools: dayzmake builds and signs the PBOs, the `workshop` uploader (the steam-workshop-uploader command line tool) publishes the folder, and `scripts/tools/dayz-linux/dayz-mod-pack.sh` ties the two together. The Windows route (AddonBuilder, DsUtils, Publisher, SteamCMD) is the rest of this skill and `workshop-publish.md`; the Proton setup is in `skills/_shared/linux-proton.md`.

This is Linux tool behaviour, measured with Proton for the DayZ Tools comparisons, not vanilla data. A PBO built, signed and verified this way loaded on a server with `-mod=@Mod` and `verifySignatures = 2` and its scripts ran, also on DayZ 1.30 stable. Not confirmed: the v3 against v2 signature check on a real client. The AutoTest mod (`skills/dayz-launch-test/assets/autotest-mod`) builds, signs and verifies this way with dayzmake 1.0.0 in `scripts/tools/dayz-linux/test_linux_helpers.py`.

## Get the right dayzmake

dayzmake is the DayZ fork of armake2, renamed at 1.0.0. It keeps adding functions only DayZ needs; the list is in `skills/_shared/linux-proton.md`, section "dayzmake, the DayZ fork of armake2" ("What the fork adds"). The original armake2 is no substitute: it is built for Arma (whether it fails on DayZ configs is not checked), and its v3 file hash leaves out `*.c` files, while dayzmake's includes them, so a changed script also changes the signed checksum.

Pin dayzmake 2.0.0 or later. 1.0.0 is enough only to build and sign your own sources: 2.0.0 adds entry name containment to `dayzmake unpack` (`safe_relative_path` and `crosses_symlink` in `src/pbo.rs`), and 1.0.0 has none (`src/pbo.rs:724` and `:731` to `:733`). Install the 2.0.0 release binary, or build the `v2.0.0` tag with `cargo install` (it needs `libssl-dev`).

```sh
dayzmake -h 2>&1 | grep -- --proton-binarize   # a hit means dayzmake; none means the original armake2
dayzmake --version                             # 2.0.0 or later; builds from before the rename print v0.3.0
```

The version string does not tell builds apart. When in doubt, reinstall from the tag, or binarize one textured model both ways and `cmp` the results. `dayz-mod-pack.sh` runs the same check: it uses `dayzmake` from `PATH` (or the binary named by `$DAYZMAKE`, or the older `$ARMAKE2`), falls back to a pre-rename `armake2`, refuses the original armake2 and warns below 1.0.0.

## Quick start

```sh
S=scripts/tools/dayz-linux/dayz-mod-pack.sh
$S init MyMod                 # folders, .gitignore, .workshopignore; --servermod sets the Server tag
$S keygen                     # secrets/MyMod.biprivatekey (never committed) and keys/MyMod.bikey
$S build                      # build/@MyMod/{addons,keys} plus mod.cpp and meta.cpp: the upload folder
$S build --binarize-models    # also .p3d and .rtm from MLOD to ODOL through BI binarize under Proton
$S check                      # no key in git, history or the upload folder; every signature verifies
$S publish-hint               # prints the workshop create and update commands; does not run them
```

- One `src/<Addon>/` per PBO. `ModName` becomes the key name (letters, digits, `_`), each addon's `$PREFIX$` defaults to its `src/<Addon>` folder name, and `-C <dir>` works on another project.
- The private key lives in `secrets/`, outside everything packed or uploaded. `build` stops if a key turns up in the content folder, `keygen` refuses unless `secrets/` is ignored by git (inside a git work tree) and never overwrites a key, and `check` fails if a `.biprivatekey` is tracked or anywhere in history.
- A key that reached git history or the Workshop is leaked. Rotate it under a new name (`MyMod_V2`) so old and new sit together in `keys/`.
- Do not commit `build/`.

## What `build` and `pack` do

| Input | `dayzmake build` | `dayzmake pack` |
|---|---|---|
| `config.cpp` (any `*.cpp`) | Preprocessed and rapified to `config.bin` | Copied as text |
| `*.rvmat` | Rapified | Copied |
| `*.p3d`, `*.rtm` | Copied as is on Linux (warning `non-windows-binarization`) unless `--proton-binarize` | Copied |
| `.c`, `.paa`, `.ogg`, `.wss` and the rest | Copied | Copied |

- Scripts always stay text.
- Textures must already be `.paa`: `dayzmake img2paa -t dxt5 -c in.png out_co.paa`, `-t dxt1` for opaque maps, power of two sizes, and `paa2img` to go back.
- `--no-bin` (`dayzmake pack`) ships `config.cpp` untouched; a `$NOBIN$` or `$NOBIN-NOTEST$` file turns binarizing off for one addon.
- `build` warns about textures and materials an MLOD names that are not in the addon (`missing-texture`, `missing-material`; `-w` silences them).

### `--proton-binarize`

It copies every `.p3d` and `.rtm` into a temporary sandbox and Wine prefix (your sources stay MLOD), runs BI's `binarize.exe` under Proton from a `P:` root with the addon mapped, builds, signs and deletes the sandbox. It finds DayZ Tools and Proton under the Steam root (`STEAM_ROOT`, `DAYZ_TOOLS` and `PROTON` override them) and fails with the binarize log when a model does not convert.

- **Texture alpha.** binarize resolves face texture paths from its current folder. Builds before 1.0.0 ran it from the `Binarize` folder, so it found no texture and printed nothing; the ODOL lost the section flags `0x802020` (IsAlpha, IsTransparent, IsAlphaFog) and the face colour fell back to the not-found default. From 1.0.0 the output for a cube with a DXT5 `_ca.paa` is byte identical to binarize run by hand from a `P:` root and to AddonBuilder's. Not checked in game.
- **Keep Wine's `Z:` small.** Run by hand, binarize walks the tree under `Z:` (the Linux root): it burned CPU for minutes listing a large home folder and a network mount, with or without the input file. Confined to a sandbox it took 3 seconds. A model without textures binarizes from any folder; with textures the current folder must be the `P:` root, and vanilla `dz\...` textures are found only when they exist under `P:`. `scripts/tools/dayz-linux/dayz-proton.sh binarize` and `skills/_shared/linux-proton.md`, section "The work drive on Linux", do this setup.
- On Windows dayzmake finds `binarize_x64.exe` through `HKCU\Software\Bohemia Interactive\binarize` and `build` binarizes in one go (not tested).

## Checking dayzmake against BI's tools

Run the same input through DayZ Tools under Proton (`dayz-proton.sh tool CfgConvert|DSSignFile|DSCheckSignatures`):

- Compare CfgConvert and dayzmake after `derapify`, not byte for byte: CfgConvert writes a 4-byte offset after every class body and dayzmake does not. The decoded configs are identical and the game loads both.
- The DS tools print nothing to Proton's console; redirect through `cmd /c ... > file`.
- A PBO edited by hand needs its SHA-1 trailer recomputed (`\0` plus `sha1(everything before it)`), or DSSignFile fails with "Stored and calculated hash don't match".

Builds from before 1.0.0 still have these faults, all fixed in 1.0.0: an unquoted string value swallowed the rest of the file; an already rapified `.rvmat` failed `build`; `#include "x.hpp"  // comment` failed; `#include` was case sensitive on Linux; a macro with the wrong argument count stayed unexpanded without a warning; `__EVAL` and `__EXEC` were not evaluated; cp1252 entry names crashed `inspect` and `unpack`; and `pack` of a file whose Linux name is not valid UTF-8 wrote a PBO that `inspect` and `unpack` refused with `failed to fill whole buffer`. On an older build, rename such a file first.

## Signatures

- `dayzmake keygen <path/Name>` writes `Name.biprivatekey` and `Name.bikey` (1024-bit RSA; the name is stored in both and in the signature's file name).
- `dayzmake sign <key.biprivatekey> <x.pbo>` writes `x.pbo.<KeyName>.bisign` beside the PBO in the same `addons/`. The default is v3; `--v2` writes the older form (`build --v2` in the script), only if v3 is rejected.
- `dayzmake verify <Name.bikey> <x.pbo> [sig]` exits 0 for a valid signature.
- For a PBO with `config.bin`, a `.c` script and an `.rvmat`, dayzmake's v3 `.bisign` was byte identical to `DSSignFile.exe`'s, and `DSCheckSignatures.exe -deep` reported it OK under Proton. For a negative control see `skills/dayz-launch-test/references/build-and-storage-traps.md`, "A signature check that cannot fail".
- Sign after the final build, and sign every PBO of a mod with one key so one `.bikey` covers them all.

What the three hashes cover (dayzmake 1.0.0, `src/pbo.rs:311` to `:322` and `:548` to `:563`; `src/sign.rs:109` to `:128`, `:157` to `:177`, `:197` to `:235`, `:475` to `:521` and `:749` to `:773`):

| Hash | Covers |
|---|---|
| `Hash 1` | The SHA-1 checksum stored in the PBO's trailer, which covers the headers and all entry bytes (`src/pbo.rs:311` to `:314` and `:548` to `:563`). |
| `Hash 2` | That checksum with the entry names and the prefix. |
| `Hash 3` | The v3 file hash, the whole stored content of the entries ending in `sqf`, `c`, `inc`, `bikb`, `ext`, `fsm`, `sqm`, `hpp`, `cfg`, `sqs` or `h` (the list at `src/sign.rs:157` to `:177`), with the names and the prefix. Other extensions such as `.paa` and `.p3d` are left out. |

`dayzmake verify` checks all three (`src/sign.rs:202` to `:234` and `:475` to `:521`). A PBO rebuilt with any change to its headers or entry bytes writes a new trailer, so it fails against an older `.bisign`. The trailer is read, not recomputed: a same-size byte change inside an entry outside the v3 hash, such as a `.paa`, made without rewriting the trailer keeps all three hashes and still verifies, since the name hash covers the non-empty entries and a same-size change keeps every entry's name and size. The same change in a `.c` entry fails on `Hash 3`. A changed header timestamp or a modified `.paa` with a recomputed trailer and the old `.bisign` is rejected. The controls where edits to uncovered entries still verified were run with Bohemia's `DSCheckSignatures`, in the same section of `skills/dayz-launch-test/references/build-and-storage-traps.md`.

## Other commands

```text
dayzmake rapify | derapify | preprocess [src [dst]]   config.cpp to and from config.bin; stdin and stdout without paths
dayzmake build | pack [-x glob] [-e k=v] [-k key] <dir> [pbo]
dayzmake inspect <pbo | model.p3d>   PBO: header extensions and files; MLOD: LODs, textures, materials, selections
dayzmake unpack <pbo> <dir>          header lands in $PBOPREFIX$; no -x; 2.0.0 or later for PBOs you did not build
dayzmake cat <pbo> <file> [dst]      one file; inner paths use \  ('scripts\5_Mission\x.c')
dayzmake img2paa | paa2img | binarize
```

Unpack a PBO you did not build only with 2.0.0 or later. In 1.0.0 `unpack` joins entry names without containment: `..\x` escapes the folder, an absolute name replaces the base and `--force` overwrites. On an older build, read every entry name first and unpack into a fresh empty folder (`skills/_shared/linux-proton.md`; the Linux extraction traps are in `skills/dayz-import-mod/references/extraction-pitfalls.md`).

Debugging: `dayzmake preprocess src/MyMod/config.cpp | less` shows what the parser sees, and `dayzmake cat Vanilla.pbo config.bin | dayzmake derapify` shows what an official PBO sets. `dayzmake inspect x.pbo` must show `prefix=<what config.cpp's script paths start with>`; with no `$PREFIX$` and no `-e`, the folder name becomes the prefix. `$PREFIX$` holds one line `MyMod`, or `key=value` lines, and `MyMod\Sub` for a nested prefix. The script adds `-e product=dayz` beside `prefix=`.

## The upload folder

Checked against the 438 items of a local `workshop/content/221100` folder and the strings of DayZ Tools' Publisher:

| File | In real Workshop items | Holds the app id | Written by |
|---|---|---|---|
| `addons/*.pbo` and `.bisign` | All; the Publisher refuses an upload without `addons/` at the root or with PBOs outside it | No | dayzmake |
| `keys/*.bikey` | Most; some server-only items have none | No | `keygen` |
| `mod.cpp` | 135 of 438 | No, in none | You, optionally |
| `meta.cpp` | 438 of 438 | No | The Publisher; `dayz-mod-pack.sh build` writes the same |

- The app id never goes into `mod.cpp`. The Publisher reads it from its own `steam_appid.txt` (221100); the `workshop` uploader takes `--app-id 221100` and keeps it in `workshop.toml`, which is never uploaded.
- `mod.cpp` is optional: 303 of 438 items ship none and the mod still works, and a local `-mod=` folder works without `meta.cpp` and `mod.cpp`. Fields seen, most common first: `name`, `overview`, `tooltip`, `action`, `author`, `picture`, `logo`, `logoSmall`, `logoOver`, `version`, `authorID`. `picture` and the `logo` fields are paths inside a PBO.
- `meta.cpp` is `protocol = 1; publishedid = <item id>; name = "<title>"; timestamp = <n>;`, where `timestamp` is .NET `DateTime.ToBinary()` of the UTC upload time, `(unix_seconds + 62135596800) * 10^7 + 2^62`.
- The official Windows tools upload `publishedid = 0` on a first publish. That does not work for DayZ clients (server mods are fine). The `workshop` uploader rewrites `meta.cpp` on every DayZ `create` and `update`, with the published id and a fresh timestamp, before uploading. Whether a client needs anything else from it is not tested.

## Workshop tags

Use exactly one type tag: `Mod` for a normal mod, `Server` for a server mod (`-servermod=`). Add any number of content tags: `Animation`, `Character`, `Economy`, `Environment`, `Equipment`, `Mechanics`, `Props`, `Sound`, `Terrain`, `Vehicle`, `Weapon`. Moderation sets `Tag Review`; never set it. There is no `servermod` or `Scenario` tag to use, and the Publisher refuses `Mod` with `Scenario`.

Of 434 items read through `ISteamRemoteStorage/GetPublishedFileDetails`, all carried `Mod` and 14 carried `Mod` with `Server`; those predate the one-type rule, so do not copy them. Not tested: whether both type tags at once, or none, is refused. The script keeps the tags as `WORKSHOP_TAGS="Mod Weapon"` in `.dayzmod`, `check` fails without exactly one type tag, and `publish-hint` turns them into `-t` options. `update` must send them again, because Steam drops tags that are not sent.

## Uploading with `workshop`

Steam must be running and signed in with an account that owns DayZ. An upload publishes to Steam and clients may cache it, so it is the user's decision: run `check`, look at the content folder, and never run `create` or `update` unasked.

```sh
workshop create --app-id 221100 --content build/@MyMod --title "My Mod" -t Mod \
    --ignore-file .workshopignore --glob '!*.biprivatekey' --visibility private -m "first upload"
cp build/@MyMod/workshop.toml workshop.toml && git add workshop.toml     # the item id is not secret
workshop --no-prompt update --content build/@MyMod --ignore-file .workshopignore --glob '!*.biprivatekey' -m "changelog"
```

- `workshop.toml` (`app_id`, `item_id`, `tags`) tells `update` which item to overwrite; it is never uploaded.
- The uploader stages a filtered copy that honours `.ignore` and `.gitignore`, `--ignore-file` and `--glob` (case sensitive; a leading `!` excludes). `--no-prompt` is a global option, so it goes before the subcommand.
- Start `private` or `unlisted`, check the item, then make it public in Steam.

## Traps

- A wrong or missing prefix loads the PBO but compiles none of its scripts, because `files[]` resolves against the prefix.
- `-servermod=` PBOs need no key on clients; `-mod=` PBOs do.
- `build` holds files in memory, so a very large asset mod needs the RAM to match.
- Before uploading, boot the result on a local server and compare the script module counts with vanilla (`skills/dayz-launch-test/references/linux-native-server.md`, "Read the result").

## What changes for `/dayz-build-pbo` on Linux

- Build with dayzmake (`build`, `keygen`, `sign`; version and install under "Get the right dayzmake"). `build --proton-binarize` runs BI binarize under Proton. The validation checks of this skill (prefix, `config.cpp`, `$PBOPREFIX$`, duplicates, stringtable) do not depend on the packer and apply unchanged.
- `--proton-binarize` keeps texture alpha from 1.0.0 on; older local builds lose it. Reinstall from the tag when in doubt, since a pre-rename build prints `v0.3.0` either way.
- To compare against BI's AddonBuilder, run it under Proton: `dayz-proton.sh tool AddonBuilder <P-root>/<Mod> <out> -prefix=<Mod>` (`-packonly`, full builds and `-clear` were measured). The rules in `addonbuilder-rules.md` hold: stage the mod in a folder that holds nothing else and build from there, never from `P:\<Mod>` or a path whose parent is a large Linux folder, because binarize scans the parent and stops on any broken `config.cpp` it finds. AddonBuilder exits 0 on a failed build; `dayz-proton.sh` returns the `[ResultCode]` from `DayZ Tools/Bin/Logs/AddonBuilder.rpt` instead.
- A mod with its own `build_*.ps1`, `robocopy` calls and junctions: read the script for the source tree, then do the same with `sh`, `rsync` and symlinks. Never run the `.ps1` under `pwsh`; it calls Windows programs and the registry.
- Publish with the `workshop` uploader instead of the Publisher; its options are in its own `--help`, and `dayz-mod-pack.sh publish-hint` prints the commands without running them.
- A PBO written as `@Mod/Addons/<Mod>.pbo` loads on both the native server and `DayZDiag`.
