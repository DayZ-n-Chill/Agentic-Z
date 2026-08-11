---
name: dayz-deploy-pbo
description: Deploy pre-compiled PBOs from a workspace bundle (workspace/<ModName>/Addons/*.pbo + Keys/*.bikey) to P:\Mods\@<ModName>\ by pure copy — no AddonBuilder, no source required. Idempotent (skips unchanged files), verified (counts + missing-.bisign warnings), marker-gated so it never clobbers a deploy dir it doesn't own. Use for PBO-only third-party mods and umbrella/bundle @mods; composes with /dayz-build-pbo for bundles with a built linker PBO.
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-deploy-pbo

Mirror pre-compiled artifacts from a workspace bundle folder to the deploy tree: `workspace/<ModName>/Addons/*.pbo` (+ `*.bisign`) to `P:\Mods\@<ModName>\Addons\`, `Keys/*.bikey` to `P:\Mods\@<ModName>\Keys\`, plus optional `meta.cpp`/`mod.cpp`. Pure copy — no AddonBuilder, no binarization, no buildable source required (`config.cpp` and `$PBOPREFIX$` are the **build** path's gate, not this one). Gates on `/dayz-preflight`.

Follow `.claude/skills/_shared/dayz-conventions.md` (see "Bundle / umbrella mods").

## How to run

```cmd
python "<skill-dir>\deploy.py" <ModName>
```

| Argument | Required? | Notes |
|---|---|---|
| `<ModName>` | yes | Must match a bundle folder `workspace/<ModName>/` containing `Addons/` with at least one `.pbo`. |

## What it does

1. **Preflight gate** — runs `/dayz-preflight`; halts on non-zero.
2. **Bundle check** — verifies `workspace/<ModName>/Addons/` exists and contains at least one `.pbo`. Does NOT require `config.cpp`, `$PBOPREFIX$`, or the `P:\<ModName>\` junction — a pure payload bundle has no buildable source.
3. **Ownership gate** — if `P:\Mods\@<ModName>\` already exists, it must contain the `.agentic-z-scaffold` marker with matching content (the same ownership rule `dayz-clean-workspace` uses). An unmarked dir could be a subscribed mod or hand-placed folder; deploy refuses to touch it.
4. **Copy Addons** — mirrors `Addons/*.pbo` + `Addons/*.bisign` into `P:\Mods\@<ModName>\Addons\`. Idempotent: a file already present with identical size + mtime is skipped. Purely additive: nothing in the deploy dir is ever deleted, so a linker PBO placed there by `/dayz-build-pbo` survives.
5. **Copy Keys** — mirrors `Keys/*.bikey` into `P:\Mods\@<ModName>\Keys\` (skipped entirely if the bundle has no keys).
6. **Copy metadata** — `meta.cpp` / `mod.cpp` from the bundle root, if present.
7. **Verify** — reports copied vs. unchanged counts per run, and `[WARN]`s for every `.pbo` lacking a matching `<name>.pbo.<key>.bisign` (signature-checking clients will reject unsigned PBOs).
8. **Drop ownership marker** — writes `P:\Mods\@<ModName>\.agentic-z-scaffold` (single line: the modname), exactly as `/dayz-build-pbo` does, so `dayz-clean-workspace` can manage the deployed dir.

## Composing with /dayz-build-pbo (umbrella bundles)

A bundle may carry an optional *linker* `config.cpp` + `$PBOPREFIX$` (a content-free `CfgPatches` declaring `requiredAddons[]`). Build the linker from source first, then deploy the payload:

```cmd
python "<skill-dir>\..\dayz-build-pbo\build.py" <ModName>
python "<skill-dir>\deploy.py" <ModName>
```

Both write the same ownership marker; deploy never deletes, so the built `<ModName>.pbo` and the copied payload PBOs coexist under one `@<ModName>\Addons\`. Order doesn't matter for correctness — but do NOT pass `--clean` to a build that runs *after* deploy (its `-clear` wipes `Addons\`, payload included).

## Refuses to run if

- `/dayz-preflight` returns non-zero.
- `workspace/<ModName>/` is missing, has no `Addons/` folder, or `Addons/` contains no `.pbo`.
- `P:\Mods\@<ModName>\` exists without the `.agentic-z-scaffold` ownership marker (or with mismatched content). Remove the dir manually if it's actually yours: `cmd /c rmdir /s /q P:\Mods\@<ModName>`.

## Output

Success:

```
DayZ preflight
[OK]    P:\ is mounted
...
Preflight complete.
[OK]    P:\Mods junction valid
[OK]    workspace\MyBundle\Addons\ found (with .pbo payload)
[WARN] extras.pbo has no matching .bisign - clients with signature verification enabled will reject it.

[OK]    Deployed to P:\Mods\@MyBundle\ - 5 copied, 0 unchanged (3 .pbo, 2 .bisign, 1 .bikey)
```

Re-run with nothing changed: same shape, `0 copied, 5 unchanged`.

Failure (any step):

```
[FAIL] <reason>
       <hint or next step>
```

## Do not

- Don't delete or overwrite anything the bundle doesn't provide — no `-clear`-style wipe, ever. The additive copy is what lets a build-pbo linker PBO coexist with the payload.
- Don't require `config.cpp`/`$PBOPREFIX$` or the `P:\<ModName>\` junction — those gate the build path only.
- Don't invoke AddonBuilder or attempt to binarize — payload PBOs are already compiled (and may be large / LFS-backed; copy is the only correct operation).
- Don't repackage multiple PBOs into one prefixed PBO — each payload PBO keeps its own prefix; `@<ModName>` is just the container.
- Don't deploy into an unmarked `@<ModName>` dir — fail and let the user resolve the collision.
