# Proxies, get-in and detachable parts: the contract

How proxies are placed on a working car, the four config and model layers a detachable door, hood or trunk needs, what a seated player's action must register, how to hide an attachment proxy from script, and what the first-person View Pilot LOD of a shell and proxy vehicle must carry.

> Status: field notes measured on third-party mods, each named in its entry (Tyson89 Landrover as the working control, LFHeli OH-1 and HH-60G, SUB_BRZ, MercedesAMGLF, LFQuad, LFQuad2, LFQuad3, GunRacks, the H2R motorbike import). Those measurements were not repeated here. The vanilla script line numbers in this file were opened on this repo's `P:\` (a 1.30 build) and corrected where they had moved; a citation written with its full `P:\` path is checked by the repo tests as well, and a number that follows a mod's own file (`LFQuad.c:176-189`, `Tyson89-Landrover\scripts\config.cpp:65-77`) is the note's own. Tags such as SP-096 or LL-172 are the notes' own lesson numbers, and `CLAIM-...` tags are the notes' own claim register. Paths such as `<vehicle-import>\...`, `SUB_BRZ_dev\...`, `LFHeli_dev\...` or `AI/20_Knowledge/...` point into those mods' work folders and the author's notes, which are not part of this repo. "Invariant N", "preflight #N" and "#N" all mean the numbered invariants; `skills/dayz-vehicles/SKILL.md` lists which file holds each number. Other skills are named by skill name, each a folder under `skills/` (dayz-model-pipeline, dayz-test-ingame, dayz-texture-pipeline, dayz-mcp-verify, enforce-script-reference).

Related file in this pack: `get-in-actions-and-proxy-pose.md` (the get-in condition chain, action registration and which anchor places the occupant).

## Vanilla anchors checked on `P:\`

- `ProxyVehiclePart` is declared at `P:\DZ\vehicles\wheeled\config.cpp:23901` with `scope=1`, `simulation="ProxyInventory"`, `autocenter=0`, `animated=0`, `shadow=1`, `reversed=0`. The Landrover mod quoted below declares its own copy with `scope=2`; every other value is the same.
- `ProxySedanWheel` (`P:\DZ\vehicles\wheeled\config.cpp:23969`) is a vanilla example of layer 2: a proxy class with a `model` and an `inventorySlot[]`.
- The base `OnDebugSpawn` is at `P:\scripts\3_game\entities\entityai.c:3955`, and the sedan's override at `P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c:415`.
- `CanBeUsedInVehicle` returns false in `ActionBase` (`P:\scripts\4_world\classes\useractionscomponent\actionbase.c:361`).
- `ActionOpenCarDoors` and `ActionCloseCarDoors` are added to the player's input action map at `P:\scripts\4_world\entities\manbase\playerbase.c:1714`.
- `CrewCanGetThrough` is at `P:\scripts\3_game\vehicles\transport.c:724` (the note was written with `:727`) and is consulted at `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:54`.
- `HideSelection` is at `P:\scripts\3_game\entities\entityai.c:3355`.

Nothing in this file is superseded: these are active lessons, ordered by topic instead of by date. The numbered get-in invariants are in `invariants-get-in-and-seats.md`, the vanilla crew and attachment API in `attachments-and-crew.md`, and the curated View Pilot contract in `view-pilot-and-first-person.md`.

---

## REGEN-FROM-glTF BODY + PROXY-SPLIT / GET-IN RADIAL + LOD LADDER -> `vehicle-structural-parity.md`

Regenerating a high-poly body from glTF/FBX and splitting it into proxies to beat the 65535 resolved-vertex ceiling (glTF->DayZ winding tautology, proxy-placement identity-frame trap, the confirmed model-space + no-`.p3d` + measured-frame convention), and the proxy-body **get-in radial + LOD ladder** (script-module binding, the geometric get-in blocker, the DECISIVE inward-wound seat ComponentNN + point flags `0x0000003F`, reversed-wheel `angle1`, shell+proxy LOD ladder) are structural parity and now live in **`vehicle-structural-parity.md`** (Appendix "REGEN-FROM-glTF + GET-IN RADIAL / LOD ladder"). That file is their declared source of truth.

## Proxy placement convention - measured on a working reference car (SP-091, added 2026-07-26)

Two full build+test cycles were burned on LFHeli OH-1 guessing this from the broken model alone.
The answer was one probe away: read a car that WORKS. Reference used:
`SUB_BRZ_dev\_references\Tyson89-Landrover` (MLOD v257, py3d reads it directly, no debinarize).

MEASURED on Landrover.p3d LOD0 (18 proxies):
- **NOT ONE has its anchor at the origin.** Every anchor sits at the real target position:
  `Landrover_Wheel [0.8746, 0.4513, -1.5638]`, `Landrover_Driver_Door [0.888, 0.6492, -0.8629]`,
  `Landrover_Trunk [0.0021, 1.1487, 2.5139]`.
- **NOT ONE has an identity frame (0 of 18).** The standard frame is `[[-1,0,0],[0,0,1],[0,1,0]]`;
  the opposite side mirrors it as `[[1,0,0],[0,0,-1],[0,1,0]]`; the spare wheel uses its own rotation.
- Sub-models are authored in **proxy-local space**, origin at the attachment point:
  `Landrover_Wheel |center| = 0.000 m`, `Landrover_Trunk 0.000 m`,
  `Landrover_Hood 0.726 m` and `Landrover_Driver_Door 0.821 m` (they pivot on their hinge).

