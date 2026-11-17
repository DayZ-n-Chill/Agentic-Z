---
name: dayz-proxy-align
description: "Reads every proxy of an MLOD host .p3d, shows them in a browser editor against the worn clothing, rewrites them as unambiguous triangles and writes them back with py3d, leaving the rest of the model as it was. Use when attached clothing or an attached item shows at the floor, floats, clips or comes out rotated, when a dressable mannequin or a crew seat needs its proxies placed, or the user asks to align a proxy, fix proxy orientation, or sort out worn against ground models (_m vs _g). Spanish trigger a user might type: ropa al suelo. Not for general LOD or memory point edits (dayz-p3d-inspector) or for clothing meshes and weights (dayz-clothing)."
argument-hint: "<host.p3d> [<aligned.p3d>] [--rot Slot=AXIS:DEG ...] [--map Slot=<item> ...]"
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-proxy-align

A proxy is a named selection `proxy:\path\to\model.NNN` over one tiny triangle in a visual LOD. The triangle sets where the other model sits and which way it faces, and the engine reads it by its angles, not by its vertex order. When the triangle is ambiguous or misplaced, the attached clothing or item renders at the floor, floating or rotated.

This skill replaces trial and error with numbers. It loads the host model and every proxy, lets you move and rotate each anchor against the real worn clothing, and writes the edited triangles straight back into the MLOD with py3d.

Follow `skills/_shared/dayz-conventions.md`. Only `worn_overlay.py` reads vanilla data: it runs `/dayz-preflight` first when its `--dz` folder is on `P:\` (the default) and stops if that fails. The other scripts read and write only the files you pass.

## When to use it

Misplaced or turned proxies on any host model. The most common host is a dressable static object: a mannequin or an armor rack, an `Inventory_Base` or `Container_Base` item whose model embeds the vanilla `\dz\characters\proxies\*_dz` proxies and whose config lists clothing slots in `attachments[]`. The same steps fix crew seats, weapon attachment proxies and body-part proxies; what differs for each is in `skills/_shared/models/proxy-frames.md`.

The host must be an MLOD file, the `.p3d` Object Builder saves. A binarized host has to be converted outside Agentic-Z first.

## What it needs

Run these from the repository root (`<skill-dir>\..\..`):

```cmd
python -m pip install -e scripts/tools/py3d
python -m pip install numpy
python -c "import py3d; assert getattr(py3d,'IS_DAYZ_FORK',False) and tuple(map(int,py3d.__version__.split('.')))>=(1,6,0), (py3d.__version__, py3d.__file__)"
```

- py3d here is the DayZ fork in `scripts/tools/py3d`, version 1.6.0 or later. The last line fails when another py3d imports instead.
- Do not run `pip install py3d`: the PyPI package of that name is a point cloud library. Upstream KoffeinFlummi py3d uses the same import name and lacks the proxy functions and write guards; uninstall either one first (`python -m pip uninstall py3d`).
- When a built wheel of the fork is at hand instead of the source folder, `python "<skill-dir>\scripts\install_py3d.py"` installs it. It looks in `<skill-dir>\wheels\`, then in `scripts\tools\py3d\dist\`, and stops without changing anything when no wheel or more than one is there, when a legacy `py3d-*.whl` sits beside it, or when the py3d already installed is not the fork. Agentic-Z ships no wheel.
- `worn_overlay.py` shows vanilla worn clothing, and vanilla worn models are binarized (`P:\DZ\characters\vests\plate_carrier_m.p3d` starts with `ODOL`). It needs an external ODOL to MLOD backend, a folder holding `odol_reader.py` and `odol_to_mlod.py`, passed with `--odol-backend` or set in `DAYZ_ODOL_BACKEND_ROOT`. Agentic-Z ships none; it is the same backend the tool in `scripts/tools/dayz-odol-strict` expects. Without it, skip the overlay: the other steps work without it.
- The editor page loads Three.js 0.185.1 from the jsDelivr CDN, so opening it needs a network. `proxy_viewer.py` takes the page scaffold from `viewer_core.py` in `scripts/tools/dayz-3d-viewer`.

## Scripts

All in `<skill-dir>\scripts\`.

| Script | What it does |
|---|---|
| `proxy_frame.py` | The frame rule: angle sort to anchor and orientation matrix, and the builder of the canonical triangle. Used by the other scripts. |
| `proxy_extract.py` | Host `.p3d` to `recipe.json`: the body mesh, and for every proxy its triangle, its derived frame, an `ambiguous` flag and the model path it points at. |
| `worn_overlay.py` | Adds the worn model of one item per slot to the recipe as `proxies[i].worn`. Seeds a default item for every slot; `--map` overrides one. |
| `proxy_canon.py` | Recipe to `edits.json`: every proxy rewritten as a canonical, unambiguous triangle at the same anchor. Identity frame by default, or a rotation per slot with `--rot`. |
| `proxy_viewer.py` | Recipe to a standalone HTML editor: move and rotate gizmo, the worn reference and the assembled preview. Its export gives `edits.json` with canonical triangles. |
| `proxy_apply.py` | `edits.json` plus the source `.p3d` to the aligned `.p3d`. Changes only the listed proxy points. |
| `install_py3d.py` | Installs the py3d fork from a wheel (see What it needs). |

## How to run

Read the proxies first. The output lists each proxy with its angles and `AMBIG` or `ok`:

```cmd
python "<skill-dir>\scripts\proxy_extract.py" mannequin.p3d recipe.json
```

**Fast path.** Fixes the common "worn, but turned" case in one pass, with no editor:

```cmd
python "<skill-dir>\scripts\proxy_canon.py" recipe.json edits.json
python "<skill-dir>\scripts\proxy_apply.py" mannequin.p3d edits.json mannequin_aligned.p3d --verify
```

`proxy_canon.py` rewrites every proxy in the recipe, including ones that were already unambiguous, to the raw identity frame. Add a rotation only where a slot needs one: `--rot Headgear=Y:90 Mask=Y:90`. `--scale` sets the triangle's short leg (default 0.001 m).

**With the worn clothing as reference.** Optional, and it needs the ODOL backend:

```cmd
python "<skill-dir>\scripts\worn_overlay.py" recipe.json recipe.json --odol-backend <backend scripts dir>
```

| Option | Use |
|---|---|
| `--dz <folder>` | The unpacked vanilla `DZ` folder. Default `P:\DZ`. |
| `--map Vest=vests/pressvest Legs=pants/cargopants` | Test a specific item on a slot. A value is a full `.p3d` path, `<subfolder>/<stem>` under `DZ\characters`, or a bare `<stem>` searched for under it. |
| `--dry-run` | Print which model each slot resolves to, and stop. Needs no backend. |
| `--no-defaults` | Start empty and map only the slots passed with `--map`. |

**Interactive path.** Set each proxy by eye:

```cmd
python "<skill-dir>\scripts\proxy_viewer.py" recipe.json proxy_align_viewer.html
```

Open the HTML in a browser, align each proxy, click "Export edits", save the text as `edits.json`, then run `proxy_apply.py` as above.

`--verify` reads the result back and prints the selection count, the proxy count and each proxy's first point. Compare them with the first `proxy_extract.py` output before trusting the file, or run `proxy_extract.py` on the result and check that every proxy now says `ok`.

## Using the editor

Click a proxy in the list or its sphere in the view to attach the gizmo. **W** moves and **E** rotates; drag the arrows or the rings. Two overlays help when the recipe holds worn meshes:

- **Final result**: every slot's worn mesh attached to its proxy, following the edits. This is the dressed preview at the current alignment.
- **Worn ref**: the selected proxy's worn mesh at its native position in character space, as a fixed target to align the anchor against.

"Reset proxy" puts a proxy back where it was loaded. "Export edits" opens a box with the JSON; use Select all and Ctrl+C (the clipboard is blocked on a `file://` page) and save it as `edits.json`.

