# Proxy editor

How to read, rewrite and write back the proxy triangles of a host model with the proxy scripts of `/dayz-model-tools`, so attached clothing or items stop rendering at the floor, floating or turned. The rule that turns a triangle into a position and a facing is in `proxy-frames.md`; proxy names and config classes are in `proxies.md`.

A proxy is a named selection `proxy:\path\to\model.NNN` over one tiny triangle in a visual LOD; the triangle sets where the other model sits and which way it faces. The triangle is read by its angles, not by its vertex order. That is MLOD format knowledge backed by in game measurements on mods, not checked on `P:\`.

The editor loads the host and every proxy, lets you move and rotate each anchor against the real worn clothing, and writes the edited triangles straight back into the MLOD with py3d. The scripts are in `skills\dayz-model-tools\scripts\`, written `<scripts>` below.

Follow `skills/_shared/dayz-conventions.md`. Only `worn_overlay.py` reads vanilla data: it runs `/dayz-preflight` first when its `--dz` folder is on `P:\` (the default) and stops if that fails. The other scripts read and write only the files you pass.

## When to use it

Use it for misplaced or turned proxies on any host model. The usual host is a dressable static object, such as a mannequin or an armor rack: an `Inventory_Base` or `Container_Base` item whose model embeds the vanilla `\dz\characters\proxies\*_dz` proxies and whose config lists clothing slots in `attachments[]`. The same steps fix crew seats, weapon attachment proxies and body part proxies; what differs for each is in `proxy-frames.md`.

The host must be an MLOD file, the `.p3d` Object Builder saves. A binarized host has to be converted outside Agentic-Z first.

## Setup

Run these from the repository root:

```cmd
python -m pip install -e scripts/tools/py3d
python -m pip install numpy
python -c "import py3d; assert getattr(py3d,'IS_DAYZ_FORK',False) and tuple(map(int,py3d.__version__.split('.')))>=(1,6,0), (py3d.__version__, py3d.__file__)"
```

- py3d here is the DayZ fork in `scripts/tools/py3d`, version 1.6.0 or later. The last line fails when another py3d imports instead.
- Never run `pip install py3d`: the PyPI package of that name is a point cloud library. The Arma py3d uses the same import name and lacks the proxy functions and write guards; uninstall either one first (`python -m pip uninstall py3d`).
- With a built wheel of the fork instead of the source folder, `python "<scripts>\install_py3d.py"` installs it. It looks in a `wheels\` folder next to `scripts\`, then in `scripts\tools\py3d\dist\`, and stops without changing anything when there is no wheel or more than one, when a legacy `py3d-*.whl` sits beside it, or when the py3d already installed is not the fork. Agentic-Z ships no wheel.
- `worn_overlay.py` shows vanilla worn clothing, and vanilla worn models are binarized (`P:\DZ\characters\vests\plate_carrier_m.p3d` starts with `ODOL`). It needs an outside ODOL to MLOD backend: a folder holding `odol_reader.py` and `odol_to_mlod.py`, passed with `--odol-backend` or set in `DAYZ_ODOL_BACKEND_ROOT`. Agentic-Z ships none. A backend set up for `scripts/tools/dayz-odol-strict` is not enough, because that tool reads ODOL only and has no `odol_to_mlod.py`. Without a backend, skip the overlay; the other steps work without it.
- The editor page loads Three.js 0.185.1 from jsDelivr, so opening it needs a network. `proxy_viewer.py` takes the page scaffold from `viewer_core.py` in `scripts/tools/dayz-3d-viewer`.

## Scripts

| Script | What it does |
|---|---|
| `proxy_frame.py` | The frame rule: angle sort to anchor and orientation matrix, and the builder of the canonical triangle. The other scripts use it |
| `proxy_extract.py` | Host `.p3d` to `recipe.json`: the body mesh, and for each proxy its triangle, its derived frame, an `ambiguous` flag and the model path it points at |
| `worn_overlay.py` | Adds the worn model of one item per slot to the recipe as `proxies[i].worn`. Seeds a default item for each slot; `--map` overrides one |
| `proxy_canon.py` | Recipe to `edits.json`: every proxy rewritten as a canonical, unambiguous triangle at the same anchor. Identity frame by default, or a rotation per slot with `--rot` |
| `proxy_viewer.py` | Recipe to a standalone HTML editor with a move and rotate gizmo, the worn reference and the dressed preview. Its export gives `edits.json` with canonical triangles |
| `proxy_apply.py` | `edits.json` plus the source `.p3d` to the aligned `.p3d`. Changes only the listed proxy points |
| `install_py3d.py` | Installs the py3d fork from a wheel (see "Setup") |

Outside an agent session, `scripts\dayz\proxy-extract.bat`, `proxy-canon.bat`, `proxy-worn-overlay.bat`, `proxy-viewer.bat` and `proxy-apply.bat` in the same folder run the five scripts with the same arguments.

## Running it

Read the proxies first. The output lists each proxy with its angles and `AMBIG` or `ok`:

```cmd
python "<scripts>\proxy_extract.py" mannequin.p3d recipe.json
```

The fast path rewrites every proxy as an unambiguous triangle in one pass, with no editor. It is meant for the common "worn, but turned" case:

```cmd
python "<scripts>\proxy_canon.py" recipe.json edits.json
python "<scripts>\proxy_apply.py" mannequin.p3d edits.json mannequin_aligned.p3d --verify
```

`proxy_canon.py` rewrites every proxy in the recipe to the raw identity frame, including ones that were already unambiguous. Add a rotation only where a slot needs one: `--rot Headgear=Y:90 Mask=Y:90`. `--scale` sets the triangle's short leg (default 0.001 m).

One point is open and not checked on `P:\`. The raw identity default assumes vanilla worn clothing is authored in character space, so identity shows the item worn and upright. In game measurements on weapon and vehicle mods found that the engine draws the triangle as `P'` times the raw frame, and a raw identity frame there came out 90 degrees on its side; the two have not been compared on the same clothing model in game. When a proxy rewritten by `proxy_canon.py` renders turned by 90 degrees, rewrite it with `space="engine"` in py3d (see "Batch edits with py3d") or pass `--rot` for that slot. Details are in `proxy-frames.md`, section "Raw frame and engine frame".

