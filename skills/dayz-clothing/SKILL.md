---
name: dayz-clothing
description: "Runs the worn clothing tools on the _m and _f models of a DayZ wearable: the alignment viewer (extract a worn MLOD, fit its plates to the body in a browser page, apply the adjustments back to every LOD) and the FBX export that hands worn models to an artist with their bone weights. Use when worn plates sit off the body and need fitting, or a worn model goes to an artist. Why a worn item floats, stays rigid or explodes, and the worn model and model.cfg contract, are in the wearables pack, skills/_shared/wearables/README.md."
argument-hint: "<garment_m.p3d> [<garment_f.p3d>] [--out <folder>]"
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-clothing

Runs the clothing scripts. They ship with the model tools; this skill is the entry point for running them on a worn model. Before fitting, rule out the three failures that leave no log error (`skills/_shared/wearables/references/worn-models.md`, "Three failures with no log error"): plates that sit off the body are worth fitting only once the item registers, binds and animates.

Follow `skills/_shared/dayz-conventions.md`. The scripts work offline on the files you name and do not run `/dayz-preflight`; packing and testing go through `/dayz-build-pbo` and `/dayz-launch-test`, which do. They read MLOD models only and need the py3d DayZ fork in `scripts/tools/py3d/`, 1.6.0 or newer, which they add to the path themselves; `alignment_viewer_build.py` reads only JSON.

## Alignment viewer

```cmd
python "<skill-dir>\..\dayz-model-tools\scripts\alignment_viewer_extract.py" path\to\garment_m.p3d --out path\to\work
python "<skill-dir>\..\dayz-model-tools\scripts\alignment_viewer_build.py" --data path\to\work\align_data.json
python "<skill-dir>\..\dayz-model-tools\scripts\apply_alignment_json.py" --adjust path\to\adjust.json path\to\garment_m.p3d path\to\garment_f.p3d
```

1. **Extract** the worn model's mesh, region weights and pivots to JSON. `--regions`, `--combo name=part+part`, `--lod` and `--ghost <p3d>` (a reference wireframe) change what is extracted.
2. **Build** the HTML page next to the data and open it in a browser with a network connection.
3. **Fit** with the sliders, press "Generate adjustments JSON" and save the text as a `.json` file.
4. **Apply** to every LOD. The script backs each file up to `_backups` first; `--samples <json>` cross-checks the math against the page before any file changes.

Exit codes: 0 done; 1 the sample cross-check failed or an input could not be used; 2 py3d or the viewer core is missing or the wrong version. The options, the reference wireframe and what was measured are in `skills/_shared/wearables/references/fitting-worn-models.md`.

Outside an agent session, `scripts\dayz\clothing-viewer-extract.bat`, `scripts\dayz\clothing-viewer-build.bat` and `scripts\dayz\clothing-viewer-apply.bat` run the three scripts with the same arguments.

## FBX handoff to an artist

```cmd
blender -b --python "<skill-dir>\..\dayz-model-tools\scripts\export_clothing_fbx.py" -- --out path\to\package --texture path\to\garment_co.png path\to\garment_m.p3d path\to\garment_f.p3d
```

The script imports each FBX again in a clean scene, prints the vertex groups and a weight sum, and exits 1 if a group was lost; read that output before shipping. Package the FBX files, the PNG, the MLOD models, the `model.cfg` (from `skills/dayz-model-tools/templates/model.cfg.template`) and a README written from `skills/dayz-model-tools/templates/README-ARTIST.template.md`. The axis map, the way back and the old packages are in `skills/_shared/wearables/references/fitting-worn-models.md`.

## Where the clothing knowledge is

| Question | Read |
|---|---|
| Skeleton name, frame, selections, weights, `model.cfg`, the build and the failures with no log error | `skills/_shared/wearables/references/worn-models.md` |
| Fitting by hand or by an artist, and the FBX round trip | `skills/_shared/wearables/references/fitting-worn-models.md` |
| Fitting by script on the official rig, and what that failed on | `skills/_shared/wearables/references/autofit-on-official-rig.md` |
| Parent class, slots, cargo, protection, colors and the 1.30 changes | The other files of `skills/_shared/wearables/README.md` |
