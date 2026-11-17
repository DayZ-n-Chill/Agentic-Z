# Building, signing and publishing a mod with dayzmake and `workshop` (Linux, no DayZ Tools)

Turn a source tree into a Workshop-ready folder without Windows: **dayzmake** builds and signs the PBOs,
**`workshop`** (the steam-workshop-uploader command-line tool) uploads the folder, and
`skills/_shared/scripts/dayz-mod-pack.sh` wires the two together. The Windows route (AddonBuilder, DsUtils,
Publisher, SteamCMD) is the rest of this skill and `workshop-publish.md`.

Not checkable on `P:\`: this is Linux tool behaviour, measured on Debian, with Proton Hotfix for the DayZ Tools
comparisons. End to end, a PBO built, signed and verified this way loaded
on a server with `-mod=@Mod` and `verifySignatures = 2`, and its scripts ran, also on DayZ 1.30 stable (build
not recorded). Not verified: the v3-against-v2 signature check on a real client. The AutoTest mod
(`skills/dayz-test-ingame/assets/autotest-mod`) builds, signs and verifies with this flow and dayzmake 1.0.0 in
`skills/_shared/scripts/test_linux_helpers.py`.

## Get the right dayzmake

dayzmake is the DayZ fork of armake2, renamed at `v1.0.0`. **The original armake2's
V3 file hash omits `*.c` files** (dayzmake's includes them; a changed script also changes the signed PBO checksum), and it fails on
DayZ configs. dayzmake keeps moving away from armake2 on purpose, with functions only DayZ
needs or needs differently from Arma; what it adds so far is listed in `skills/_shared/linux-proton.md`, section 1. Use dayzmake >= 2.0.0, pinned (or >= 1.0.0 if you only build/sign your own sources and never run `dayzmake unpack` on third-party PBOs: `v2.0.0`, commit `f31056ae`, adds entry-name containment in `src/pbo.rs` `safe_relative_path`/`crosses_symlink` and skips unsafe entries, whereas `v1.0.0` `src/pbo.rs:724,731-733` has none). Install the `v2.0.0` release binary, or build the `v2.0.0` tag from its source with `cargo install` (needs `libssl-dev`).

```sh
dayzmake -h 2>&1 | grep -- --proton-binarize   # a hit = dayzmake; none = the original armake2, do not use
dayzmake --version                             # >= v2.0.0 (v1.x ok for building only); pre-rename builds print v0.3.0
```

The version string does not tell builds apart. If in doubt, reinstall from the tag, or binarize one textured model
both ways and `cmp` the results. `dayz-mod-pack.sh` runs the same check: it uses `dayzmake` from `PATH`
(or the binary named by `$DAYZMAKE`, or the older `$ARMAKE2`), falls back to a pre-rename `armake2`, refuses the original armake2 and warns below 1.0.0.

## Quick start (`dayz-mod-pack.sh`)

```sh
S=skills/_shared/scripts/dayz-mod-pack.sh
$S init MyMod                 # folders, .gitignore, .workshopignore; --servermod sets the Server tag
$S keygen                     # secrets/MyMod.biprivatekey (never committed) + keys/MyMod.bikey (public)
$S build                      # build/@MyMod/{addons,keys} (+ mod.cpp, meta.cpp): the upload folder
$S build --binarize-models    # also .p3d/.rtm MLOD -> ODOL through BI binarize under Proton
$S check                      # no key in git, history or the upload folder; every signature verifies
$S publish-hint               # prints the `workshop create|update` commands; does not run them
```

One `src/<Addon>/` per PBO; `ModName` becomes the key name (letters, digits, `_`); each addon's `$PREFIX$` defaults to its `src/<Addon>` folder name; `-C <dir>`
works on another project. The private key lives in `secrets/`, outside everything that is packed or
uploaded: `build` aborts if one turns up in the content folder, `keygen` refuses unless `secrets/` is git-ignored (when the
project is inside a git work tree) and never overwrites a key, and `check` fails if a `.biprivatekey` is tracked or anywhere in history. A key that reached
git history or the Workshop is leaked: rotate it under a new name (`MyMod_V2`) so old and new coexist in `keys/`.
Do not commit `build/`. `dayzmake verify` recomputes the three hashes and compares them with the `.bisign`: `Hash 1` is the SHA-1 checksum stored in the PBO's trailer, `Hash 2` hashes it with the entry names and the prefix, and `Hash 3` hashes the v3 file hash (the content of the entries ending in `sqf`, `c`, `inc`, `bikb`, `ext`, `fsm`, `sqm`, `hpp`, `cfg`, `sqs` or `h`) with the names and the prefix. A PBO rebuilt with any change to its headers or entry bytes writes a new trailer, so it fails against an older `.bisign`. The trailer is read, not recomputed: a same-size byte change inside an entry outside the v3 file hash, such as a `.paa`, made without rewriting the trailer keeps all three hashes and still verifies (the name hash covers the non-empty entries, and a same-size change keeps every entry's name and size); the same change in a `.c` entry fails on `Hash 3` (dayzmake v1.0.0 `src/pbo.rs:311-322,548-563`, `src/sign.rs:109-128,157-177,197-235,475-521,749-773`).

## What `build` and `pack` do

| Input | `dayzmake build` | `dayzmake pack` |
|---|---|---|
| `config.cpp` (any `*.cpp`) | preprocessed, rapified to `config.bin` | copied as text |
| `*.rvmat` | rapified | copied |
| `*.p3d`, `*.rtm` | copied as-is on Linux (warning `non-windows-binarization`) unless `--proton-binarize` | copied |
| `.c`, `.paa`, `.ogg`, `.wss`, ... | copied | copied |

Scripts always stay text. Textures must already be `.paa`:
`dayzmake img2paa -t dxt5 -c in.png out_co.paa` (`-t dxt1` for opaque maps, power-of-two sizes; `paa2img` back;
measured with v1.0.0). `--no-bin` (`dayzmake pack`) ships `config.cpp` untouched; a `$NOBIN$` or
`$NOBIN-NOTEST$` file disables binarization for one addon. `build` also warns about textures and materials an MLOD
references that are not in the addon (`missing-texture`, `missing-material`; `-w` silences).

### `--proton-binarize`

It copies every `.p3d`/`.rtm` into a temporary sandbox and Wine prefix (your sources stay MLOD), runs BI's
`binarize.exe` under Proton from a `P:` root with the addon mapped, builds, signs and deletes the sandbox. It finds DayZ
Tools and Proton under the Steam root (`STEAM_ROOT`, `DAYZ_TOOLS`, `PROTON` override) and fails with the binarize log
if a model does not convert.

- **Texture alpha.** binarize resolves face texture paths relative to its current directory. dayzmake builds before
  commit `0a0ce3b` ran it from the `Binarize` folder, so no texture was found and nothing was printed: the ODOL lost the
  section flags `0x802020` (IsAlpha|IsTransparent|IsAlphaFog) and the face colour fell back to the not-found default
  (binarize 1.30.164200.56). From commit `7dcb3cf` (in `v1.0.0`) the output for a cube with a DXT5 `_ca.paa` is
  byte-identical to binarize run by hand from a `P:` root and to AddonBuilder's (binarize 1.30.164289.70).
  Not checked in game.
- **Keep Wine's `Z:` tiny.** Run by hand, binarize walks the tree under `Z:` (= `/`): it burned CPU for minutes
  listing `~/.cargo` and a CIFS mount, with or without the input file. Confined to a sandbox it took 3 s, exit 0. A
  model without textures binarizes from any directory (a hand-made MLOD triangle came out as ODOL); with textures the
  current directory must be the `P:` root, and vanilla `dz\...` textures are only found if they exist under `P:`.
  `skills/_shared/scripts/dayz-proton.sh binarize` and `skills/_shared/linux-proton.md` section 3 do this setup.
- On Windows dayzmake finds `binarize_x64.exe` through `HKCU\Software\Bohemia Interactive\binarize` and `build`
  binarizes in one go (not tested).

### Checking dayzmake against BI's own tools

Run the same input through DayZ Tools under Proton (`dayz-proton.sh tool CfgConvert|DSSignFile|DSCheckSignatures`):

- Compare CfgConvert and dayzmake **after `derapify`**, not byte for byte: CfgConvert writes a 4-byte offset after
  every class body and dayzmake does not. The decoded configs are identical and the game loads both.
- The DS tools print nothing on Proton's console; redirect through `cmd /c ... > file`.
- A PBO edited by hand needs its SHA-1 trailer recomputed (`\0` + `sha1(everything before it)`), or DSSignFile fails
  with "Stored and calculated hash don't match".

Bugs found against CfgConvert and fixed in `v1.0.0`, so a pre-rename build still has them: an unquoted string value
swallowed the rest of the file; an already-rapified
`.rvmat` failed `build`; `#include "x.hpp"  // comment` failed; `#include` was case-sensitive on
Linux; a macro with the wrong argument count stayed unexpanded silently;
`__EVAL`/`__EXEC` were not evaluated; cp1252 entry names crashed `inspect`/`unpack`.
Also fixed in 1.0.0: `pack` of a file whose Linux name is not valid UTF-8 wrote
a PBO that `inspect`/`unpack` refused with `failed to fill whole buffer`; older builds need such a file renamed first.

