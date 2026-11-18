# GTA V rip intake

How to read a GTA V vehicle mod archive offline, what its skeleton names map to in DayZ, and why bone names and exclusion lists must be checked against the real mesh pieces.

Nothing in GTA's formats can be checked on `P:\`; what follows was measured on one third-party helicopter rip (an HH-60G) with third-party tools (**tool knowledge**). The one vanilla link is the glass: a ripped vehicle's panes take a vanilla glass material such as the `niva_glass` one the hatchback door uses (`P:\DZ\vehicles\wheeled\config.cpp:942`).

## Reading the archive

Mod archives (`dlc.rpf`) built with OpenIV are usually not encrypted and can be read fully offline, with no GTA V install and no keys. Check the encryption dword at offset 12 of the RPF7 header first: `0x4E45504F` ("OPEN") means unencrypted.

| Part | Layout |
|---|---|
| Header | 16 bytes: `7FPR` magic, entry count, names length, encryption |
| Entry | 16 bytes; the second dword tells the kind: `0x7FFFFF00` is a folder, high bit set is a resource, otherwise a plain file |
| Offsets | In 512-byte sectors |
| Plain file of size 0 | Stored as is, usually a nested `.rpf`; recurse into it in place |
| Resource | A 16-byte RSC7 header in the clear (magic `RSC7`, version 162 for `.yft` and 13 for `.ytd`, system flags, graphics flags), then raw deflate from byte 16 (`zlib` with `wbits=-15`) |

A standalone `.yft` or `.ytd` is exactly that byte range, so extracting one is a copy, not a re-encode.

## What the skeleton names tell you

A string scan of the decompressed payload is enough; no fragment parsing is needed. Typical names:

- Rotors in three states, `rotor_main`, `rotor_main_slow`, `rotor_main_fast`, and the same for `rotor_rear`: a direct match for DayZ's static and blurred rotor pattern.
- Doors `door_dside_f`, `door_pside_r` and so on, with `handle_*`.
- Glass as its own bones (`windscreen`, `window_*`), which gives a glass list for free.
- `seat_dside_*`, `seat_pside_*`, `wheel_lf`, `wheel_rf`, `wheel_lr`, and `gear_*` including `gear_door_*`.
- Guns and turrets as separate bones (`turret_*`, `weapon_*`), easy to leave out of a first version.

These are names, not pieces. On the HH-60G, `handle_dside_f`, `handle_pside_f`, `handle_dside_r` and `handle_pside_r` are bones in the skeleton but exist in no LOD of the `.yft` and no mesh of the imported Blender file. Intersect the name list with the mesh list per LOD before routing anything. "The export lost a piece" and "the export named a piece that never existed" look the same from a silent `if obj_by_name(n)` skip, and need opposite fixes: go find it, or delete the row.

## Importing into Blender

Sollumz 2.8.3 imports a binary `.yft` directly through PyMateria (Windows only) on Blender 4.0 to 5.1. CodeWalker asks for a GTA V game folder on first run, so for an unencrypted rip use your own extractor and the Sollumz binary import, and keep CodeWalker as a fallback.

- PyMateria's native `.pyd` fails to load from a long path ("DLL load failed ... filename too long"). Install Sollumz into a short, separate Blender profile by setting `BLENDER_USER_RESOURCES` to a short folder; this also leaves the user's own Blender alone. Headless install: `bpy.ops.extensions.package_install_files(repo="user_default", enable_on_install=True)`, then the add-on's `dependencies.install_dependencies(online_access_override=True, optional_dependencies_to_install={"pymateria"})`.
- The `.yft` does not carry its textures; they are in the sibling `.ytd`. Sollumz's `gta5.try_load_asset` returns `None` for a `.ytd`, and its `.yft` import wires 47 named but empty image nodes. Use the raw binding instead: `pmg8 = szio.gta5.native.provider_gen8.pmg8`, `td = pmg8.TextureDictionary.import_rsc(Path(ytd)).result`, then `tex.export_dds(path)` for each item of `td.textures`.
- Shared base game textures (`vehicle_generic_*`) live in GTA's `vehshare.ytd`, not in the mod, and stay pink in Blender. They do not matter for DayZ: glass gets a vanilla `.rvmat`, and the rest are secondary detail layers.

## Exclusions are literal names

A first version of the HH-60G excluded parts with the pattern `^(mod_[a-z0-9]+|turret_|weapon_|siren\d|extra_\d|hbgrip_)`. It also caught `mod_n` (31,598 triangles: the whole nose, with refuelling probe, rescue hoist, radome and nose pods) and `mod_s` (52,550 triangles: the entire interior, seats included). The vehicle shipped with no nose and a hollow cabin, 94,084 triangles or 38 percent of the source gone, with no warning, and only a full in-game look showed it.

Write the exclusion list as literal names, each with one line saying why; never a pattern. A pattern classifies pieces nobody has looked at, and a literal list forces you to look.

Cheap offline checks that catch both failures:

- The source is the measured piece set of the richest LOD (on the HH-60G, 49 pieces in `hh60g.yft` High, identical to `hh60g_hi.yft` VeryHigh).
- Every source piece appears exactly once, either in a routing group or in the exclusion list; compare the sets, not the totals.
- Every routed name is in the source.
- A missing piece is an error, never a skip.