RULES:
1. Proxy anchor = target position in HOST coordinates. Anchor at origin is a defect.
2. Sub-model geometry authored near ITS OWN origin (< ~1 m). A sub-model whose bbox center sits
   2-7 m away is authored in host coordinates - that is the defect, and it is the one worth gating.
3. The frame `[[-1,0,0],[0,0,1],[0,1,0]]` is the NORMAL neutral, not a smell: the crew proxies that
   work carry it too. Numerical identity NEVER appears in a working model - forcing it makes
   placement WORSE (verified in-game on OH-1).
4. A zero-size crew marker proxy (~463 bytes) is immune to any frame rotation because its geometry
   sits at the origin. Do not infer the convention from those - use a geometry-bearing proxy.
5. Doors on a working vehicle are PROXIES with their own .p3d anchored at the hinge, not baked
   geometry driven by a bone. Consider that before designing bone-driven doors.

METHOD RULE (the expensive lesson): calibrate every gate rule against a model that WORKS before
trusting it. Three rules were written from the broken model; two were false positives that would
have red-flagged every correct model. The reference car killed both in one probe.

Gates implementing this: `LFHeli_dev\tools\import_gates\proxy_placement_gate.py` (P1 anchor at
origin, P8 sub-model authored in host space, P9 normal/winding coherence) plus
`texture_binding_gate.py` (one .rvmat must not carry two base textures).

## Detachable parts (doors/hood/trunk): the FOUR-layer contract, and three rules it corrects (SP-098, added 2026-07-28)

Measured on a working control, `SUB_BRZ_dev\_references\Tyson89-Landrover` (MLOD v257, py3d reads it
directly). LFHeli OH-1 spent weeks on "the door does not animate" with the full script+model contract
verified, because the project only ever knew layer 3 below.

### The contract is four layers, not one

1. **`CfgSlots`** (`Tyson89-Landrover\scripts\config.cpp:65-77`)
   ```cpp
   class Slot_Landrover_Driver_Door {
       name = "Landrover_Driver_Door";
       displayName = "...";
       selection = "doors_driver";        // <-- the ANIMATION BONE selection
       ghostIcon = "set:dayz_inventory image:doorfront";
   };
   ```
   `selection` is the binding between "the attachment is mounted" and "the proxy is drawn".

2. **`CfgNonAIVehicles` / `ProxyVehiclePart`** (`Tyson89-Landrover\scripts\config.cpp:80-100`) —
   THE LAYER PEOPLE MISS.
   ```cpp
   class ProxyAttachment;
   class ProxyVehiclePart : ProxyAttachment {
       scope=2; simulation="ProxyInventory"; autocenter=0; animated=0; shadow=1; reversed=0;
   };
   class ProxyLandrover_Driver_Door : ProxyVehiclePart {
       Model = "\Landrover\proxy\Landrover_Driver_Door.p3d";
       inventorySlot = "Landrover_Driver_Door";
   };
   ```
   Without it the engine does not resolve the host's `proxy:\...` as an attachment proxy. Note
   `autocenter=0` appears HERE too: vanilla declares it in THREE places - the sub-model's visual
   LOD, the sub-model's Geometry LOD, and this config class.

3. **Item class** `Landrover_Driver_Door : CarDoor` with `Model`, `inventorySlot`, `hiddenSelections`,
   `weight`, `itemSize[]`, `physLayer`, `DamageSystem` (`Tyson89-Landrover\config.cpp:70-95`).

4. **Vehicle**: the slot name inside `attachments[]`, plus `class Doors` in the vehicle DamageSystem.

**Host proxy triangle: DOUBLE membership.** Measured on `Landrover.p3d` LOD0, the 3 points of
`proxy:\Landrover\proxy\Landrover_Driver_Door.001` belong 3/3 to `doors_driver` (the bone) AND 3/3
to `Landrover_Driver_Door` (the slot name). A proxy wired only to the bone animates but is not
attachment-aware.

**A detachable part is a physical ITEM.** It can be dropped on the ground, so its `.p3d` needs real
special LODs, not an empty Geometry. Measured: `Landrover_Driver_Door.p3d` = visual `463/754`,
Geometry `32/24`, Memory `7/0`, ViewGeo `32/24`, FireGeo `72/56`, with `autocenter=0` on the visual
LOD and on Geometry. Budget the item LODs before promising the feature.

Custom inventory slots are the T148506 family (the enforce-script-reference skill): if the slot name and the
`inventorySlot` string diverge, the item never attaches and the proxy never draws.

> Pointer (CHANGE-1): the corrected SP-093 rule is in `rip-geometry-and-winding.md`, "Rewriting a proxy triangle".

> Pointer (CHANGE-1): the corrected SP-097 rule is in `rip-geometry-and-winding.md`, "`autocenter=0`: corrected scope by LOD, host, and submodel".

### `binarize` is NOT deterministic - never gate on ODOL byte identity