To align against the worn clothing, add it to the recipe. This step is optional and needs the ODOL backend:

```cmd
python "<scripts>\worn_overlay.py" recipe.json recipe.json --odol-backend <backend scripts dir>
```

| Option | Use |
|---|---|
| `--dz <folder>` | The unpacked vanilla `DZ` folder. Default `P:\DZ` |
| `--map Vest=vests/pressvest Legs=pants/cargopants` | Test a given item on a slot. A value is a full `.p3d` path, `<subfolder>/<stem>` under `DZ\characters`, or a bare `<stem>` searched for under it |
| `--dry-run` | Print which model each slot resolves to, then stop. Needs no backend |
| `--no-defaults` | Start empty and map only the slots passed with `--map` |

To set each proxy by eye, write the editor page:

```cmd
python "<scripts>\proxy_viewer.py" recipe.json proxy_align_viewer.html
```

Open it in a browser, align each proxy, click "Export edits", save the text as `edits.json`, then run `proxy_apply.py` as above.

`--verify` reads the result back and prints the selection count, the proxy count and each proxy's first point. Compare them with the first `proxy_extract.py` output before trusting the file, or run `proxy_extract.py` on the result and check that every proxy now says `ok`.

## Using the editor

Click a proxy in the list, or its sphere in the view, to attach the gizmo. W moves and E rotates; drag the arrows or the rings. Two overlays help when the recipe holds worn meshes:

- Final result: each slot's worn mesh attached to its proxy, following the edits. This is the dressed preview at the current alignment.
- Worn ref: the selected proxy's worn mesh at its own position in character space, a fixed target to align the anchor against.

