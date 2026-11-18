# Vehicle build, packaging and debug after deploy

What changes between a packed-only and a binarized vehicle PBO: what `model.cfg` means for an ODOL against an MLOD, where the wheel spin direction lives, why drive letters in proxy paths are harmless, and how to check a vehicle PBO offline.

> Status: field notes measured on a third-party mod, the TestQuad (an imported Yamaha Banshee quad), in 2026-06. Those measurements were not repeated here. A citation written with its full `P:\` path was opened on the vanilla data of this repo. A citation without `P:\` keeps the line number the note was written with, for the DayZ build that entry names, and is not yet checked on `P:\`: Grep for the symbol before relying on the number. `[TestQuad ✓]` marks a fact verified against that mod's `config.cpp`, `model.cfg` and raw PBO bytes; the line numbers after it are lines of those files, not of vanilla files. `/dayz-build-pbo` is how this repo packs a mod; run `/dayz-preflight` before it.

## Vanilla anchors checked on `P:\`

- Vanilla picks each wheel's rotation animation in config the same way: `animRotation="wheelfrontleft"` at `P:\DZ\vehicles\wheeled\config.cpp:295`.
- Vanilla ships binarized and with no loose `model.cfg`: `P:\DZ\vehicles\wheeled\offroadhatchback\offroadhatchback.p3d` opens with the `ODOL` signature, version 56 (header read 2026-11-17), so section 2's baked reading applies to every vanilla car.

## Scope of these notes

> Packaging and debug lessons from shipping the **TestQuad** (imported Yamaha Banshee quad) to a
> dedicated server. These are the failures that PASS local filepatching and only surface on a
> dedicated box — the worst kind, because the dev loop never sees them.

> The white, untextured vehicle on a dedicated server (assets that only `config.cpp` references are
> left out of a binarized PBO) is in `symptom-white-vehicle.md`.
> "§1" below means that file; the sections here start at 2.

## 2. ODOL vs MLOD changes what `model.cfg` MEANS at runtime

This bites whenever animation/skeleton behavior is "fixed in model.cfg" but doesn't change in-game.

- **MLOD** `.p3d` (what packonly ships): the engine reads `model.cfg` from the PBO at runtime.
  Edits to animations/skeleton take effect on the next pack — no re-binarize needed.
- **ODOL** `.p3d` (binarized): `model.cfg` is **BAKED into the model** at binarize time. A loose
  `model.cfg` shipped next to an ODOL is **IGNORED** at runtime. Animation edits require a
  **RE-BINARIZE** to take effect.

**Trap:** a PBO can contain `config.bin` + ODOL `.p3d` **and** a loose `model.cfg` at the same time
(e.g. when you packonly a folder whose `.p3d` files were already binarized). The loose `model.cfg`
is residual and ignored — behavior comes from the ODOL. Do not trust the text file; read the baked
value out of the ODOL (§5). `[TestQuad ✓: shipped PBO had an ODOL body + a loose model.cfg carrying
the corrected angle; the wheel direction the engine used came from the ODOL bake, not the text.]`

## 3. Wheel spin direction lives in `model.cfg` rotation animations

Each wheel rotates via a `class Animations` entry: `type="rotation"`, `source="wheel<pos>"`,
`sourceAddress="loop"`, around the memory axis `wheel_X_X_axis`, mapping `angle0=0 → angle1="rad 360"`.
`[TestQuad ✓ model.cfg:80-92 wheelfrontleft + 3 siblings]`. `config.cpp` only picks WHICH animation each
wheel uses (`Axles → class Wheels → animRotation`), not the direction `[TestQuad ✓ config.cpp:467-519]`.

**Wheels spin backwards → flip the sign on all four:** `angle1 = "rad 360"` → `"rad -360"`.

Before flipping, **read the four `wheel_X_X_axis` memory points** (py3d, Memory LOD): if they are
uniform (e.g. all `(+1,0,0)`), every wheel spins the same way and the fix is symmetric — flip all
four. If one side's axis points the other way, the model is mirror-inconsistent and a blanket flip
will fix one side and break the other. `[TestQuad ✓: 4 axes all (+1,0,0) → uniform → flipped all four.]`

The change only reaches the game after a rebuild — and **re-binarize if the `.p3d` is ODOL** (§2).

## 4. Absolute drive paths in proxies (`P:\`, `Y:\`) are HARMLESS

Imported `.p3d` files routinely carry absolute proxy paths like `y:\testquad\testquad_wheel_front` or
`y:\dz\vehicles\wheeled\proxies\crew_driver` (a leftover of whatever drive the model was authored
on). The engine **strips the drive letter** and resolves the proxy by relative name against the
mounted PBOs — they load fine even when that drive does not exist on the machine.

`[TestQuad ✓: the working packonly PBO carried y:\ proxy paths; the Y: drive was not even mounted; the
four wheel proxies and both crew proxies loaded correctly in local test.]`

Do **NOT** chase proxy drive letters when debugging a white/untextured vehicle — that is §1. A drive
letter on a **texture or material** path (not a proxy) is a different story and IS worth fixing.

## 5. Verify a vehicle PBO offline (no game launch)

The PBO format is a flat header — for each entry, an asciiz filename then 5×`uint32`
(packing-method, original-size, reserved, timestamp, data-size) — followed by the concatenated file
data. A ~40-line Python parser gives you full offline verification:

- **Completeness** — list entries, diff against the mod folder. Catches §1 (config-only assets
  missing). `0 missing` is the gate before distribution.
- **Build mode** — `config.bin` + `ODOL` magic on the body `.p3d` = binarized; `config.cpp` + `MLOD`
  = packonly. Tells you which §2 semantics apply.
- **Baked wheel angle** — extract the body `.p3d` entry (raw slice at its data offset) and scan the
  bytes for float32 `±2π` (`rad ±360` = `±6.28319`). `−2π ×4` and `+2π ×0` confirms the wheel-spin
  fix is in the MODEL, not just the loose model.cfg (§2/§3).
- **Stray absolute paths** — scan text/model entries for `[A-Za-z]:\`. Proxy drives are noise (§4);
  a drive letter inside a `.rvmat` texture path or the body's material table is a real defect.

`[TestQuad ✓: this exact offline workflow caught the 26 missing assets, distinguished the 5.4 MB
binarized (broken) PBO from the 18 MB packonly (complete) one, and confirmed the −360 wheel bake —
all without launching DayZ.]`

No such parser ships in this repo: write it from the format above.