## Signatures

- `dayzmake keygen <path/Name>` writes `Name.biprivatekey` and `Name.bikey` (1024-bit RSA; the name is stored in both
  and in the signature's file name).
- `dayzmake sign <key.biprivatekey> <x.pbo>` writes `x.pbo.<KeyName>.bisign` beside the PBO, in the same `addons/`.
  Default is **v3**; `--v2` writes the older form (`build --v2` in the script), only if v3 is rejected.
- `dayzmake verify <Name.bikey> <x.pbo> [sig]` exits 0 for a valid signature.
- For a PBO with `config.bin`, a `.c` script and an rvmat, dayzmake's v3 `.bisign` was **byte-identical** to
  `DSSignFile.exe`'s, and `DSCheckSignatures.exe -deep` reported it OK (under Proton). For a negative
  control see `skills/dayz-test-ingame/references/build-and-storage-traps.md`, "A signature negative control that cannot fail".
- Sign after the final build. In v3 signatures, the v3 file hash (`Hash 3`) selects entries by extension (`sqf`, `c`, `inc`, `bikb`, `ext`, `fsm`, `sqm`, `hpp`, `cfg`, `sqs`, `h` in dayzmake v1.0.0 `src/sign.rs:157-177`) and hashes each selected entry's whole stored content, omitting other extensions such as `.paa` or `.p3d`, while `Hash 1` signs the PBO's SHA-1 checksum over headers and all entry bytes (`src/pbo.rs:311-314,548-563`). `dayzmake verify` (`src/sign.rs:202-234,475-521`) checks `Hash 1`, `Hash 2` and `Hash 3`, so a changed header timestamp or modified `.paa` with a recomputed PBO trailer and the old `.bisign` is rejected by `dayzmake verify`; the negative controls where edits to uncovered entries still verified were run with Bohemia's `DSCheckSignatures` (same section of `build-and-storage-traps.md`). Sign every PBO of a mod with one key, so one `.bikey` covers all.

## Other commands

```
dayzmake rapify | derapify | preprocess [src [dst]]   config.cpp <-> config.bin; stdin/stdout without paths
dayzmake build | pack [-x glob] [-e k=v] [-k key] <dir> [pbo]
dayzmake inspect <pbo | model.p3d>   PBO: header extensions + files; MLOD: LODs, textures, materials, selections
dayzmake unpack <pbo> <dir>          header lands in $PBOPREFIX$; no -x; require >= v2.0.0 for third-party PBOs
dayzmake cat <pbo> <file> [dst]      one file; inner paths use \  ('scripts\5_Mission\x.c')
dayzmake img2paa | paa2img | binarize
```

Unpacking any PBO you did not build yourself requires dayzmake >= `v2.0.0` (tag `v2.0.0`, commit `f31056ae`; `src/pbo.rs` `safe_relative_path` and `crosses_symlink` validate relative paths and skip unsafe entries). In `v1.0.0` (`src/pbo.rs:724,731-733`) `unpack` joins entry names without containment (`..\x` escapes, an absolute name replaces the base, `--force` overwrites); on < `v2.0.0` inspect all entry names first into a fresh empty directory (`skills/dayz-pbo-reverse-engineering/references/linux.md`).

Debug recipes: `dayzmake preprocess src/MyMod/config.cpp | less` shows what the parser sees;
`dayzmake cat Vanilla.pbo config.bin | dayzmake derapify` shows what an official PBO set; `dayzmake inspect x.pbo` must
show `prefix=<what config.cpp's script paths start with>`, and with no `$PREFIX$`/`-e` the folder name becomes the
prefix. `$PREFIX$` holds one line `MyMod`, or `key=value` lines; `MyMod\Sub` for nested prefixes. The script adds
`-e product=dayz` beside `prefix=`.

## The upload folder: `mod.cpp`, `meta.cpp` and the app id

Checked against the 438 items of a local `workshop/content/221100` and the strings of DayZ Tools' Publisher:

| File | In real Workshop items | Holds the app id? | Written by |
|---|---|---|---|
| `addons/*.pbo` + `.bisign` | all; the Publisher refuses an upload without `addons/` at the root or with PBOs outside it | no | dayzmake |
| `keys/*.bikey` | most (some server-only items have none) | no | `keygen` |
| `mod.cpp` | 135 of 438 | **no, in none** | you, optionally |
| `meta.cpp` | 438 of 438 | **no** | the Publisher; `dayz-mod-pack.sh build` mirrors it |

- **The app id does not go into `mod.cpp`.** The Publisher reads it from its own `steam_appid.txt` (221100); the
  `workshop` uploader takes `--app-id 221100` and keeps it in `workshop.toml`, which is never uploaded.
- `mod.cpp` is optional: 303 of 438 items ship none, a mod works without it (build not
  recorded), and a locally loaded `-mod=` folder works without `meta.cpp` and `mod.cpp`. Fields seen, most common
  first: `name`, `overview`, `tooltip`, `action`, `author`, `picture`, `logo`, `logoSmall`, `logoOver`, `version`,
  `authorID`. `picture`/`logo*` are paths inside a PBO.
- `meta.cpp` is `protocol = 1; publishedid = <item id>; name = "<title>"; timestamp = <n>;`, where `timestamp` is .NET
  `DateTime.ToBinary()` of the UTC upload time, `(unix_seconds + 62135596800) * 10^7 + 2^62`.
- The official Windows tools upload `publishedid = 0` on a first publish. That **does not work for DayZ clients**
  (server mods are fine). The `workshop` uploader rewrites `meta.cpp` on every DayZ `create` and `update`
  (publishedid, fresh timestamp) before uploading. Whether a client needs anything else from it
  was not tested.

## Workshop tags

Exactly one **type** tag: `Mod` for a normal mod, `Server` for a servermod (`-servermod=`). Any number
of **content** tags: `Animation`, `Character`, `Economy`, `Environment`, `Equipment`, `Mechanics`, `Props`, `Sound`,
`Terrain`, `Vehicle`, `Weapon`. `Tag Review` is set by moderation; never set it. There is no `servermod` or
`Scenario` tag to use (the Publisher refuses `Mod` with `Scenario`). Of 434 items read through
`ISteamRemoteStorage/GetPublishedFileDetails`, all carried `Mod` and 14 carried `Mod` with `Server`; that predates the
rule, do not copy it. Not tested: whether both type tags at once, or none, is refused. The script keeps them as
`WORKSHOP_TAGS="Mod Weapon"` in `.dayzmod`; `check` fails without exactly one type tag; `publish-hint` turns them into
`-t` options. `update` must resend them, because Steam drops tags that are not sent.

## Uploading with `workshop`

Steam must be running and logged in with an account that owns DayZ. Uploading publishes to Steam and
may be cached by clients: it is the user's decision, so run `check`, look at the content folder, and never run
`create`/`update` unprompted.

```sh
workshop create --app-id 221100 --content build/@MyMod --title "My Mod" -t Mod \
    --ignore-file .workshopignore --glob '!*.biprivatekey' --visibility private -m "first upload"
cp build/@MyMod/workshop.toml workshop.toml && git add workshop.toml     # the item id is not secret
workshop --no-prompt update --content build/@MyMod --ignore-file .workshopignore --glob '!*.biprivatekey' -m "changelog"
```

- `workshop.toml` (`app_id`, `item_id`, `tags`) tells `update` which item to overwrite; it is never uploaded.
- The uploader stages a filtered copy honouring `.ignore`/`.gitignore`, `--ignore-file` and `--glob` (case-sensitive,
  a leading `!` excludes). `--no-prompt` is a global option, so it goes before the subcommand.
- Start `private` (or `unlisted`), check the item, then make it public in Steam.

## Pitfalls

A wrong or missing prefix loads the PBO but compiles none of its scripts (`files[]` resolves against the
prefix). `-servermod=` PBOs need no key on clients; `-mod=` PBOs do. `build` holds files in memory, so very large asset
mods need RAM to match. Before uploading, boot the result on a local server and compare script module counts with
vanilla (`skills/dayz-test-ingame/references/linux-native-server.md`, section 4).

## What changes on Linux for `/dayz-build-pbo`

The rest of `/dayz-build-pbo` is the Windows workflow and stays valid there. On Linux, the Proton setup, the measured tool matrix and the pitfalls are in `skills/_shared/linux-proton.md`; this section only says what changes for this skill.

- Build with dayzmake (version and install: "Get the right dayzmake" above): use `dayzmake build`, `keygen` and `sign`. The original armake2 is no substitute: it is built for Arma, its V3 file hash omits `*.c` files and it lacks the DayZ-only functions dayzmake keeps adding. `build --proton-binarize` invokes BI binarize under Proton. `skills/_shared/scripts/dayz-mod-pack.sh` wraps keygen, build, sign, check and the Workshop upload commands; the whole Linux route (signatures, `meta.cpp`, tags, `workshop` uploader) is in the sections above. The validation checks of this skill (prefix, `config.cpp`, `$PBOPREFIX$`, duplicates, stringtable) do not depend on the packer and apply unchanged.
- `--proton-binarize` keeps texture alpha from commit `0a0ce3b` on, which `v1.0.0` contains; older local builds lose it. Reinstall from the tag when in doubt: a pre-rename build prints `v0.3.0` either way.
- To compare against BI's AddonBuilder, it runs under Proton: `dayz-proton.sh tool AddonBuilder <P-root>/<Mod> <out> -prefix=<Mod>` (`-packonly` and full builds measured, `-clear` too). The binarize rules in `addonbuilder-rules.md` hold: build from `P:\<Mod>`, never from a path whose parent is a large Linux directory, because binarize scans the parent. AddonBuilder exits 0 on a failed build; `dayz-proton.sh` returns the `[ResultCode]` from `DayZ Tools/Bin/Logs/AddonBuilder.rpt` instead.
- A mod with its own `build_*.ps1`, `robocopy` calls and junctions: read the script for the source tree, then do the same with `sh`, `rsync` and symlinks. Do not run the `.ps1` under `pwsh`: it calls Windows programs and the registry.
- Publishing: the `workshop` uploader by itself instead of Publisher, its command left to its own `--help`; `skills/_shared/scripts/dayz-mod-pack.sh publish-hint` prints the commands and does not run them.
- dayz-mcp on a Linux host: `dayz_test_run build=true` drives the pinned dayzmake `v1.0.0` release binary from `PATH` and refuses any other build (`dayzmake_pin_mismatch`). It writes `@Mod/Addons/<Mod>.pbo`; both the native server and `DayZDiag` load that spelling. Managed binarization with assets is not verified.