The gizmo sets the anchor's position and the frame's rotation. The export writes a canonical triangle that encodes exactly that, so the frame derived from it is the one set in the editor. Scale is fixed, since a proxy is a tiny triangle; only position and rotation matter.

## Picking the worn model

Clothing ships as more than one model, told apart by suffix: `_m` is worn on the male character, `_f` on the female, and `_g` or `_ground` is the model lying on the ground. For a male host the reference is `_m`. Picking the ground model is the classic cause of "it shows the floor model".

`worn_overlay.py` seeds one default item per slot and prefers the `_m` file when it resolves a name. When a slot has several candidates it prints them (`NOTE` for several `_m` files, `ASK` when there is no `_m` file). Pick one with `--map` and tell the user which; do not guess silently.

This skill aligns the anchor and previews the right worn model. It does not make the engine swap a slot's default `*_dz` proxy for the equipped item's worn model: that is config and skeleton behaviour, described in `skills/_shared/models/proxy-frames.md`.

## Why the write-back is safe

`proxy_apply.py` loads the MLOD with py3d, changes the coordinates of the listed proxy points and writes the model again. It adds and removes nothing, so the host geometry, the host's own selections (for example `woodup1` and `zbytek`), the Geometry and Memory LODs and `#UVSet#` come back as they were. The skill's end to end test builds a host, runs extract, canon and apply, and checks that the body points, the selections, the face count and the Memory LOD are unchanged.

Measured while importing the skill, on a small synthetic host with five proxies and py3d fork 1.10.1: reading the file and writing it back gave identical bytes, and the aligned file had the same length as the source with 67 bytes changed, all inside the point table. The source reports the same byte for byte round trip on real DayZ MLOD files.

The recipe and build path of `dayz-p3d-inspector` is not used here: it does not write proxies and can drop Memory selections.

