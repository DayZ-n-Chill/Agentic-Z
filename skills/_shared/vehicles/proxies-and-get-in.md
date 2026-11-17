# Proxies, get-in and detachable parts: the contract

How proxies are placed on a working car, the four config and model layers a detachable door, hood or trunk needs, what a seated player's action must register, how to hide an attachment proxy from script, and what the first-person View Pilot LOD of a shell and proxy vehicle must carry.

> Status: the measurements below were made on mod vehicles, not on vanilla ones: a working off-road car that ships unbinarized (the control), a helicopter built on `CarScript` with two airframes, two imported cars, three quad bikes, a gun rack mod, a storage mod and a motorbike import derived from `Motorbike_02_ColorBase`. They are third-party mod behaviour, not vanilla. The vanilla script line numbers were opened on the vanilla data on `P:\` (a 1.30 build); a bare `file.c:N` is the vanilla script of that name under `P:\scripts\`, and `entityai.c` means `P:\scripts\3_game\entities\entityai.c`. "Invariant N", "preflight #N" and "#N" all mean the numbered invariants; `skills/dayz-vehicles/SKILL.md` lists which file holds each number. Other skills are named by skill name, each a folder under `skills/` (dayz-model-pipeline, dayz-test-ingame, dayz-mcp-verify).

Related file in this pack: `get-in-actions-and-proxy-pose.md` (the get-in condition chain, action registration and which anchor places the occupant).

## Vanilla anchors checked on `P:\`

- `ProxyVehiclePart` is declared at `P:\DZ\vehicles\wheeled\config.cpp:23901` with `scope=1`, `simulation="ProxyInventory"`, `autocenter=0`, `animated=0`, `shadow=1`, `reversed=0`. The control car quoted below declares its own copy with `scope=2`; every other value is the same.
- `ProxySedanWheel` (`P:\DZ\vehicles\wheeled\config.cpp:23969`) is a vanilla example of layer 2: a proxy class with a `model` and an `inventorySlot[]`.
- The base `OnDebugSpawn` is at `P:\scripts\3_game\entities\entityai.c:3955`, and the sedan's override at `P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c:415`.
- `CanBeUsedInVehicle` returns false in `ActionBase` (`P:\scripts\4_world\classes\useractionscomponent\actionbase.c:361`).
- `ActionOpenCarDoors` and `ActionCloseCarDoors` are added to the player's input action map at `P:\scripts\4_world\entities\manbase\playerbase.c:1714`.
- `CrewCanGetThrough` is at `P:\scripts\3_game\vehicles\transport.c:724` and is consulted at `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:54`.
- `HideSelection` is at `P:\scripts\3_game\entities\entityai.c:3355`.

These are active rules, ordered by topic. The numbered get-in invariants are in `invariants-get-in-and-seats.md`, the vanilla crew and attachment API in `attachments-and-crew.md`, and the curated View Pilot contract in `view-pilot-and-first-person.md`.

---

## Regenerated bodies, the get-in radial and the LOD ladder are in `vehicle-structural-parity.md`

Regenerating a high-poly body from glTF or FBX and splitting it into proxies to stay under the resolved-vertex ceiling (the glTF to DayZ winding check that proves nothing, the identity-frame trap of proxy placement, the model-space convention with no `.p3d` suffix and a measured frame), and the get-in radial and LOD ladder of a proxy-body car (script module binding, the geometric get-in blocker, the inward-wound seat ComponentNN with point flags `0x0000003F`, reversed-wheel `angle1`, the shell and proxy LOD ladder) are structural parity. They are in **`vehicle-structural-parity.md`** (Appendix "REGEN-FROM-glTF + GET-IN RADIAL / LOD ladder"), which is the one place that holds them.

## Proxy placement convention, measured on a working reference car

Two full build and test cycles were spent on a helicopter mod guessing this from the broken model alone.
The answer was one probe away: read a car that works. The control is a working off-road car mod that ships
unbinarized (MLOD v257, which py3d reads directly, with no debinarize).

Measured on the control's LOD0 (18 proxies):
- **Not one has its anchor at the origin.** Every anchor sits at the real target position:
  a wheel at `[0.8746, 0.4513, -1.5638]`, the driver door at `[0.888, 0.6492, -0.8629]`,
  the trunk at `[0.0021, 1.1487, 2.5139]`.
- **Not one has an identity frame (0 of 18).** The standard frame is `[[-1,0,0],[0,0,1],[0,1,0]]`;
  the opposite side mirrors it as `[[1,0,0],[0,0,-1],[0,1,0]]`; the spare wheel uses its own rotation.
- Sub-models are authored in **proxy-local space**, origin at the attachment point:
  the distance from origin to bounding box centre is 0.000 m for the wheel and the trunk,
  0.726 m for the hood and 0.821 m for the driver door (they pivot on their hinge).

Rules:
1. Proxy anchor = target position in host coordinates. An anchor at the origin is a defect.
2. Sub-model geometry is authored near its own origin (under about 1 m). A sub-model whose bounding box centre sits
   2 to 7 m away is authored in host coordinates: that is the defect, and it is the one worth gating.
3. The frame `[[-1,0,0],[0,0,1],[0,1,0]]` is the normal neutral, not a smell: the crew proxies that
   work carry it too. Numerical identity never appears in a working model, and forcing it makes
   placement worse (verified in game on the helicopter).
4. A zero-size crew marker proxy (about 463 bytes) is immune to any frame rotation because its geometry
   sits at the origin. Do not infer the convention from those; use a proxy that carries geometry.
5. Doors on a working vehicle are proxies with their own `.p3d` anchored at the hinge, not baked
   geometry driven by a bone. Consider that before designing bone-driven doors.

Method rule: calibrate every gate rule against a model that works before
trusting it. Three rules were written from the broken model; two were false positives that would
have flagged every correct model. The reference car removed both in one probe.

A gate that implements this checks three things on each proxy (anchor at the origin, sub-model authored
in host space, coherence of normal and winding), and a texture binding gate checks that one `.rvmat`
does not carry two base textures.

## Detachable parts (doors, hood, trunk): the four-layer contract

Measured on the same working control. The helicopter mod spent weeks on "the door does not animate" with the full script and model contract
verified, because it only knew layer 3 below.

### The contract is four layers, not one

1. **`CfgSlots`**
   ```cpp
   class Slot_MyCar_Driver_Door {
       name = "MyCar_Driver_Door";
       displayName = "...";
       selection = "doors_driver";        // <-- the ANIMATION BONE selection
       ghostIcon = "set:dayz_inventory image:doorfront";
   };
   ```
   `selection` is the binding between "the attachment is mounted" and "the proxy is drawn".

2. **`CfgNonAIVehicles` / `ProxyVehiclePart`**, the layer that gets missed.
   ```cpp
   class ProxyAttachment;
   class ProxyVehiclePart : ProxyAttachment {
       scope=2; simulation="ProxyInventory"; autocenter=0; animated=0; shadow=1; reversed=0;
   };
   class ProxyMyCar_Driver_Door : ProxyVehiclePart {
       Model = "\MyCar\proxy\MyCar_Driver_Door.p3d";
       inventorySlot = "MyCar_Driver_Door";
   };
   ```
   Without it the engine does not resolve the host's `proxy:\...` as an attachment proxy. Note that
   `autocenter=0` appears here too: the control declares it in three places, the sub-model's visual
   LOD, the sub-model's Geometry LOD, and this config class.

3. **Item class** `MyCar_Driver_Door : CarDoor` with `Model`, `inventorySlot`, `hiddenSelections`,
   `weight`, `itemSize[]`, `physLayer`, `DamageSystem`.

4. **Vehicle**: the slot name inside `attachments[]`, plus `class Doors` in the vehicle DamageSystem.

**Host proxy triangle: double membership.** Measured on the control's LOD0, the 3 points of
the driver door proxy belong 3/3 to `doors_driver` (the bone) and 3/3
to the selection named after the slot. A proxy wired only to the bone animates but does not
follow the attachment.

**A detachable part is a physical item.** It can be dropped on the ground, so its `.p3d` needs real
special LODs, not an empty Geometry. Measured on the control's driver door (points/faces): visual `463/754`,
Geometry `32/24`, Memory `7/0`, ViewGeo `32/24`, FireGeo `72/56`, with `autocenter=0` on the visual
LOD and on Geometry. Budget the item LODs before promising the feature.

Custom inventory slots fall under Bohemia ticket T148506 (`skills/_shared/conventions/config.md`): if the slot name and the
`inventorySlot` string diverge, the item never attaches and the proxy never draws.

> The rule for rewriting a proxy triangle is in `rip-geometry-and-winding.md`, "Rewriting a proxy triangle".

> The scope of `autocenter=0` is in `rip-geometry-and-winding.md`, "`autocenter=0`: corrected scope by LOD, host, and submodel".

### `binarize` is not deterministic: never gate on ODOL byte identity

Two runs of `binarize.exe -always` over the same source, same flags: the shell came out
`2,886,719 b` / `8C290530214C...` and `2,763,097 b` / `0705207DB7F0...`; the interior `1,062,412 b`
against `1,062,417 b`. The two small rotor models were byte-identical, so the effect scales with model
size. Semantically the two shells match (66/66 `model_info` fields, same faces, selections and properties
per LOD); the divergence is encoding and compression order, and between builds the order of faces and
sections changes too (`skills/dayz-build-pbo/references/post-build-gates.md`, measured with AddonBuilder; section order was not compared
on the helicopter). The motorbike import saw it with `binarize.exe` called directly: a rebuild from
byte-identical MLODs kept every per-LOD count while its face arrays differed in every resolution LOD and
the ViewPilot, and between two of its builds the LOD 0 section of `dashboard` went from index 175 to 204
with the same faces, section count and material set.

Rule: gates over ODOL compare semantics (per-LOD counts, selections, properties, proxies, centres),
never bytes or section indices (between builds, key on the unordered multiset of that file). Hash identity is
still valid for MLOD, which the pipeline writes itself. Re-read any earlier "the ODOL came out
byte-identical" result with this in mind.

A vanilla car only draws a door proxy when the door is attached; that is the behaviour a baked door has to be converted to.

### Two traps that follow from converting a baked part into an attachment

Both bite the moment the part becomes an attachment, and both look like "my model change
broke the vehicle".

**1. A detachable part is invisible on every debug or admin spawn until something attaches it.**
`CreateObject`, admin-tool spawns and spawns through a test bridge do not populate attachment
slots, which is why a vanilla car spawned that way has no wheels. The moment a door moves from
baked hull geometry to an attachment, a spawned vehicle shows an empty doorway, and it reads as
a regression when it is the contract working.

The hook is `OnDebugSpawn()` (`P:\scripts\3_game\entities\entityai.c:3955`, with
`OnDebugSpawnEx(DebugSpawnParams)` delegating to it at `entityai.c:3937-3939`). Two patterns:

- explicit `CreateAttachment` per part, as a quad bike mod does:
  ```c
  override void OnDebugSpawn()
  {
      EntityAI entity;
      if (Class.CastTo(entity, this))
      {
          entity.GetInventory().CreateAttachment("CarBattery");
          entity.GetInventory().CreateAttachment("SparkPlug");
          entity.GetInventory().CreateAttachment("MyQuad_Wheel_Front");
          // ...
      }
  }
  ```
- vanilla car, `CreateInInventory` per part: `P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c:415-436`
  (`SpawnUniversalParts(); SpawnAdditionalItems(); FillUpCarFluids();` then one call per door and wheel).

The `EntityAI` base implementation is config-driven instead: it reads the type's `attachments[]`
and scans `CfgVehicles`, `CfgMagazines` and `CfgWeapons` for any class whose `inventorySlot` matches,
then calls `CreateInInventory` for it (`entityai.c:3955-4009`). Calling `super.OnDebugSpawn()` therefore
attaches per type from config with no per-vehicle code, which is useful when one script base serves
several models. The vanilla cars do not call super; they list their parts explicitly.

**2. `attachments[]` depends on the PBO boundary; `+=` is not an unconditional rule.**
Within the same source config tree, `+=` can retain the parent's slots. When the parent class comes from another PBO that is already compiled, that list is not a safe basis: write the complete list of vital and own slots in the child class. The earlier form of this rule is in `history/superseded-family-b-rules.md`.

The gate does not look for a `+=` token: it inspects the effective list after a compile or config dump and verifies battery, ignition, radiator, wheels, and each declared door or part. A door change cannot silently remove a vital slot. Also keep the independent check that each declared part appears in the `OnDebugSpawn` path; they are separate contracts.

## In-vehicle actions need two registrations, and a proxied part is a placement oracle

### An action offered to a seated occupant must be registered in two places

Measured on the helicopter mod, which spent a build cycle on "the close-door action does not appear
when seated" with the action class already correct.

1. The action must opt in: `ActionBase.InitConditionMask` only sets `ACM_IN_VEHICLE` when
   `CanBeUsedInVehicle()` returns true (`actionbase.c:110`), and the base returns false
   (`actionbase.c:361`). Any world action inherited from `ActionInteractBase` is therefore
   masked out the moment the player boards.
2. A seated player has no cursor target on the vehicle carrying them, so the target contract
   is `CCTNone` plus `HasTarget()` false, the shape vanilla uses in `actioncardoors.c:20` (`CCTNone`)
   and `actioncardoors.c:120` (`HasTarget()` returns false).
3. **Both registrations are required, and the second one is the one that gets missed:**
   - `ActionConstructor.RegisterActions` builds the instance into the global pool.
   - `PlayerBase.SetActions(out TInputActionMap)` calls `AddAction(MyAction, InputActionMap)`.
     Vanilla puts `ActionOpenCarDoors` and `ActionCloseCarDoors` right there
     (`playerbase.c:1714-1715`).
   Registering only in the constructor builds an action the manager never offers, because
   `FindContextualUserActions` walks the player's `InputActionMap` per input, not the pool.

Vanilla splits inside and outside into separate classes (`ActionCloseCarDoors` and
`ActionCloseCarDoorsOutside`); copy that split instead of making one class serve both.

**Ship the opening half too.** If entry and exit are gated on the door being open, an inside-only
close action traps the occupant. Pair it with an inside open action, and keep one exemption in
the gate: a door that is not mounted must leave the seat escapable, because no action can open
what is not there.

### A proxied part is the first correctly placed reference on the host: use it as an oracle

When a host renders wrong, there is usually nothing trustworthy to measure it against. Parts
drawn through attachment proxies are placed by the engine from the entity transform, so they
are trustworthy, and the disagreement localises the fault:

- proxies agree with each other and disagree with the host: **the host is the broken one**.
  Do not "correct" the proxy anchors to match: that deforms the correct piece, and the
  error changes with the host's state.
- On the helicopter mod the doors, both rotors and the interior all followed the aircraft into the
  air while the fuselage stayed at ground level. The doors had just been migrated to proxies,
  and became the reference that localised a render bug that had been open for a week.

Corollary: the `scene_raycast` tool of dayz-mcp in `rvproxy` mode returns the Geometry LOD, not the visual mesh, so
it cannot settle a visual misalignment. On a coarse collision hull it reports a surface
tens of centimetres inside the visible skin. Use it for collision questions only.

## A vehicle core shared by several models makes "deploy ordering" gates unenforceable

When one Enforce Script core file serves several vehicle lines (one base script serving two
helicopter airframes), any patch in it, even one gated by `ConfigIsExisting("vehicleProp")` so only one
line executes it, deploys whenever any line rebuilds the core PBO. A sequencing rule like "do
not deploy the core patch until the model ships its matching memory points" does not survive
the sibling line's next rebuild. Measured case: one airframe's line rebuilt and deployed
the shared core for its own fixes, and the other airframe's get-in patch went live with it, pointing at
ten memory points the deployed model does not have (verified by scanning the
deployed PBO bytes for the patch symbols, not by file time).

1. A core-side patch that requires a model-side contract (memory points, selections, bones)
   must tolerate its absence at runtime: fall back with `MemoryPointExists` to the previous mapping, so the
   patch stays inert until the model ships the contract. Deploy-order gates across a
   shared source cannot be enforced by anyone.
2. Alternatively, land model and core in the same build; never leave a
   contract-dependent patch sitting in shared source waiting for its model.
3. When auditing what is live, verify the deployed PBO content (a byte scan for the patch's
   symbols). A note that the core changed says nothing about what else went out with it; only the bytes do.

## A phantom vehicle command blocks all vanilla get-in after a client crash while seated

Symptom: the get-in prompt shows but accepting does nothing, on both seats, with no trace in the RPT or script log,
and it survives rebuilds because nothing in the mod is broken. Mechanism:
`ActionGetInTransport.ActionCondition` runs on both sides; the client player (clean) shows the
prompt, but the server-side player still carries a non-null `GetCommand_Vehicle()` restored
from player storage after a client crash while seated. The first server gate
(`actiongetintransport.c:42-43`) rejects silently, and a null `StartCommand_Vehicle` in `Start()`
(`actiongetintransport.c:104-105`) produces no log either.

Checklist before suspecting model, proxies or config for a get-in regression:
1. Check the previous run's client profiles for a `crash_*.log`: a crash while seated is where
   the phantom starts.
2. With dayz-mcp available: `query_get_in_condition` returning `first_block=already_in_vehicle`
   with the player standing in the open confirms the phantom; `vehicle_get_in_client` (direct on the owner side,
   skipping the action gates) seating fine shows the seat contract and model are healthy.
3. The phantom clears on a clean logout cycle. "It fixed itself next session" is the signature
   of this bug, not of a flaky model.

Measured case: a full get-in regression was blamed on a model edit whose Geometry, ViewGeo, FireGeo and Memory LODs
were byte-identical before and after.

## The ViewPilot (1100) of a shell and proxy car must carry the body geometry, not only proxy triangles

Symptom: on entering the vehicle in first person the body goes invisible for
seconds (vanilla never does). Measured root cause on an imported sports car: the shell's 1100 LOD held 7
faces, only the proxy triangles (interior, doors, wheels), and no geometry of its own,
while the vanilla control (the unbinarized civiliansedan) carries 11,977 real faces there
(interior, body and glass) plus its 13 proxies. The engine switches the shell to
the 1100 on mount; with nothing but proxy anchors in it, the body vanishes
until the proxies resolve. The design in which the interior file held a subset
never produced a subset (the interior file's 1100 was its full visual LOD).

Fix pattern: merge the shell LOD0 into the 1100. Copy the shell's own geometry
with remapped point and normal indices, get or create the named selections
(so `camo` and `light_*` keep working in first person), and copy the proxies that
only LOD0 has verbatim (points, face and selection; `add_proxy` would lose the
frame). Exclude the faces and anchor points of proxies the 1100 already has.
Gates that must pass: the original proxy selections intact (1 face and 3 points each), the proxy set equal to
the originals plus the copied ones, the count of bone companion selections unchanged, and the resolved
vertices printed against the design budget (about 16k on that car). Binarize preserved
the merge exactly (22,849 faces and 11 proxies in the ODOL).

> **Capacity.** A check of `facenormals <= 32768` is not a universal engine or load gate. Keep that number only
> when it is declared as a local design budget. For a load verdict, first
> count the known-good blob extracted from the deployed PBO on the same `MLOD`/`ODOL`
> route, then use the candidate's three-state `binarize` verdict (`binarize-vertex-budget.md`). A warning threshold
> alone never authorizes geometry reduction, and the absent-1100 path below must not
> choose its seed from this number.

This applies to every shell and proxy car, but **the defect has two shapes and
they need different fixes**, so census before assuming which one is present. A second imported
car, opened with py3d 1.4.0, carried 10 LODs and none of them was 1100:
resolutions 0, 1, 2, 3, 4, 10000, then the canonical 1e13 Geometry, 1e15 Memory,
6e15 ViewGeometry and 7e15 FireGeometry. It had no ViewPilot LOD to be
proxy-only, and the merge fix would have merged into a LOD that does not exist.

Day-1 check for the next car: census the shell 1100 against civiliansedan before the first in-game
cycle, and give the census **three** outcomes, not two:

| census | what it is | fix |
|---|---|---|
| populated | 1100 with its own geometry | none |
| **proxy-only** | 1100 exists but only carries proxies | merge above |
| **absent** | no 1100 (measured on the second car) | **create** the 1100; the merge does not apply |

The creation procedure is in the next section. It is verified offline only: measure it in game before trusting it.

## Creating an absent ViewPilot is a lifecycle, not a blind LOD copy

**[OFFLINE VERIFIED; IN-GAME VALIDATION STILL REQUIRED]** Keep the three-way census
above. For the absent case, create resolution 1100 only through the assembler that builds the model,
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

## Detachable extraction is proved by material and space, not selection count

**[OFFLINE VERIFIED]** A shell can report only the proxy triangle under `door_1`
and still retain the whole window because the window belongs to a global `glass`
selection. For every visual LOD, count shell faces inside the detached part's
footprint by material, place the submodel at its proxy anchor, and match candidate
face twins in world/model space. A matched shell face is a duplicate; an unmatched
face is legitimate shell. Derive the distance tolerance from the valley in the
measured bimodal distance histogram, not from a round literal.

Removing the duplicate can expose a pre-existing submodel placement error, so a
more visible hole after cleanup is not proof of regression. A zero residual
between the submodel and the volume used by its own authoring transform proves
lineage only; it shares the producer's frame and does not settle the engine render.
The final placement verdict remains in-game.

## Continuous actions and input exclusion while seated

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


## Hiding an attachment proxy from script: the two config halves

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
vanilla comment says so at `entityai.c:1430`: *"making them INVISIBLE if they are
configured in models.cfg in such way. These selections must also be defined in
the entity's config class in 'AnimationSources'"*. Without both halves every
call is a no-op, and a no-op that looks like a timing race, which is how a whole
debugging round can be spent on `CallLater` retries that could never have helped.

**Name contract, read in two mods that work in game:** the
string passed to `SetAnimationPhase` / `HideSelection` is the **class name in
`AnimationSources`**, which is also the animation's **`source`** in model.cfg. It
is not the animation's class name and not necessarily the selection name.

| piece | file | example |
|---|---|---|
| source | config.cpp `AnimationSources` | `class rotor_static_hide { source="user"; animPeriod=0.001; initPhase=0; };` |
| animation | model.cfg `Animations` | `class main_rotor_static_hide { type="hide"; source="rotor_static_hide"; selection="main_rotor"; minValue=0; maxValue=1; hideValue=0.5; }` |
| call | script | `SetAnimationPhase("rotor_static_hide", staticHide)` |

Naming the three the same also works (a storage mod and a gun rack mod use `hideproxy`
for all three), which is why the contract is easy to get wrong by accident: a
mod that happens to use one name everywhere gives no evidence about which name
the engine reads.

- `initPhase = 1` hides at spawn; `initPhase = 0` shows. The direction was
  verified in game in the gun rack mod
  and matches the vanilla comment above. For a cargo slot that starts empty,
  `initPhase = 1` is the state to use.
- `hideValue = 0.01` with `animPeriod = 0.01` is the near-instant swap the
  storage mod's unbinarized gun rack model uses.
- Both precedents also declare the hidden selection as a **skeleton bone**. Not
  proven necessary here, but a hide animation that the engine ignores is
  indistinguishable from the unfixed symptom, and each in-game cycle costs
  minutes, so match the precedent unless there is a reason not to.
- Refresh the phase in `DeferredInit` **and** `AfterStoreLoad`
  (`entityai.c:1418`, "called when entity is being loaded from DB or Storage
  (after all children loaded)"), plus `EEItemAttached`/`EEItemDetached`.

## Gating a crew position on an attachment

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


## The pilot LOD is assembled by hand: census it by classes and against LOD0

A ViewPilot (res 1100/1200) is not a decimation of LOD0: it is a **curated** view, and whatever
its assembler left out does not appear anywhere. Measured on two sibling
quad bike mods from the same source tree, with **opposite** results:

| | Quad A | Quad B |
|---|---|---|
| body | 25,234 faces (LOD0: 76,044) | 2,294 faces (LOD0: 9,011) |
| dashboard | **complete**: `light_dashboard` 744 faces, same as LOD0 | `light_dashboard` **0** faces (LOD0: 12) |
| attachment proxies | **0 of 7** (only the interior and the two crew ones) | 3 of 17 |

The two consequences are gates that lie, and they lie in opposite directions:

- **False green**: "verify that with empty slots no proxy is seen" comes out green from the
  seat whether fixed or not, because the attachment proxies are not there. That check must be done **from
  outside, in third person**.
- **False red**: "sit down and check if the dashboard lights up" always comes out red on a model
  whose `light_dashboard` never reached the view, even if material and script are perfect.

**The census is made against LOD0, not in absolute terms.** "0 faces in 1100" does not distinguish *the view
dropped it* from *it never existed*; only the LOD0 and 1100 pair separates the two classes. In the measured case,
four out of nine light selections would have been misread by looking only at 1100: they were at 0 across
all LODs (a defect of the source model, not of the view).

Before spending an in-game cycle on a test that depends on the seat, census by classes:

```python
for L in sorted(p3d.lods, key=lambda l: getattr(l, "resolution", 0)):
    if getattr(L, "resolution", 0) not in (1.0, 1100.0, 1200.0):
        continue
    # for each class that the test requires: lights, proxies, gauge textures
    lights = {n: len(s.faces) for n, s in L.selections.items() if n.startswith("light_")}
    prox = [n for n in L.selections if n.lower().startswith("proxy:")]