The editor does not read the frame stored in the loaded triangle. Each gizmo starts at its loaded anchor with the raw identity frame (rotation 0, 0, 0), and "Reset proxy" returns to that anchor and frame, not to the loaded orientation. "Export edits" opens a box with the JSON; use Select all and Ctrl+C (the clipboard is blocked on a `file://` page) and save it as `edits.json`.

The gizmo sets the anchor's position and the frame's rotation. The export writes a canonical triangle for every proxy, touched or not, that encodes exactly that position and rotation. A proxy you did not rotate is therefore written at the raw identity frame, as `proxy_canon.py` does, even when its loaded frame was already right. To keep such a proxy as it is, delete its entry from `edits.json` before running `proxy_apply.py`, which changes only the proxies listed. Each entry carries `"moved": true` when its gizmo was dragged. Scale is fixed, since only position and rotation matter for a proxy.

## Picking the worn model

Clothing ships as more than one model, told apart by suffix: `_m` is worn on the male character, `_f` on the female, and `_g` or `_ground` lies on the ground. For a male host the reference is `_m`. Picking the ground model is the usual cause of "it shows the floor model".

`worn_overlay.py` seeds one default item per slot and prefers the `_m` file. When a slot has several candidates it prints the one it picked and the others: `NOTE` with the `_m` files when there are several, `ASK` with every match when there is no `_m` file. Pick one with `--map` and tell the user which; never guess silently.

The editor aligns the anchor and previews the right worn model. It does not make the engine swap a slot's default `*_dz` proxy for the equipped item's worn model; that is config and skeleton behaviour, described in `proxy-frames.md`.

## What the write back keeps

`proxy_apply.py` loads the MLOD with py3d, changes the coordinates of the listed proxy points and writes the model again. It adds and removes no point, face or selection, so the host geometry, the host's own selections (for example `woodup1` and `zbytek`), the Geometry and Memory LODs and `#UVSet#` come back as they were. The end to end test `test_proxy_pipeline.py` in the scripts folder builds a host, runs extract, canon and apply, and checks that the body points, the selections, the face count and the Memory LOD are unchanged.

Measured with py3d 1.10.1 on a small synthetic host with five 90/45/45 proxies: a read and write gave identical bytes, and the aligned file had the same length as the source, with every changed byte inside the point table.

A real MLOD does not always come back byte for byte. py3d writes tags in the order Object Builder writes them, and it does not read `#Animation#` tags, so they are not written back. Measured with py3d 1.10.1 on a third party MLOD with `#Animation#` tags: a plain read and write shrank it to about a seventh of its size, while the point, face and selection counts of every LOD stayed the same. Keep the source file. When the aligned file is much smaller than the source, the host had vertex animation frames that this write back dropped.

The Recipe and build path of the p3d inspector (`tools-p3d-inspector.md`) is not used here: it does not write proxies and can drop Memory selections.

## Batch edits with py3d

For scripted work without the editor, the py3d fork has the whole add, inspect, align and remove cycle:

```python
import py3d

with open("host.p3d", "rb") as handle:
    model = py3d.P3D(handle)
lod = model.lods[0]

# The index must be free: add_proxy refuses a name the LOD already has,
# and a dressable host usually has vest_dz.001 already.
name = lod.add_proxy(
    r"\dz\characters\proxies\vest_dz", 2,
    origin=(0.0, 1.1, 0.0),
    rotation=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
    space="engine",
)
descriptor = {item["name"]: item for item in lod.get_proxies()}[name]
lod.align_proxy(
    name,
    origin=(0.0, 1.15, 0.02),
    rotation=descriptor["engine_frame"],
    space="engine",
)
# lod.remove_proxy(name)
model.save("host_aligned.p3d")
```

