# DayZ: verified capabilities and feasibility verdicts

Covers what has already been tried and ruled out (screen capture from a mod, `CallExtension`, runtime textures), debris and dynamic item physics verdicts, the two animation systems, a limit of ODOL v55 readers, and a list of config and script gotchas.

Status: verdicts and gotchas measured while building five mods (LF-COM, Crate, LF_VStorage, LF_PowerGrid, LF_Transfer; their source is not in this repo). Not yet checked on `P:\` line by line; the facts checked on 2026-11-17 are listed under "Checked on `P:\`" at the end. Third-party facts name the product they are about.

The verdicts below each cost a full investigation (reading all of `P:\`, reading the Community Framework and Dabs Framework sources, test spikes). The goal is not to repeat an investigation that is already closed.

## Verdict: pixels CANNOT be captured from a pure DayZ mod

Investigated for LF-COM, a mod for an in-game photo feed. Firm conclusion after reviewing all of `P:\` and the Community Framework and Dabs Framework sources (neither has a capture, bitmap or readback API):

- **Retail DayZ does not allow reading the framebuffer from script.** It is an
  intentional block by Bohemia (anticheat / platform control).
- **`CallExtension` (native DLL) is not in the DayZ public API.**
  It exists in Arma 3, not in DayZ. BattlEye blocks client-side extensions and
  there is no whitelisting process. No Workshop mod is known to
  ship a client-side DLL.
- **`MakeScreenshot` is broken since 1.19** and remains broken in 1.29.
- **`Workspace.SaveScreenshot()` does NOT exist**; do not assume it.
- **`SetObjectTexture` is local/client-only** in DayZ Enforce Script. `SetObjectTextureGlobal`
  does not exist (that is Arma 3 only). `r2t` surfaces are
  config-bound (statically declared in `config.cpp`, tied to memory
  points), **not creatable at runtime** from script, and require active PiP.
  Read in `entityai.c` of build 1.24.157551.

**Architectural decision derived (LF-COM)**: the viable path is
**PBO + launcher companion `.exe` + web backend**. The launcher polls the
Steam screenshots folder and a flag file in `$profile:\LFCOM\`,
converts PNG→EDDS with Bohemia's `ImageToPAA.exe`, and the mod loads the EDDS
with `LoadImageFile`.

### Camera/preview APIs that DO work (measured in game)

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
  The full pattern with citations is in `technical-notes.md`.
- **PhysX silently ignores Geometry LOD components < 0.5 m.**
  That is why a ball test object was made 50 cm. Production trick: an
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

## Gotchas measured in mods

These caused repeated waves of compilation errors or bugs. The Enforce Script
hard rules in `skills/enforce-script-reference/references/hard-rules.md` and the error catalog in
`skills/dayz-mod-workflow/references/error-catalog.md` supplement them.

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
- Bohemia feedback tracker T148506: `inventorySlot` string-vs-array when porting classes.
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

## Verdict: DayZ animation (researched 2026-05-20)

**There are TWO animation systems in parallel — do not confuse them:**

- **Config-driven** (`model.cfg` + `config.cpp` + script): props/objects —
  doors, levers, wheels, hide-on-attach. Types `rotation(X/Y/Z)` and
  `translation(X/Y/Z)`. `SetAnimationPhase`. **100% text,
  producible without DayZ Tools.** The `hide` type is used by a working
  third-party vehicle mod; confirm `hideValue` against vanilla before relying on it.
- **Skeletal**: characters/weapons use the **Enfusion `.txa`→`.anm`** pipeline
  (NOT RTM). RTM is legacy (Real Virtuality), for legacy props/man.

**Sandbox/GUI seam (the critical part):** a Linux sandbox without `P:\` or DayZ
Tools can produce Layer 1 (config) entirely. Layer 2 (open intermediaries:
**SEAnim**, an open format, and headless Blender keyframes) is assisted there. Layer 3 (Workbench,
FBXToRTMGui, PBO signing, in-game test) needs Windows and a GUI.

**Walls:**
- **Only one player animation mod at a time** — two crash client/server
  (Enfusion engine limit, not policy). Does not affect object animation.
- **Writing RTM directly is reverse engineering** (Bohemia publishes an explicit legal notice on it). No
  open-source pure Python RTM writer is known; only Blender add-ons write RTM.
- **`.anm` is proprietary**; DayZATool writes it (closed binary). **SEAnim
  IS an open format** → programmatic path (writer verified by round-trip
  in `skills/dayz-animation-pipeline/scripts/seanim_writer.py`).
- Skeleton `OFP2_ManSkeleton`, exact bone names or RPT logs
  `Bone X doesn't exist`. Whether the vanilla skeleton can be restructured is
  `[TBD-verify]`; assume it cannot.