```

and classify each selection into three buckets: **present seated** (over 0 in LOD0 and in 1100),
**the view drops it** (over 0 in LOD0, 0 in 1100), and **source defect** (already 0 in LOD0). The useful
question is not "is the full LOD present" but "what class of thing is missing", because two views of the same tree
can be missing different things.

## Closing first-person gaps: membranes in the ViewPilot only, behind the steering sweep, tested with the steering turned

Measured in game and offline on a motorbike import derived from `Motorbike_02_ColorBase` (DayZDiag 1.30 Exp).

Gaps in a fairing or cockpit through which the seated rider sees the ground can be closed with
single-sided black membranes ("closures") that only the ViewPilot (res 1100) carries. On a model
with a ViewPilot this narrows the seals of the dayz-model-pipeline skill ("Instrument and seal for
see-through triage") and of `skills/dayz-p3d-audit/references/winding-absolute-check.md` (a defect seen from the seat): a fix for what
only the seat sees goes in res 1100 alone. Unlike the exterior gap closure of
`visual-gates-and-winding.md` #10 (m), seen from every angle and double-sided in the gap, a 1100
closure is seen only from the seat. It is single-sided on purpose (rule 3 relies on the culled
side, and twins would double its cost in a 1100 with little headroom), and it goes behind the
steering sweep because the bars and fork move through the rider's line of sight.

[EXACT] Measured in game on the motorbike import (DayZDiag 1.30.164014 Exp): closures (double-sided at that point)
and first-person inverted twins in LOD0 showed from outside as black slivers, one closure hiding the compressor intake, and an A/B kit
without both lost the slivers (it removed them together, so it does not say which made them). With
both in res-1100 LODs only, close-up outside shots were clean and, in first person, the closures
covered the large gaps.

The vanilla bikes ship no ViewPilot (parsed from their ODOLs, not checked in game:
`skills/dayz-motorbikes/references/vanilla-p3d-anatomy.md`), so the 1100 has to be added. Seat-only
geometry of a proxied part goes in that part's own 1100, since first person draws each referenced proxy's
1100, or its finest visual LOD when it has none (the curated-view section of `view-pilot-and-first-person.md`); the import's engine proxy got
a 1100 for its inverted twins.

The closures were generated offline. From each measured or offset eye and pitch, a
rasterizer found the gaps (enclosed, at least 40 px at half resolution, centred in the cockpit, at
least 20 % of the rim on fixed parts), and each such gap got a membrane whose depth is a Laplace
fill from its rim, wound so that the engine draws it toward that eye (calibrate that convention on
a face seen in game: `rip-geometry-and-winding.md` and the self-check in `visual-metrics-and-viewer.md`).
Rules 2-4 come from defects seen in game, rule 1 from offline renders only. The offline
pixel counts are at half resolution (1920x1080) unless a line says otherwise; the later in-game results
are on DayZDiag 1.30.164200 Exp.

1. **Test with the steering turned.** Offline, the closures of a kit that showed the steering intact
   in game with the bars straight hid the fork once the bars turned: 247,420 px over 48 views (12
   eyes at pitch -50, bars at ±10° and ±20°), up to ~8,000 px in one view. Every closure check until
   then, offline and in game, had the bars straight; the defect was never observed or checked in
   game.
2. **Put the membrane behind everything the steering sweeps, ray by ray.** In each pixel, keep the
   membrane at least 2 cm deeper than the deepest point of the sweep that projects there (bars, fork
   and front wheel over the full lock, ±20° on that bike, suspension at rest; that depth map dilated
   4 px), then drop every face with a vertex, an edge midpoint or its centroid within 6 mm of the
   sweep. From the eye that generated it, a gap's ray meets no fixed part, so there the membrane
   hides only the ground; from other eyes it can still cover fixed parts (the final generator run's
   first cleanup pass removed 111 such faces, 18,824 px), which is what rule 3's cleanup is for.
   Both alternatives failed:
   - Trimming the membrane where the sweep passes fails either way. Kept, the thin strips it leaves
     stack up, one per eye and pitch, in the same gap: the earlier closures, trimmed cell by
     cell, showed it in game as mottling, and the first pixel-trimmed run stacked strips until the
     generator's vertex cap refused 52 patches. Refusing patches that cover under half of their gap
     leaves the gaps the steering crosses open: 108 refused, 55,884 px open over 36 views, against
     4,012 for the closures being replaced. Behind the sweep, the mottled gap read uniform black in
     game, and that 50 % guard never fired: every patch of the final run covered its whole gap.
   - Pushing single vertices back along their rays let triangles cross the steering: in game the top
     clamp, controls and grips vanished behind black fragments, while the offline check, which
     counted only ground seen through gaps, passed. That is the coverage-versus-appearance trap of
     `visual-gates-and-winding.md` #10 (k-CORRECTION) and of `rip-panel-open-rim.md`: count closure pixels
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
   assembled from whole grid cells gave stair-stepped edges in game. From the
   eye of that capture, exactly horizontal or vertical edge fell from 53 % to 14 % of the contour,
   and turns over 60° from 43 % to 14 %; later kits showed no steps in game.
5. **[DESIGN] Matte black.** The closures use a near-black procedural colour, specular 0 and an
   SMDI with no level or gloss, because membranes behind the sweep have steep faces that a glossy
   rvmat might light into pale bands. Not A/B-tested; in game the matte closures read as uniform
   black.

[DESIGN] The closures are computed against LOD0 and live in the 1100: regenerate them from the final
LOD0 as a step of assembling the 1100, and again after any re-seed, merge or LOD0 edit (the
lifecycle section above). Declare them in any 1100 census or containment gate (the census by classes above,
and the curated-view section of `view-pilot-and-first-person.md`), where they are a class present in the 1100 and absent from LOD0, and keep
them out of any pass that double-sides the 1100 (`visual-gates-and-winding.md` #10 (g),
`rip-import.md` VISUAL CORRECTNESS #5), which would draw rule 3's edge-on walls. Not measured.

**Generate from every eye the rider can have, then test outside that set.** On that bike the first-person eye
changed with the character and between runs of one character, and within one run it moved with the
pitch: in one run an eye went from 7.6 cm off-centre at pitch -50 to 4.7 cm on the other side
at -65. With the head aside at yaw 0 it sat about 9 cm off-centre (8.7 cm at pitch -50, up to
9.4 cm). Log the eye of every run (`skills/dayz-test-ingame/references/session-findings.md`). The final set had 23 eyes: two eyes
logged in game, each also moved ±3 cm in height and fore-aft; three more, two logged in game and one
recovered by PnP from a screenshot (`skills/dayz-p3d-audit/references/winding-absolute-check.md`);
±9 cm lateral copies of the highest and the lowest eye logged in game, and ±4.5 and ±9 cm of a
third; and the off-centre eye with its mirror. No offset combines two axes. Each eye looked at
pitches -35, -50 and -65, yaw 0. Counting only enclosed gaps of at least 40 px centred in the
cockpit with at least 40 % fixed rim, 526 px stayed open over the 69 views (the closures they
replaced: 70,261 by the same count), and no closure stood in front of a fixed part or of a turned
part, both checked at pitch -50 only. In game, at pitch -50 with the bars straight, two characters
were clean over three runs, one with the head 7.6 cm off-centre. An eye set is a sample, not a
bound: a later review moved one measured eye 12 cm sideways, to 10.5 cm off-centre (beyond
the 9.4 cm logged in game), and found offline, at pitch -50, 10 px of closure more than 3 mm in
front of a fixed part (resolution not stated), not shown to be visible in DayZ.

**What that offline check cannot see.** Its renderer drops every glass face, so "any fixed part"
leaves out the windscreen: whether a closure stands in front of it, or behind it in the rider's
view, was not measured. Geometry close to a pane has read in game as a painted-over window
(`visual-gates-and-winding.md` #10 (k-CORRECTION): a black band 0-1 mm behind the glass) and as an
artifact on the glass (`rip-panel-open-rim.md`: skirts within 5 cm of a pane, the closest 6.1 mm):
check the clearance to transparent glass against the ~8 mm of #10 (m). The renderer samples points
on the faces instead of rasterizing them as the engine does, and its gap detector closes slits up to
about 2 px wide (about 4 px of the capture) and keeps only enclosed gaps, so a 2-3 px line like the
one seen in game is never counted. Fixed and turned parts were checked at pitch -50
and yaw 0 only, and since the in-game eye moves with the pitch, real eye-and-pitch pairs fall
between the sampled ones. No in-game first-person capture with the bars turned was evaluated; the
in-game capture stays the last word.
