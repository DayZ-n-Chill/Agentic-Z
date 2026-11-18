# Vehicle packaging and offline PBO checks

How a packed only vehicle PBO differs from a binarized one: what `model.cfg` means for an ODOL and an MLOD, where wheel spin direction lives, why drive letters in proxy paths do no harm, and how to check a vehicle PBO without starting the game.

The results were measured on an imported quad bike shipped to a dedicated server; they are mod behaviour, not vanilla. These faults pass local file patching and show only on a dedicated server. `/dayz-build-pbo` packs a mod in this repo; run `/dayz-preflight` before it. A vehicle that turns white or untextured on a dedicated server is covered in `binarize-dropped-textures.md`.

## What vanilla shows

- Vanilla picks each wheel's rotation animation in config: `animRotation="wheelfrontleft"` (`P:\DZ\vehicles\wheeled\config.cpp:295`).
- Vanilla ships binarized models with no loose `model.cfg`: `P:\DZ\vehicles\wheeled\offroadhatchback\offroadhatchback.p3d` starts with the `ODOL` signature, version 56, so the baked reading below applies to every vanilla car.

## ODOL and MLOD read model.cfg differently

This matters whenever an animation or skeleton fix in `model.cfg` makes no difference in game.

| Model | When `model.cfg` is read | To change an animation |
|---|---|---|
| MLOD, shipped by a packed only build | From the PBO at runtime | Pack again |
| ODOL, binarized | Baked into the model at binarize time; a loose `model.cfg` beside it is ignored | Binarize again |

A PBO can hold `config.bin`, an ODOL `.p3d` and a loose `model.cfg` at once, for example when you pack a folder whose models were already binarized. The loose `model.cfg` is a leftover and does nothing; behaviour comes from the ODOL. Read the baked value from the ODOL (see "Check a vehicle PBO offline") instead of trusting the text. On the quad, the shipped PBO held an ODOL body and a loose `model.cfg` with the corrected wheel angle, and the wheels followed the ODOL.

## Wheel spin direction lives in model.cfg

Each wheel turns through an entry in `class Animations`: `type="rotation"`, `source="wheel<pos>"`, `sourceAddress="loop"`, about the memory axis `wheel_X_X_axis`, from `angle0=0` to `angle1="rad 360"`. `config.cpp` only picks which animation each wheel uses (`Axles`, then `class Wheels`, then `animRotation`), not the direction.

When the wheels spin backwards, flip the sign on all four: `angle1 = "rad -360"`. Before you flip, read the four `wheel_X_X_axis` points in the Memory LOD with py3d. If they all match, for example all `(+1,0,0)`, every wheel turns the same way and flipping all four is right. If one side's axis points the other way, the model is mirrored inconsistently and a blanket flip fixes one side and breaks the other. Whether the result is right is checked offline in `animation-sign-and-axis.md`.

The change reaches the game only after a rebuild, and after a new binarize if the `.p3d` is ODOL.

## Drive letters in proxy paths do no harm

Imported models often carry absolute proxy paths such as `y:\mymod\mymod_wheel_front` or `y:\dz\vehicles\wheeled\proxies\crew_driver`, left from the drive the model was made on. The engine drops the drive letter and finds the proxy by its relative name in the loaded PBOs, so they load even when that drive does not exist. On the quad, a packed only PBO with `y:\` proxy paths loaded its four wheel proxies and both crew proxies with no Y: drive mounted.

Do not chase proxy drive letters when a vehicle renders white; see `binarize-dropped-textures.md`. A drive letter in a texture or material path, not a proxy, is a real fault and worth fixing.

## Check a vehicle PBO offline

A PBO is a flat header, then the file data end to end. For each entry the header holds a zero terminated file name and five `uint32` values: packing method, original size, reserved, timestamp, data size. A parser of about 40 lines of Python covers:

| Check | How | Catches |
|---|---|---|
| Completeness | List the entries and compare with the mod folder; zero missing before release | Assets only `config.cpp` names, left out of a binarized PBO |
| Build mode | `config.bin` and an `ODOL` body means binarized; `config.cpp` and `MLOD` means packed only | Which `model.cfg` reading applies |
| Baked wheel angle | Slice the body `.p3d` at its data offset and search for float32 plus or minus 2 pi (`rad 360` is `6.28319`) | Four `-2 pi` and no `+2 pi` confirms the fix is in the model, not only the loose `model.cfg` |
| Stray drive letters | Search text and model entries for `[A-Za-z]:\` | Proxy drives are noise; a drive letter in a `.rvmat` texture path or the body's material table is a real fault |

On the quad this found 26 missing assets, told the broken 5.4 MB binarized PBO from the complete 18 MB packed only one, and confirmed the `-360` wheel bake, all without starting DayZ. No such parser ships in this repo: write it from the format above.