- `space="raw"` is the default and means the frame the angle sort gives. `space="engine"` means the pose expected in DayZ. The two differ by the matrix `P'` (`proxy-frames.md`).
- Each of these calls checks its input before changing anything: path, index, anchor, rotation, scale, the shape of the triangle, and that the proxy owns its points and face alone.
- `get_proxies(strict=True)`, `align_proxy` and `remove_proxy` raise `ValueError` on a malformed proxy selection. That includes a proxy whose stored face normal is not the X row of its raw frame, which is the usual state of a hand written 90/45/45 proxy. `proxy_apply.py` moves points only and leaves the stored normal, so a proxy it rewrote can still fail this check (py3d 1.10.1). `get_proxies(strict=True)` checks every proxy of the LOD, so one such proxy fails the whole listing; that is why the example lists without `strict`. Place such proxies with `proxy_canon.py` and `proxy_apply.py`, and keep `align_proxy` and `remove_proxy` for proxies that pass, such as the ones `add_proxy` wrote.
- `align_proxy` keeps the identities of the points, the face and the selection. `remove_proxy` deletes exactly the proxy's selection, face and three points, renumbers the remaining point indexes and sharp edges, and leaves the normal pool as it is on purpose.

## Where to read more

| Question | Open |
|---|---|
| How does the engine turn the triangle into a position and a facing, and why is a 90/45/45 triangle ambiguous? | `proxy-frames.md`, sections "The triangle is read by its angles" and "Ambiguous triangles" |
| Why does a model render 90 degrees off although the offline frame is identity? | `proxy-frames.md`, section "Raw frame and engine frame" |
| A driver or passenger sits sideways, in the air, or turns on get in | `proxy-frames.md`, section "Crew proxies" |
| A body part split into its own model shows at the origin, turned, or not at all | `proxy-frames.md`, section "Body-part proxies" |
| A suppressor, optic or rail mount is turned on the gun, or right on the gun and wrong in the inventory icon | `proxy-frames.md`, section "Weapon attachment proxies" |
| How is a proxy named, and which config class does it need? | `proxies.md` |
| Which model is worn and which lies on the ground, in config? | `_shared/wearables/references/models-and-proxies.md` |

## After aligning

Run `/dayz-p3d-audit` on the aligned MLOD, pack it with `/dayz-build-pbo`, and check it in game with `/dayz-launch-test`. An offline frame is not proof for a proxy; the model spawned and drawn in game is.

## On Linux

Agentic-Z is a Windows workspace and the steps above are the Windows workflow. The editor also runs on Linux through Proton; the setup, the tool matrix and the pitfalls are in `_shared/linux-proton.md`. What changes here:

- `P:\` is a plain directory mapped by `dayz-proton.sh init <dir>` (`scripts/tools/dayz-linux/dayz-proton.sh`), so `P:\<Mod>\...` is `<dir>/<Mod>/...`. Pass that directory's `DZ` folder to `worn_overlay.py --dz`; the preflight check runs only for a folder on `P:`.
- The scripts are Python and the editor is a browser page; both run natively.
- Object Builder and TexView run under Proton: `dayz-proton.sh gui ObjectBuilder <p3d>` and `gui TexView <paa>`. Object Builder opens and displays a model there; editing in it is untested.
- Packing, signing and binarizing use dayzmake 1.0.0 or later, the DayZ fork of armake2; installing a pinned release is in `_shared/linux-proton.md`. Use `dayzmake build`, `keygen`, `sign`, and `build --proton-binarize` where needed; `scripts/tools/dayz-linux/dayz-mod-pack.sh` wraps them (`init`, `keygen`, `build [--binarize-models]`, `check`, `publish-hint`). The original armake2 is no substitute: it is built for Arma, its V3 file hash leaves out `*.c` files, and it lacks the DayZ only functions dayzmake adds.
- A textured cube binarized with `dayzmake build --proton-binarize` (dayzmake 1.0.0) matched Bohemia's Binarize run from a `P:` root byte for byte. That compares files; it is not an in game check of the binarized model.
- In game checks on Linux are in `skills/dayz-launch-test/references/linux.md`.