## Batch edits with py3d

For scripted work with no editor, the py3d fork has the whole add, inspect, align and remove cycle:

```python
import py3d

with open("host.p3d", "rb") as handle:
    model = py3d.P3D(handle)
lod = model.lods[0]

name = lod.add_proxy(
    r"\dz\characters\proxies\vest_dz", 1,
    origin=(0.0, 1.1, 0.0),
    rotation=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
    space="engine",
)
descriptor = {item["name"]: item for item in lod.get_proxies(strict=True)}[name]
lod.align_proxy(
    name,
    origin=(0.0, 1.15, 0.02),
    rotation=descriptor["engine_frame"],
    space="engine",
)
# lod.remove_proxy(name)
model.save("host_aligned.p3d")
```

- `space="raw"` is the default and means the frame the angle sort gives. `space="engine"` means the pose expected in DayZ. The two differ by the matrix `P'`; see `skills/_shared/models/proxy-frames.md`.
- Every one of these calls checks its input before changing anything: path, index, anchor, rotation, scale, the shape of the proxy triangle and that the proxy owns its points and face alone.
- `get_proxies(strict=True)` raises `ValueError` on a malformed proxy selection, which includes a hand-written 90/45/45 proxy whose face normal does not match its frame. Run `proxy_canon.py` and `proxy_apply.py` first, or call `get_proxies()` without `strict` to list them.
- `align_proxy` keeps the identities of the points, the face and the selection. `remove_proxy` deletes exactly the proxy's selection, face and three points, renumbers the remaining point indexes and sharp edges, and leaves the normal pool as it is on purpose.

## References

| Question | Open |
|---|---|
| How does the engine turn the triangle into a position and a facing, and why is a 90/45/45 triangle ambiguous? | `skills/_shared/models/proxy-frames.md`, "The triangle is read by its angles" and "Ambiguous triangles" |
| Why does a model render 90 degrees off although the offline frame is identity? | same file, "Raw frame and engine frame" |
| A driver or passenger sits sideways, in the air, or turns on get-in. | same file, "Crew proxies" |
| A body part split into its own model shows at the origin, rotated, or not at all. | same file, "Body-part proxies" |
| A suppressor, optic or rail mount is turned on the gun, or right on the gun and wrong in the inventory icon. | same file, "Weapon attachment proxies" |
| How is a proxy named, and which config class does it need? | `skills/_shared/models/proxies.md` |
| Which model is worn and which lies on the ground, in config? | `skills/_shared/wearables/references/models-and-proxies.md` |

## After aligning

Run `/dayz-p3d-audit` on the aligned MLOD, pack it with `/dayz-build-pbo`, and check the result in game with `/dayz-launch-test`. An offline frame is not proof for a proxy: the model spawned and rendered in game is.

## On Linux

Agentic-Z is a Windows workspace and the steps above are the Windows workflow. The source of this skill also ran on Linux through Proton; the setup, the measured tool matrix and the pitfalls are in `_shared/linux-proton.md`. What changes for this skill:

- `P:\` is a plain directory mapped by `dayz-proton.sh init <dir>` (the script is `skills/_shared/scripts/dayz-proton.sh`), so a `P:\<Mod>\...` path is `<dir>/<Mod>/...`. Pass that directory's `DZ` folder to `worn_overlay.py --dz`; the preflight gate runs only for a folder on `P:`.
- The scripts here are Python and the editor is a browser page; both run natively.
- Object Builder and TexView run under Proton: `dayz-proton.sh gui ObjectBuilder <p3d>` and `gui TexView <paa>`. Object Builder opened and displayed a model there; editing in it was not exercised.
- Packing, signing and binarizing use dayzmake 1.0.0 or later, bzed's DayZ fork of armake2 (https://github.com/bzed/dayzmake), pinned to `v1.0.0`: the release binary `dayzmake-v1.0.0-debian-trixie-x86_64.tar.gz` from https://github.com/bzed/dayzmake/releases/tag/v1.0.0, or `cargo install --git https://github.com/bzed/dayzmake --tag v1.0.0`. Use `dayzmake build`, `keygen`, `sign`, and `build --proton-binarize` where needed; the `skills/_shared/scripts/dayz-mod-pack.sh` helper wraps them (`init`, `keygen`, `build [--binarize-models]`, `check`, `publish-hint`). Upstream armake2 is no substitute: it is built for Arma, its V3 file hash leaves out `*.c` files, and it lacks the DayZ-only functions dayzmake keeps adding.
- The source author's comparison of 2026-11-03, a textured cube against Bohemia's Binarize from a `P:` root, matched byte for byte (fork commit `7dcb3cf`, then still named armake2; `v1.0.0` contains it). That compares files; it is not an in-game check of the binarized model.
- In-game checks on Linux are in the Linux notes of the `dayz-test-ingame` skill (`skills/dayz-test-ingame/references/linux.md`).
