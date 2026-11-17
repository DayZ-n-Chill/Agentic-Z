# DayZ: verified capabilities and feasibility verdicts

Status: verdicts and gotchas from the author's mod projects (LF-COM, Crate, LF_VStorage, LF_PowerGrid, LF_Transfer), translated into English. Vendored, not yet checked on `P:\` line by line; the facts checked on 2026-11-17 are listed under "Checked on `P:\`" at the end. Third-party facts name the mod or page they come from.

> Cross-cutting knowledge. Gathers **feasibility verdicts** that cost
> entire research sessions (reviewing P:\, cloning CF/Dabs, web
> search, spikes) and a handful of **verified gotchas** not covered
> by DayZ skills. The goal: do not repeat investigations already closed.

## Verdict: pixels CANNOT be captured from a pure DayZ mod

Thoroughly investigated in the **LF-COM** project (mod for "in-game photo
social network"). Firm conclusion after reviewing all of `P:\`, cloning CF and Dabs
Framework (zero capture/bitmap/readback APIs) and web search:

- **Retail DayZ does not allow reading the framebuffer from script.** It is an
  intentional block by Bohemia (anticheat / platform control).
- **`CallExtension` (native DLL) was removed from the DayZ public API.**
  It exists in Arma 3, not in DayZ. BattlEye blocks client-side extensions and
  there is no whitelisting process. Zero Workshop mods have managed
  to ship a client-side DLL. (Source: blog.lystic.dev, 2021-05-22.)
- **`MakeScreenshot` is broken since 1.19** and remains broken in 1.29.
  Bohemia is not going to fix it.
- **`Workspace.SaveScreenshot()` does NOT exist** — it was a confabulation in a
  session; do not assume it.
- **`SetObjectTexture` is local/client-only** in DayZ Enforce. `SetObjectTextureGlobal`
  does not exist (that is Arma 3 only). `r2t` surfaces are
  config-bound (statically declared in `config.cpp`, tied to memory
  points), **not creatable at runtime** from script, and require active PiP.
  Verified in `entityai.c v1.24.157551`.

**Architectural decision derived (LF-COM)**: the viable path is
**PBO + launcher companion `.exe` + web backend**. The launcher polls the
Steam screenshots folder and a flag file in `$profile:\LFCOM\`,
converts PNG→EDDS with Bohemia's `ImageToPAA.exe`, and the mod loads the EDDS
with `LoadImageFile`.

### Camera/preview APIs that DO work (verified)

- `PlayerPreviewWidget`: `GetDummyPlayer()` (since 1.02), `SetModelOrientation`,
  `SetModelPosition`, `UpdateItemInHands`. **Only works for humans** — there is
  no equivalent vanilla widget for zombies/animals/AI.
- `FreeDebugCamera.GetInstance().SetFreezed(false)`.
- Replicated skins pattern that does work: distribute N `.paa` in the PBO
  via `hiddenSelectionsTextures[]`, replicate only index via SyncVar/RPC,
  each client calls `SetObjectTexture(i, array[idx])` locally.

## Verdict: debris physics and dynamic items

- **`ECE_CREATEPHYSICS` is not enough** for debris with `simulation = "inventoryItem"`:
  creates the shape but leaves the body static, `dBodyApplyImpulse` is discarded
  → debris frozen in the air. **Fix**: `InventoryItem.ThrowPhysically(null, impulse, false)`
  (requires casting `EntityAI → ItemBase`). Manual alternative:
  `CreateDynamicPhysics` + `SetDynamicPhysicsLifeTime` + gravity + impulse.
- **PhysX silently ignores Geometry LOD components < 0.5 m.**
  That is why a ball POC was made 50 cm. Production trick: an
  invisible oversized Geometry LOD to keep the visual at real size.
- **0.5 m rule nuanced**: applies to Geometry LOD collision
  (`Container_Base`/`BuildingBase`), NOT to `Inventory_Base` with
  `simulation=inventoryItem`. And a destructible `Container_Base` **without
  FireGeo does not receive bullets** — FireGeo is necessary to receive gunshots.
- **`StaticObj_Wreck_Train_Wagon_*` are static PhysX bodies** —
  `dBodyApplyImpulse` is discarded on them. Viable path: detect collision
  with `OnContact`, delete the static and replace with own dynamic entity.
- **Vanilla plastic explosive does NOT detonate when ruined** — intentional Bohemia
  safety feature. Only detonates via Remote Detonation Unit; `Detonate()`
  is private. Alternative: orchestrate manually (particle + soundset +
  `AreaDamageManager`) or call `Detonate()` via reflection.

## Verified gotchas not covered by skills

These caused repeated waves of compilation errors or bugs in
real projects. If they reappear in a third mod, candidates to enter
`enforce-script-reference` / `dayz-build-pbo`.

**Config / build:**
- `requiredAddons` must be `"JM_CF_Scripts"`, **not** `"CF"`.
- `worldScriptModule files[]` lists only the **root folder** (`4_World`), not
  subfolders (`Actions`) separately. Pointing to a folder automatically includes
  new files → `config.cpp` does not need to be touched when adding
  a `.c` to that folder.
- Texture paths in `config.cpp` need **double backslash**
  (`\\dz\\gear\\…`); with a single one the engine does not resolve.
- Proxy classes: must inherit from `ProxyAttachment` and proxy model
  paths take an initial `\` (`"\LFPowerGrid\data\…"`). `hiddenSelections[]`
  necessary for material swaps by script.
- `hiddenSelections[]={"camoGround"}` (e.g. `Barrel_ColorBase`) **hides
  the geometry** until `hiddenSelectionsTextures[]` assigns texture to it:
  without texture the object is invisible, not gray.
- Missing `$PBOPREFIX$` in root = AddonBuilder fails.

**Enforce Script:**
- No `do...while`. Standard DayZ pattern:
  `bool keep=true; while(keep){ …; keep=FindNextFile(...); }`.
- Does not allow expressions split across multiple lines.
- If the parent class has a parameterized constructor, **all** children
  must have identical signature → solution: parent without parameterized
  constructor, each child defines its own.
- `ref` only on class member fields, **never** on locals.
- `JsonKeyExists` must include the `:` in the pattern (`"key":`) to avoid
  matching substrings.
- `Print()` writes to the **script log** (where the `SCRIPT :` appear);
  `PrintToRPT()` writes to the `.rpt`. Confusing them = "nothing appears in the log".
- To notify the player: `player.MessageStatus()` — not `GetGame().Chat()`
  (does not depend on chat mods).
- When consuming a key with a visible custom prompt: `return` WITHOUT calling
  `super.OnKeyPress()`, otherwise there is double activation (F is bound to
  vanilla ActionManager).
- `DZ_Weapons` is always loaded at runtime even if not in
  `requiredAddons`.

**Other:**
- Bug T148506: `inventorySlot` string-vs-array when porting classes.
- Damage rvmat that only changes tint = Stage3 uses proc `color()` instead
  of the vanilla overlay texture (`weapons_damage_wood_mc.paa`, tiling 4×).
- DayZ 1.29 renamed vanilla SoundSets: `VSS_Vintorez_*` → `VSS_silencer_*`;
  `AmphibianS_InteriorTail` → `AmphibianS_silencerInteriorTail`. Custom
  mod SoundSets live in their own PBOs and do not need aliases.
- `OnStoreLoad` returning `false` does not crash the server: the entity does not
  enter the world, `m_IsStoreLoad=false`, the entry is purged on the next
  autosave (it is a caught `Virtual Machine Exception`, self-healing).
- DayZ server minidump diagnostics: RPT truncates addresses to 32
  bits (misleading "Unknown module"); the real address is 64-bit. Without Bohemia
  PDBs you cannot go further than "the AV falls within
  `DayZServer_x64.exe`" = engine bug.

## Verdict: DayZ animation (phase 0 research, 2026-05-20)

Investigated for the `dayz-animation-pipeline` skill (then a draft). Two web sub-agents
with primary sources (Bohemia wiki, PMC wiki, GitHub repos, `seanim.py`).

**There are TWO animation systems in parallel — do not confuse them:**

- **Config-driven** (`model.cfg` + `config.cpp` + script): props/objects —
  doors, levers, wheels, hide-on-attach. Types `rotation(X/Y/Z)` and
  `translation(X/Y/Z)` [VERIFIED PMC wiki]. `SetAnimationPhase`. **100% text,
  producible in sandbox.** The `hide` type is [VERIFIED against real mod
  kt_roadkill] but not on the PMC wiki — confirm `hideValue` against vanilla.
- **Skeletal**: characters/weapons use the **Enfusion `.txa`→`.anm`** pipeline
  (NOT RTM). RTM is legacy (Real Virtuality), for legacy props/man.

**Sandbox/GUI seam (the critical part):** the author's sandbox is Linux without `P:\` or DayZ
Tools. Layer 1 (config) is produced there entirely. Layer 2 (open intermediaries:
**SEAnim** open-spec, headless Blender keyframes) is assisted there. Layer 3 (Workbench,
FBXToRTMGui, PBO signing, in-game test) is Windows/GUI/computer-use only.

**Walls [VERIFIED]:**
- **Only one player animation mod at a time** — two crash client/server
  (Enfusion engine limit, not policy). Does not affect object animation.
- **RTM is reverse engineering** (explicit legal notice from Bohemia). There is NO
  open-source pure Python RTM writer; only Blender plugins write RTM.
- **`.anm` is proprietary**; DayZATool writes it (closed binary). **SEAnim
  IS an open format** → programmatic path (writer verified by round-trip
  in `skills/dayz-animation-pipeline/scripts/seanim_writer.py`, layout transcribed verbatim from `seanim.py`).
- Skeleton `OFP2_ManSkeleton`, exact bone names or RPT logs
  `Bone X doesn't exist`. Vanilla skeleton cannot be restructured
  ([TBD-verify], community consensus).

**Real tools (all Windows):** Arma3ObjectBuilder (Blender 4.2+,
export RTM), FBXToRTMGui.exe (DayZ Tools), DayZATool (DTZxPorter, `.anm`↔SEAnim),
DayZAnimationPluginDemo (Blender→`.txa`), SE2Dev/io_anim_seanim (SEAnim spec).

**Inherited pending [TBD-verify]** (confirm against `P:\` before trusting):
types `translationModelX/Y/Z` and `direct`; DayZ engine sources `doors`/`damage`;
exact signature of `SetAnimationPhase`; Blender→DayZ scale factor; whether DayZ/Arma
Blender plugins run headless in sandbox; vanilla IK `.anm` catalog
(Hatchback_02 paths); whether FBXToRTM comes with DayZ Tools or only Arma 3.

**Seam clarification (added 2026-05-20, evals + packaging):** the `.p3d`
geometry side that an animation needs —the named selection being animated and the
pair of memory points defining the `axis`— **is producible in sandbox**, it is NOT
Object Builder/Windows. Route: `dayz-p3d-inspector` (extract → Recipe JSON → edit
memory points/axes/selections → rebuild `.p3d`) or `dayz-model-pipeline` (py3d
assembly); an external ODOL→MLOD converter first if the `.p3d` is ODOL (binarized, not
editable); `dayz-p3d-audit` to verify winding/`Component01`. Caveats: py3d
edits MLOD; adding memory points and the axis is trivial, but **authoring a new named
selection grouping specific geometry** relies on the context of
`dayz-model-pipeline`. Real Layer 3 for Layer 1 work = only PBO signing + in-game
test. (The initial draft pushed this to Object Builder out of conservatism;
corrected in the skill after eval.)

**Skill status (2026-05-20):** `dayz-animation-pipeline` packaged as a
skill (in this repo: `skills/dayz-animation-pipeline/`).
Evals closed (with-skill 100% vs baseline 56% over 4 cases, n=1/arm). Two
validated improvements: `hideValue` as `[TBD-verify]` must-tag, and the seam
clarification above.

## Related

- Skills: `enforce-script-reference`, `dayz-build-pbo`, `dayz-model-pipeline`,
  `dayz-p3d-audit` — cover most of modding; this note is the
  supplement to what was verified in projects and is not in them.
- Skill draft `dayz-animation-pipeline` — complete animation pipeline
  (config-driven + skeletal), pending evals + packaging.
- The modded class server stub pattern note, now in `skills/_shared/enscript/patterns/modded_class.md` ("Server-only overrides need a stub in the base class") — stub pattern
  server-only (bug pattern related to `#ifdef SERVER`).
- Projects where verified: LF-COM, Crate, LF_VStorage, LF_PowerGrid,
  LF_Transfer.
- The Enforce Script reference note, now in `skills/enforce-script-reference/references/review-and-troubleshooting.md` and `hard-rules.md` in the same folder — Enforce hard rules supplementing the build/script gotchas here.
- The mod implementation checklists note, now in `skills/dayz-mod-workflow/references/checklists.md` and `error-catalog.md` in the same folder (the note's E20 to E31 are E24 to E35 there) — recurring error catalog (E01–E31) and anti-crash engine minimums.
- The animations, creatures and weapons note, now in `skills/dayz-animation-pipeline/references/creature-animation.md` and `skills/_shared/ai/creature-animation.md` — expands animation verdict with VERIFIED identifiers against vanilla.
- The p3d inspector memory and selection bugs note, now in `skills/dayz-p3d-inspector/references/round-trip-caveats.md` and `skills/_shared/models/selections.md` ("Membership lost by tools") — RE gap detail in ODOL v55 reader mentioned below.

## Verified limitation — ODOL v55 reader: anims section does not parse (added 2026-05-25)

Confirmed 2 times independently on 2026-05-24/25 (Claude on kt_roadkill_armed
+ Codex C1 in the same session): the external ODOL reader (ODOL→MLOD converter, not in this repo) **does
not parse the animation section in v55 format**. The desync is NOT in `AnimationClass`
(a patch there did not resolve it). Practical consequence:

- Do NOT retry recovering exact offsets/sources of dampers/anims from a `.p3d`
  binarized v55 until the reader is fixed — it is a reverse-engineering hole
  that already cost time twice.
- Alternative routes: recover those anims by inspecting the binarized file **after**
  own rebuild, or treat them as deferrable cosmetics (R26: do not eyeball).
- Reader dependency: `odol_reader.py` needs its sibling modules
  (`math_types.py`, `bis_reader.py`, `lzo_decompress.py`) in the same scripts
  folder of the external converter. Copying the loose script fails (happened to Codex).

Pending proposal (NOT applied — converter `SKILL.md` is in
`skills-plugin` read-only path from sandbox): replicate this limitation inside
SKILL.md itself via a session with write access to the plugin (or draft in `skills-drafts/`).
Cross-reference: the author's session notes of 2026-05-25, item PB-010 (not in this repo).

## Checked on `P:\`

Opened on 2026-11-17. A line here confirms only what it says; the verdicts above stay the author's.

- `MakeScreenshot` is still declared, at `P:\scripts\1_core\proto\proto.c:142`. That it is broken is the author's measurement.
- `SetObjectTexture` is declared at `P:\scripts\3_game\entities\entityai.c:2881`. Neither `SetObjectTextureGlobal` nor `CallExtension` occurs anywhere in `P:\scripts`.
- `GetDummyPlayer` is declared at `P:\scripts\3_game\gameplay.c:310`.
- `ThrowPhysically` is declared at `P:\scripts\3_game\entities\inventoryitem.c:26`; see `technical-notes.md` for the full pattern.
- `MessageStatus` is declared at `P:\scripts\4_world\entities\manbase\playerbase.c:6924`.
- `PrintToRPT` is declared at `P:\scripts\1_core\proto\endebug.c:99`.