**Real tools (all Windows):** Arma3ObjectBuilder (Blender 4.2+,
export RTM), FBXToRTMGui.exe (DayZ Tools), DayZATool (`.anm`↔SEAnim),
DayZAnimationPluginDemo (Blender→`.txa`), the `io_anim_seanim` Blender add-on (SEAnim).

**Pending `[TBD-verify]`** (confirm against `P:\` before trusting):
types `translationModelX/Y/Z` and `direct`; DayZ engine sources `doors`/`damage`;
exact signature of `SetAnimationPhase`; Blender→DayZ scale factor; whether DayZ/Arma
Blender plugins run headless in sandbox; vanilla IK `.anm` catalog
(Hatchback_02 paths); whether FBXToRTM comes with DayZ Tools or only Arma 3.

**Seam clarification (added 2026-05-20):** the `.p3d`
geometry side that an animation needs — the named selection being animated and the
pair of memory points defining the `axis` — **is producible without Object Builder or Windows**.
Route: `dayz-p3d-inspector` (extract → Recipe JSON → edit
memory points/axes/selections → rebuild `.p3d`) or `dayz-model-pipeline` (py3d
assembly); an external ODOL→MLOD converter first if the `.p3d` is ODOL (binarized, not
editable); `dayz-p3d-audit` to verify winding/`Component01`. Caveats: py3d
edits MLOD; adding memory points and the axis is trivial, but **authoring a new named
selection grouping specific geometry** relies on the context of
`dayz-model-pipeline`. The only Layer 3 steps left for Layer 1 work are PBO signing and the in-game
test.

The `dayz-animation-pipeline` skill (`skills/dayz-animation-pipeline/`) carries the full
pipeline (config-driven and skeletal), with `hideValue` as a must-verify item and the seam
clarification above.

## Related

- Skills: `enforce-script-reference`, `dayz-build-pbo`, `dayz-model-pipeline`,
  `dayz-p3d-audit` — cover most of modding; this note supplements them with
  what was measured in mods and is not in them.
- `skills/_shared/enscript/patterns/modded_class.md` ("Server-only overrides need a stub in the base class") — the server-only stub pattern
  (a bug pattern related to `#ifdef SERVER`).
- `skills/enforce-script-reference/references/review-and-troubleshooting.md` and `hard-rules.md` in the same folder — Enforce Script hard rules supplementing the build and script gotchas here.
- `skills/dayz-mod-workflow/references/checklists.md` and `error-catalog.md` in the same folder — the recurring error catalog and the anti-crash engine minimums.
- `skills/dayz-animation-pipeline/references/creature-animation.md` and `skills/_shared/ai/creature-animation.md` — expand the animation verdict with identifiers checked against vanilla.
- `skills/dayz-p3d-inspector/references/round-trip-caveats.md` and `skills/_shared/models/selections.md` ("Membership lost by tools") — detail of the ODOL v55 reader gap described below.

## Verified limitation — ODOL v55 reader: anims section does not parse (added 2026-05-25)

Confirmed twice independently on 2026-05-24/25 on a binarized v55 vehicle model: the external
ODOL reader (an ODOL→MLOD converter, not in this repo) **does
not parse the animation section in v55 format**. The desync is NOT in `AnimationClass`
(a patch there did not resolve it). Practical consequence:

- Do NOT retry recovering exact offsets/sources of dampers/anims from a `.p3d`
  binarized v55 until the reader is fixed — it is a reverse-engineering hole
  that already cost time twice.
- Alternative routes: recover those anims by inspecting the binarized file **after**
  own rebuild, or treat them as deferrable cosmetics (do not eyeball them).
- Reader dependency: `odol_reader.py` needs its sibling modules
  (`math_types.py`, `bis_reader.py`, `lzo_decompress.py`) in the same scripts
  folder of the external converter. Copying the loose script fails.

## Checked on `P:\`

Opened on 2026-11-17. A line here confirms only what it says; the verdicts above are not checked here.

- `MakeScreenshot` is still declared, at `P:\scripts\1_core\proto\proto.c:142`. That it is broken was measured in game, not checked here.
- `SetObjectTexture` is declared at `P:\scripts\3_game\entities\entityai.c:2881`. Neither `SetObjectTextureGlobal` nor `CallExtension` occurs anywhere in `P:\scripts`.
- `GetDummyPlayer` is declared at `P:\scripts\3_game\gameplay.c:310`.
- `ThrowPhysically` is declared at `P:\scripts\3_game\entities\inventoryitem.c:26`; see `technical-notes.md` for the full pattern.
- `MessageStatus` is declared at `P:\scripts\4_world\entities\manbase\playerbase.c:6924`.
- `PrintToRPT` is declared at `P:\scripts\1_core\proto\endebug.c:99`.