Two runs of `binarize.exe -always` over the same source, same flags: the shell came out
`2,886,719 b` / `8C290530214C...` and `2,763,097 b` / `0705207DB7F0...`; the interior `1,062,412 b`
vs `1,062,417 b`. The two small rotor models were byte-identical, so the effect scales with model
size. Semantically the two shells match (66/66 `model_info` fields, same faces/selections/properties
per LOD); the divergence is encoding/compression order, and between builds the order of faces and
sections changes too (SP-194 of the `/dayz-build-pbo` skill, measured with AddonBuilder; section order was not compared
on the OH-1). The H2R import (2026-10) saw it with `binarize.exe` called directly: a rebuild from
byte-identical MLODs kept every per-LOD count while its face arrays differed in every resolution LOD and
the ViewPilot, and between two of its builds the LOD 0 section of `dashboard` went from index 175 to 204
with the same faces, section count and material set (claim: CLAIM-BINARIZE-SECTION-ORDER-130).

Rule: gates over ODOL compare SEMANTICS (per-LOD counts, selections, properties, proxies, centres),
never bytes or section indices (between builds, key on SP-194's unordered multiset). Hash identity is
still valid for MLOD, which the pipeline writes itself. Re-read any historical "the ODOL came out
byte-identical" claim with this in mind.

Origin: LFHeli OH-1 2026-07-28, the session that converted doors to proxied attachments after the
user pointed out that a vanilla car only draws the door proxy when the door is attached.

### Two traps that follow immediately from converting a baked part into an attachment

Both bite the moment the part becomes an attachment, and both look like "my model change
broke the vehicle".

**1. A detachable part is INVISIBLE on every debug/admin spawn until something attaches it.**
`CreateObject`, VPP/admin-tool spawns and MCP-style bridge spawns do not populate attachment
slots - that is why a VPP-spawned vanilla car has no wheels. The moment you move a door from
baked hull geometry to an attachment, a spawned vehicle shows an empty doorway, and it reads as
a regression when it is the contract working.

The hook is `OnDebugSpawn()` (`P:\scripts\3_game\entities\entityai.c:3955`, with
`OnDebugSpawnEx(DebugSpawnParams)` delegating to it at `entityai.c:3937-3939`). Two source-verified patterns:

- explicit `CreateAttachment` per part - `LFQuad.c:176-189`:
  ```c
  override void OnDebugSpawn()
  {
      EntityAI entity;
      if (Class.CastTo(entity, this))
      {
          entity.GetInventory().CreateAttachment("CarBattery");
          entity.GetInventory().CreateAttachment("SparkPlug");
          entity.GetInventory().CreateAttachment("LFQuad_Wheel_Front");
          // ...
      }
  }
  ```
- vanilla car, `CreateInInventory` per part - `P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c:415-436`
  (`SpawnUniversalParts(); SpawnAdditionalItems(); FillUpCarFluids();` then one call per door/wheel).

The `EntityAI` base implementation is config-driven instead: it reads the type's `attachments[]`
and scans `CfgVehicles`/`CfgMagazines`/`CfgWeapons` for any class whose `inventorySlot` matches,
then `CreateInInventory`s it (`entityai.c:3955-4009`). Calling `super.OnDebugSpawn()` therefore
attaches per-type from config with no per-airframe code - useful when one script base serves
several models. Note the vanilla cars deliberately do NOT call super; they list parts explicitly.

**2. `attachments[]` depends on the PBO boundary; `+=` is not an unconditional rule.**
> Superseded text history: `history/superseded-family-b-rules.md`, section "attachments[] += as an unconditional rule".
Within the same source config tree, `+=` can retain parent slots. When parent class comes from another already compiled PBO, that list is not a safe contractual basis: materialize in the child class the COMPLETE list of vital and own slots. This corrects the previous rule with the case verified in `AI/20_Knowledge/dayz-mod-implementation-checklists.md:234-240` (E28).

The gate does not look for a `+=` token: it inspects the effective list after compile/config-dump and verifies battery, ignition, radiator, wheels, and each declared door/part. A door change cannot silently remove a vital slot. Also maintain the independent check that each declared part appears in the `OnDebugSpawn` path; they are distinct contracts.

## In-vehicle actions need TWO registrations, and a proxied part is your placement oracle (SP-123, added 2026-07-28)

### An action offered to a SEATED occupant must be registered in two places

Measured on LFHeli OH-1, which spent a build cycle on "the close-door action does not appear
when seated" with the action class already correct.

1. The action must opt in: `ActionBase.InitConditionMask` only sets `ACM_IN_VEHICLE` when
   `CanBeUsedInVehicle()` returns true (`actionbase.c:110`), and the base returns false
   (`actionbase.c:361`). Any world action inherited from `ActionInteractBase` is therefore
   MASKED OUT the moment the player boards.
2. A seated player has no cursor target on the vehicle carrying them, so the target contract
   is `CCTNone` plus `HasTarget()` false - the shape vanilla uses in `actioncardoors.c:20` (`CCTNone`)
   and `actioncardoors.c:120` (`HasTarget()` returns false).
3. **Both registrations are required, and the second one is the one people miss:**
   - `ActionConstructor.RegisterActions` - builds the instance into the global pool.
   - `PlayerBase.SetActions(out TInputActionMap)` - `AddAction(MyAction, InputActionMap)`.
     Vanilla puts `ActionOpenCarDoors`/`ActionCloseCarDoors` right there
     (`playerbase.c:1714-1715`).
   Registering only in the constructor builds an action the manager never offers, because
   `FindContextualUserActions` walks the player's `InputActionMap` per input, not the pool.

Vanilla splits inside/outside into separate classes (`ActionCloseCarDoors` vs
`ActionCloseCarDoorsOutside`); copy that split rather than trying to make one class serve both.

**Ship the opening half too.** If entry/exit is gated on the door being open, an inside-only
CLOSE action traps the occupant. Pair it with an inside OPEN action, and keep one exemption in
the gate: a door that is NOT MOUNTED must leave the seat escapable, because no action can open
what is not there.

### A proxied part is the first correctly-placed reference on the host - use it as an oracle

When a host renders wrong, there is usually nothing trustworthy to measure it against. Parts
drawn through attachment proxies are placed by the engine from the entity transform, so they
ARE trustworthy, and the disagreement localises the fault:

- proxies agree with each other and disagree with the host -> **the host is the broken one**.
  Do not "correct" the proxy anchors to match: you would deform the correct piece, and the
  error changes with the host's state.
- On LFHeli OH-1 the doors, both rotors and the interior all followed the aircraft into the
  air while the fuselage stayed at ground level. The doors had just been migrated to proxies,
  and became the reference that finally localised a render bug open since 2026-07-20.

Corollary: `scene_raycast` in `rvproxy` mode returns the GEOMETRY LOD, not the visual mesh, so
it cannot adjudicate a visual misalignment. On a coarse collision hull it reports a surface
tens of centimetres inside the visible skin. Use it for collision questions only.

## (added 2026-08-01) A shared vehicle-core source turns "deploy ordering" gates into fiction

When one Enforce core file serves several vehicle lines (LFHeliCore's `LFHeli_Base.c` serves
OH-1 and HH-60G), any patch in it — even gated by `ConfigIsExisting("vehicleProp")` so only one
line executes it — DEPLOYS whenever ANY line rebuilds the core PBO. A sequencing rule like "do
not deploy the core patch until the model ships its matching memory points" does not survive
the sibling line's next rebuild. Case: LFHeli 2026-08-01 — the OH-1 line rebuilt and deployed
the shared core for its own fixes, and the HH-60G get-in patch went live with it, pointing at
ten `lfheli_con_*` memory points the deployed model does not emit (verified by scanning the
deployed PBO bytes for the patch symbols, not by mtime).

1. A core-side patch that requires a model-side contract (memory points, selections, bones)
   must be RUNTIME-TOLERANT: `MemoryPointExists` fallback to the previous mapping, so the
   patch stays inert until the model actually ships the contract. Deploy-order gates across a
   shared source are not enforceable by anyone.
2. Alternatively, land model and core in the same session/build — never leave a
   contract-dependent patch sitting in shared source "waiting" for its model.
3. When auditing what is live, verify the deployed PBO CONTENT (byte scan for the patch's
   symbols). The sibling line's handoff tells you the core changed; only the bytes tell you
   what rode along.

## Phantom vehicle command blocks ALL vanilla get-in after a client crash while seated (added 2026-08-02)

Symptom: the get-in prompt SHOWS but accepting does nothing - both seats, zero RPT/script-log
trace, and it survives rebuilds because nothing in the mod is broken. Mechanism:
'ActionGetInTransport.ActionCondition' runs on BOTH sides; the CLIENT player (clean) shows the
prompt, but the SERVER-side player still carries a non-null 'GetCommand_Vehicle()' restored
from player storage after a client crash while seated. The first server gate
(actiongetintransport.c:42-43) rejects silently, and a null 'StartCommand_Vehicle' in Start()
(actiongetintransport.c:104-105) produces no log either.

Checklist BEFORE suspecting model/proxies/config for a get-in regression:
1. Check the previous run's client profiles for a 'crash_*.log' - a crash while seated is the
   phantom's birth certificate.
2. With dayz-mcp available: 'query_get_in_condition' returning 'first_block=already_in_vehicle'
   with the player standing in the open = phantom confirmed; 'vehicle_get_in_client' (owner-side
   direct, skips the action gates) seating fine = seat contract and model are healthy.
3. The phantom clears on a clean logout cycle. "It fixed itself next session" is the signature
   of THIS bug, not of a flaky model.

Origin: LFHeli OH-1 gate D 2026-08-02 (GD-1): a full regression gate was misattributed to a
model surgery whose Geometry/ViewGeo/FireGeo/Memory LODs were byte-identical pre/post.

## ViewPilot (1100) of a shell+proxy car MUST carry the body geometry, not only proxy tris (SP-189, added 2026-08-06, SUB_BRZ B-3)

Symptom: on entering the vehicle in FIRST person the body goes invisible for
seconds (vanilla never does). Measured root cause: the shell's 1100 LOD held 7
faces = only the proxy triangles (interior/doors/wheels), zero own geometry,
while the vanilla control (civiliansedan MLOD) carries 11,977 REAL faces there
(interior + body + glass) plus its 13 proxies. The engine switches the shell to
the 1100 on mount; with nothing but proxy anchors in it, the body vanishes
until proxies resolve. The generator's "subset lives in the interior file"
design never materialized as a subset (brz_int 1100 = its full visual LOD).

Fix pattern (fix_b3_viewpilot.py, s45): merge the shell LOD0 into the 1100 —
own geometry with remapped point/normal indices, named selections via
get-or-create (camo/light_* keep working in 1PP), plus the LOD0-only chunk
proxies copied VERBATIM (points+face+selection; add_proxy would lose the
frame). Exclude faces AND anchor points of proxies the 1100 already has.
Gates that must pass: original proxy sels intact (1 face/3 pts), proxy set ==
originals + copied, bone companions cardinality unchanged, facenormals <=
32768, resolved-verts printed vs the ~16k design budget. Binarize preserved
the merge exactly (22,849 faces / 11 proxies in the ODOL).

> **Capacity correction (SP-182, added 2026-08-31).** The `facenormals <= 32768`
> check above is superseded as a universal engine/load gate. Keep that number only
> when it is declared as a local historical design budget. For a load verdict, first
> count the known-good blob extracted from the deployed PBO on the same `MLOD`/`ODOL`
> route, then use the candidate's three-state `binarize` verdict. A warning threshold
> alone never authorizes geometry reduction, and the absent-1100 path below must not
> choose its seed from this number.

Applies to every car built by this pipeline — but **the defect has TWO shapes and
they need different fixes**, so census before assuming which one you have.

> **Corrected 2026-08-22.** This paragraph used to say «MercedesAMGLF has the same
> proxy-only 1100 — same latent defect». It does not. Measured by opening the shell
> with py3d 1.4.0: `mercedes_amglf.p3d` carries **10 LODs and none of them is 1100** —
> resolutions 0, 1, 2, 3, 4, 10000, then the canonical 1e13 Geometry, 1e15 Memory,
> 6e15 ViewGeometry and 7e15 FireGeometry. There is no ViewPilot LOD to be
> proxy-only. Sending the next car to the merge fix on that sentence means merging
> into a LOD that does not exist.

Day-1 check for car #2: census the shell 1100 vs civiliansedan BEFORE first in-game
(`b3_viewpilot_census.py`), and let the census have **three** outcomes, not two:

| census | what it is | fix |
|---|---|---|
| populated | 1100 with its own geometry | none |
| **proxy-only** | 1100 exists but only carries proxies | merge above |
| **ABSENT** | no 1100 (MercedesAMGLF, measured) | **create** the 1100; merge does not apply |

The creation procedure —which visual LOD to copy from, against what facenormals
budget, where to insert it, and in what order relative to texturing— is described
in the ledger (SP-191) but **has not been validated here**, so it is not transcribed: if
you encounter the ABSENT case, read it there and measure it before trusting it.

## Creating an absent ViewPilot is a lifecycle, not a blind LOD copy (SP-191, added 2026-08-31)

**[OFFLINE VERIFIED; IN-GAME VALIDATION STILL REQUIRED]** Keep the three-way census
above. For `ABSENT`, create resolution 1100 only through the authoritative assembler,
or through an idempotent post-fix that is reapplied after texturing. A pre-texture copy
can preserve `texture=(none)` and silently diverge from later visual edits.

Use a complete visual LOD only as the seed. Choose it by the current curated ViewPilot
contract in `view-pilot-and-first-person.md`: preserve required structural faces, evaluate the complete
assembled first-person scene, and enforce material ownership. Do not choose the source
by a fixed facenormal ceiling. Copy geometry with remapped indexes; preserve proxy
triangles and frames verbatim; preserve named selections, sharp edges and LOD
properties. Never rebuild existing proxies with a convenience constructor that changes
their frame.

Fail before writing or backing up if 1100 already exists. Before save, require source
parity for the selected seed, all expected proxies and selections, and a valid curated
content verdict. After save, re-read the model, prove every other LOD byte/semantic
snapshot unchanged, and require a second run to make no change. The final gate remains
an in-game first-person cycle; this offline lifecycle does not claim that validation.

## Detachable extraction is proved by material and space, not selection count (SP-129, added 2026-08-31)

**[OFFLINE VERIFIED]** A shell can report only the proxy triangle under `door_1`
and still retain the whole window because the window belongs to a global `glass`
selection. For every visual LOD, count shell faces inside the detached part's
footprint by material, place the submodel at its proxy anchor, and match candidate
face twins in world/model space. A matched shell face is a duplicate; an unmatched
face is legitimate shell. Derive the distance tolerance from the valley in the
measured bimodal distance histogram rather than a round literal.

Removing the duplicate can expose a pre-existing submodel placement error, so a
more visible hole after cleanup is not proof of regression. A zero residual
between the submodel and the volume used by its own authoring transform proves
lineage only; it shares the producer's frame and does not adjudicate engine render.
The final placement verdict remains in-game.

## Continuous actions and input exclusion while seated (SP-218, added 2026-08-31)

- **[IN-GAME VERIFIED]** A seated `ActionContinuousBase` must use a command modifier
  whose progress callback runs in a vehicle. The vanilla precedent is
  `CMD_ACTIONMOD_STARTENGINE` (`actionstartengine.c:14`); a walking/open-door
  modifier can animate while never reaching `OnFinishProgress`.
- For an interface that uses `AddActiveInputExcludes(...)`, interrupt any action
  already in progress with `ActionManagerClient.RequestInterruptAction()`
  (`actionmanagerclient.c:1341`). Excluding input first can swallow the release,
  wedge the action manager, and suppress every later action. Record ownership and
  remove only that interface's exclude idempotently on close, force-close, abort
  and teardown; `SetDisabled(true)` alone does not block action input.
- During an exclude, `UAInput.LocalValue()` reads zero. `KeyState`
  (`ensystem.c:291`) and `GetMouseState` still read physical input, but `KeyState`
  ignores user rebindings; treat it as a diagnostic or add binding-aware handling.
- The preferred seated-camera path keeps the pawn possessed, overrides the vehicle
  camera, and gates get-out in `ActionGetOutTransport.ActionCondition`. It needs no
  broad input exclude, avoiding the transitive zeroing of bound aiming axes.


## Hiding an attachment proxy from script: the two config halves (added 2026-09-04, LFQuad3)

**[SOURCE-VERIFIED, not yet in-game]** A cargo/attachment proxy baked into the p3d
is drawn whether or not its slot holds an item. `HideSelection(name)` looks like
the fix and silently does nothing on its own:

```c
// scripts/3_game/entities/entityai.c:3355
void HideSelection( string selection_name )
{
    if ( !ToDelete() )
        SetAnimationPhase ( selection_name, 1 );   // 1 = hide, 0 = unhide!
}
```

`SetAnimationPhase` addresses an **animation source**, not a bare selection. The
engine says so in `entityai.c:1430`: *"making them INVISIBLE if they are
configured in models.cfg in such way. These selections must also be defined in
the entity's config class in 'AnimationSources'"*. Without both halves every
call is a no-op — and a no-op that looks like a timing race, which is how a whole
debugging round can be spent on `CallLater` retries that could never have helped.

**Name contract, verified across two mods in this tree that work in game:** the
string passed to `SetAnimationPhase` / `HideSelection` is the **class name in
`AnimationSources`**, which is also the animation's **`source`** in model.cfg. It
is NOT the animation's class name and NOT necessarily the selection name.

| piece | file | example |
|---|---|---|
| source | config.cpp `AnimationSources` | `class rotor_static_hide { source="user"; animPeriod=0.001; initPhase=0; };` (`hh60g_pack_v19/config.cpp:74`) |
| animation | model.cfg `Animations` | `class main_rotor_static_hide { type="hide"; source="rotor_static_hide"; selection="main_rotor"; minValue=0; maxValue=1; hideValue=0.5; }` (`LFHeli_HH60G/models/model.cfg:67`) |
| call | script | `SetAnimationPhase("rotor_static_hide", staticHide)` (`LFHeliCore .../lfheli_base.c:3381`) |

Naming the three the same also works (A6 base storage / GunRacks use `hideproxy`
for all three), which is why the contract is easy to get wrong by accident: a
mod that happens to use one name everywhere gives no evidence about which name
the engine reads.

- `initPhase = 1` -> hidden at spawn; `initPhase = 0` -> visible. Direction
  verified in game in GunRacks (`GunRacks_mod_dev/GunRacks/config.cpp:611-613`)
  and matching the engine comment above. For a cargo slot that starts empty,
  `initPhase = 1` is the state you want.
- `hideValue = 0.01` with `animPeriod = 0.01` is the near-instant swap copied
  from A6's debinarized `singlegunrack.p3d`.
- Both precedents also declare the hidden selection as a **skeleton bone**. Not
  proven necessary here, but a hide animation that the engine ignores is
  indistinguishable from the unfixed symptom, and each in-game cycle costs
  minutes, so match the precedent unless you have a reason not to.
- Refresh the phase in `DeferredInit` **and** `AfterStoreLoad`
  (`entityai.c:1418`, "called when entity is being loaded from DB or Storage
  (after all children loaded)"), plus `EEItemAttached`/`EEItemDetached`.

## Gating a crew position on an attachment (added 2026-09-04, LFQuad3)

**[SOURCE-VERIFIED, not yet in-game]** To make a seat unusable while something is
mounted, override the gate `ActionGetInTransport` already consults; do not add a
parallel condition.

```c
// scripts/3_game/vehicles/transport.c:724
bool CrewCanGetThrough( int posIdx )

// scripts/4_world/.../actiongetintransport.c:54
if (!transport.CrewCanGetThrough(crewIndex) || !transport.IsAreaAtDoorFreeDiag(crewIndex))
    return false;
```

Vanilla uses it for doors (`civiliansedan.c:226`). For an attachment gate:

```c
override bool CrewCanGetThrough(int posIdx)
{
    switch (posIdx)
    {
        case 0: return true;
        case 1: return FindAttachmentBySlotName("MyMod_backpack") == null;
    }
    return false;
}
```

The null-check idiom is vanilla's (`improvisedexplosive.c:215`,
`return FindAttachmentBySlotName(slotName) != null;`).


## The pilot LOD is assembled by hand: census it by CLASSES and against LOD0 (added 2026-09-05)

A ViewPilot (res 1100/1200) is not a decimation of LOD0: it is a **curated** view, and whatever
whoever assembled it left out does not appear anywhere. Measured on 2026-09-05 across two sibling
mods from the same tree, with **opposite** results:

| | LFQuad3 | LFQuad2 |
|---|---|---|
| body | 25,234 faces (LOD0: 76,044) | 2,294 faces (LOD0: 9,011) |
| dashboard | **complete**: `light_dashboard` 744 faces, same as LOD0 | `light_dashboard` **0** faces (LOD0: 12) |
| attachment proxies | **0 of 7** (only interior and the two crew ones) | 3 of 17 |

The two consequences are gates that lie, and they lie in opposite directions:

- **False GREEN**: "verify that with empty slots no proxy is seen" comes out green from the
  seat whether fixed or not, because attachment proxies aren't there. That check must be done **from
  outside, in third person**.
- **False RED**: "sit down and check if the dashboard lights up" always comes out red on a model
  whose `light_dashboard` never reached the view, even if material and script are perfect.

**The census is performed against LOD0, not in absolute terms.** "0 faces in 1100" does not distinguish *the view
dropped it* from *it never existed*; only the LOD0/1100 pair separates the two classes. In the measured case,
four out of nine light selections would have been misread by looking only at 1100 — they were at 0 across
ALL LODs (origin defect, not a view defect).

Before spending an in-game cycle on a test depending on the seat, census by classes:

```python
for L in sorted(p3d.lods, key=lambda l: getattr(l, "resolution", 0)):
    if getattr(L, "resolution", 0) not in (1.0, 1100.0, 1200.0):
        continue
    # for each class that the test requires: lights, proxies, gauge textures
    lights = {n: len(s.faces) for n, s in L.selections.items() if n.startswith("light_")}
    prox = [n for n in L.selections if n.lower().startswith("proxy:")]
```

and classify each selection into three buckets: **present seated** (>0 in LOD0 and in 1100),
**the view drops it** (>0 in LOD0, 0 in 1100), and **origin defect** (already 0 in LOD0). The useful
question is not "is the full LOD present" but "what CLASS of thing is missing", because two views of the same tree
can be missing different things.

## Closing first-person gaps: membranes in the ViewPilot only, behind the steering sweep, tested with the steering turned (SP-469, added 2026-10-24, measured in game and offline, DayZDiag 1.30 Exp)

Gaps in a fairing or cockpit through which the seated rider sees the ground can be closed with
single-sided black membranes ("closures") that only the ViewPilot (res 1100) carries. On a model
with a ViewPilot this narrows the seals of SP-166 in the dayz-model-pipeline skill ("Instrument and seal for
see-through triage") and `dayz-p3d-audit` ("Locating seat-visible see-through"): a fix for what
only the seat sees goes in res 1100 alone. Unlike the exterior gap closure of
`visual-gates-and-winding.md` #10 (m), seen from every angle and double-sided in the gap, a 1100
closure is seen only from the seat. It is single-sided on purpose (rule 3 relies on the culled
side, and twins would double its cost in a 1100 with little headroom), and it goes behind the
steering sweep because the bars and fork move through the rider's line of sight.

[EXACT][CLAIM-VEH-MOTO-1PP-VIEWPILOT-130] Measured in game on the H2R import (2026-10), a motorbike
derived from `Motorbike_02_ColorBase` (DayZDiag 1.30.164014 Exp): closures (double-sided at that date)
and 1PP inverted twins in LOD0 showed from outside as black slivers, one closure hiding the compressor intake, and an A/B kit
without both lost the slivers (it removed them together, so it does not say which made them). With
both in res-1100 LODs only, close-up outside shots were clean and, in first person, the closures
covered the large gaps.

The vanilla bikes ship no ViewPilot (parsed from their ODOLs, not checked in game:
`skills/dayz-motorbikes/references/vanilla-p3d-anatomy.md`), so the 1100 is the author's to add. Seat-only
geometry of a proxied part goes in that part's own 1100, since 1PP draws each referenced proxy's
1100, or its finest visual LOD when it has none (SP-249 in `view-pilot-and-first-person.md`); the H2R's engine proxy got
a 1100 for its inverted twins.

The H2R closures were generated offline. From each measured or offset eye and pitch, the project's
rasterizer found the gaps (enclosed, at least 40 px at half resolution, centred in the cockpit, at
least 20 % of the rim on fixed parts), and each such gap got a membrane whose depth is a Laplace
fill from its rim, wound so that the engine draws it toward that eye (calibrate that convention on
a face seen in game: `rip-geometry-and-winding.md` SP-191, `visual-metrics-and-viewer.md` SP-193).
Rules 2-4 come from defects seen in game, rule 1 from offline renders only. The project's offline
pixel counts are at half resolution (1920x1080) unless a line says otherwise; its in-game results
from 2026-10-16 on are on DayZDiag 1.30.164200 Exp.

1. **Test with the steering turned.** Offline, the closures of a kit that showed the steering intact
   in game with the bars straight hid the fork once the bars turned: 247,420 px over 48 views (12
   eyes at pitch -50, bars at ±10° and ±20°), up to ~8,000 px in one view. Every closure check until
   then, offline and in game, had the bars straight; the defect was never observed or checked in
   game.
2. **Put the membrane behind everything the steering sweeps, ray by ray.** In each pixel, keep the
   membrane at least 2 cm deeper than the deepest point of the sweep that projects there (bars, fork
   and front wheel over the full lock, ±20° on the H2R, suspension at rest; that depth map dilated
   4 px), then drop every face with a vertex, an edge midpoint or its centroid within 6 mm of the
   sweep. From the eye that generated it, a gap's ray meets no fixed part, so there the membrane
   hides only the ground; from other eyes it can still cover fixed parts (the final generator run's
   first cleanup pass removed 111 such faces, 18,824 px), which is what rule 3's cleanup is for.
   Both alternatives failed:
   - Trimming the membrane where the sweep passes fails either way. Kept, the thin strips it leaves
     stack up, one per eye and pitch, in the same gap: the H2R's earlier closures, trimmed cell by
     cell, showed it in game as mottling, and the first pixel-trimmed run stacked strips until the
     generator's vertex cap refused 52 patches. Refusing patches that cover under half of their gap
     leaves the gaps the steering crosses open: 108 refused, 55,884 px open over 36 views, against
     4,012 for the closures being replaced. Behind the sweep, the mottled gap read uniform black in
     game, and that 50 % guard never fired: every patch of the final run covered its whole gap.
   - Pushing single vertices back along their rays let triangles cross the steering: in game the top
     clamp, controls and grips vanished behind black fragments, while the offline check, which
     counted only ground seen through gaps, passed. That is the coverage-versus-appearance trap of
     `visual-gates-and-winding.md` #10 (k-CORRECTION) and SP-247 in `rip-panel-open-rim.md`: count closure pixels
     in front of parts next to open pixels.
3. **Tuck the rim under fixed parts by centimetres, behind the deepest fixed point of its grid
   cell.** A rim 6 mm behind each pixel cut panels seen edge-on between grid vertices: in game, an
   irregular black edge and a row of light teeth; offline, 3,097 px (full resolution) of closure in
   front of a fixed part from the eye of that capture. Three changes cleared it: the rim 2 cm behind
   the deepest fixed point of its cell, the depth smoothed only backward (an edge-on wall turns its
   back to the next eye and is not drawn), and a cleanup that removes any closure face more than
   3 mm in front of any fixed part, not only the cockpit's. Offline that left 4 px in front of fixed
   parts over 12 eyes at pitch -50, and in game the edge read clean.
4. **Trace the contour with marching squares on a smoothed mask, crossings interpolated.** Membranes
   assembled from whole grid cells gave the stair-stepped edges the user reported in game. From the
   eye of that capture, exactly horizontal or vertical edge fell from 53 % to 14 % of the contour,
   and turns over 60° from 43 % to 14 %; later kits showed no steps in game (in-game observations
   of rules 2-4 and of the 2026-10-24 runs below, claim: CLAIM-VEH-MOTO-1PP-CLOSURE-INGAME-130).
5. **[DESIGN] Matte black.** The H2R closures use a near-black procedural colour, specular 0 and an
   SMDI with no level or gloss, because membranes behind the sweep have steep faces that a glossy
   rvmat might light into pale bands. Not A/B-tested; in game the matte closures read as uniform
   black.

[DESIGN] The closures are computed against LOD0 and live in the 1100: regenerate them from the final
LOD0 as a step of assembling the 1100, and again after any re-seed, merge or LOD0 edit (the SP-191
lifecycle above). Declare them in any 1100 census or containment gate (the census by classes above,
SP-249 in `view-pilot-and-first-person.md`), where they are a class present in the 1100 and absent from LOD0, and keep
them out of any pass that double-sides the 1100 (`visual-gates-and-winding.md` #10 (g),
`rip-import.md` VISUAL CORRECTNESS #5), which would draw rule 3's edge-on walls. Not measured.

**Generate from every eye the rider can have, then test outside that set.** On the H2R the 1PP eye
changed with the character and between runs of one character, and within one run it moved with the
pitch: on 2026-10-24 one eye went from 7.6 cm off-centre at pitch -50 to 4.7 cm on the other side
at -65. With the head aside at yaw 0 it sat about 9 cm off-centre (8.7 cm at pitch -50, up to
9.4 cm). Log the eye of every run (SP-470 of the dayz-test-ingame skill). The final set had 23 eyes: two eyes
logged in game, each also moved ±3 cm in height and fore-aft; three more, two logged in game and one
recovered by PnP from a user's screenshot (`dayz-p3d-audit`, "Locating seat-visible see-through");
±9 cm lateral copies of the highest and the lowest eye logged in game, and ±4.5 and ±9 cm of a
third; and the off-centre eye with its mirror. No offset combines two axes. Each eye looked at
pitches -35, -50 and -65, yaw 0. Counting only enclosed gaps of at least 40 px centred in the
cockpit with at least 40 % fixed rim, 526 px stayed open over the 69 views (the closures they
replaced: 70,261 by the same count), and no closure stood in front of a fixed part or of a turned
part, both checked at pitch -50 only. In game, at pitch -50 with the bars straight, two characters
were clean over three runs, one with the head 7.6 cm off-centre. An eye set is a sample, not a
bound: a cross-family review moved one measured eye 12 cm sideways, to 10.5 cm off-centre (beyond
the 9.4 cm logged in game), and found offline, at pitch -50, 10 px of closure more than 3 mm in
front of a fixed part (resolution not stated), not shown to be visible in DayZ. (Offline counts of
rules 1-4 and of this eye set, claim: CLAIM-VEH-MOTO-1PP-CLOSURE-OFFLINE-130.)

**What that offline check cannot see.** Its renderer drops every glass face, so "any fixed part"
leaves out the windscreen: whether a closure stands in front of it, or behind it in the rider's
view, was not measured. Geometry close to a pane has read in game as a painted-over window
(`visual-gates-and-winding.md` #10 (k-CORRECTION): a black band 0-1 mm behind the glass) and as an
artifact on the glass (SP-247 in `rip-panel-open-rim.md`: skirts within 5 cm of a pane, the closest 6.1 mm):
check the clearance to transparent glass against the ~8 mm of #10 (m). The renderer samples points
on the faces instead of rasterizing them as the engine does, and its gap detector closes slits up to
about 2 px wide (about 4 px of the capture) and keeps only enclosed gaps, so a 2-3 px line like the
one seen in game on 2026-10-16 is never counted. Fixed and turned parts were checked at pitch -50
and yaw 0 only, and since the in-game eye moves with the pitch, real eye-and-pitch pairs fall
between the sampled ones. No in-game 1PP capture with the bars turned was evaluated on the H2R; the
in-game capture stays the last word.
