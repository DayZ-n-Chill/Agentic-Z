# Vehicle lights

Why a car's lights do not switch: material paths, hidden selection ownership and order, bulbs, driver exit, and how to test the setter against a vanilla car.

> Status: the measurements below were taken in game or offline on mod vehicles, named in each entry; they describe those mods, not vanilla, unless a vanilla citation backs them. Every citation of a vanilla file was opened on `P:\` (a 1.30 build), whether it is written with its full `P:\` path or with the file name alone. A citation marked `1.29` gives the line in a 1.29 build, which is not on `P:\` and is not checked. "Invariant N", "preflight #N" and "#N" all mean the numbered invariants; `skills/dayz-vehicles/SKILL.md` lists which file holds each number.

Related file in this pack: `emissive-leds-and-dynamic-lights.md` (an LED or indicator built from a hidden selection, one `.rvmat` per state and an optional scripted point light).

## Vanilla anchors checked on `P:\`

- The light selection indices are fixed: `SELECTION_ID_FRONT_LIGHT_L` 0 to `SELECTION_ID_DASHBOARD_LIGHT` 8 (`P:\scripts\4_world\entities\vehicles\carscript.c:174` to `:182`). The dashboard pair is registered with `dashboardMatOn` and `dashboardMatOff` (`P:\scripts\4_world\entities\vehicles\carscript.c:230`).
- With `CarHeadlightBulbsState.BOTH`, one aggregated front light is attached at the midpoint of the two headlight memory points (`P:\scripts\4_world\entities\vehicles\carscript.c:1891-1896`). The rear light is attached at `m_ReverseLightPoint` (`P:\scripts\4_world\entities\vehicles\carscript.c:1934`) and only when `m_HeadlightsState` is not `NONE` (`P:\scripts\4_world\entities\vehicles\carscript.c:1929`).
- `m_HeadlightsState` comes from the bulbs in the reflector slots (`P:\scripts\4_world\entities\vehicles\carscript.c:529`).
- `CarScript.OnDriverExit` calls `EngineStop` when the gear is not neutral (`P:\scripts\4_world\entities\vehicles\carscript.c:940-947`); `Transport` leaves `OnDriverExit` empty (`P:\scripts\3_game\vehicles\transport.c:224`). `GetNeutralGear` and `ShiftTo` are native on `Car` (`P:\scripts\3_game\vehicles\car.c:251`, `P:\scripts\3_game\vehicles\car.c:260`).
- `UpdateLights` runs `UpdateLightsClient` inside `#ifndef SERVER` and `UpdateLightsServer` on both sides (`P:\scripts\4_world\entities\vehicles\carscript.c:1853-1858`).
- `VehicleLightsComponent` applies the material with `SetObjectMaterial` (`P:\scripts\4_world\entities\vehicles\components\vehiclelightscomponent.c:79`); `SetObjectMaterial` and `GetObjectMaterial` are native (`P:\scripts\3_game\entities\entityai.c:2884-2885`) and `GetHiddenSelectionIndex` resolves a selection by name (`P:\scripts\3_game\entities\entityai.c:2778`).
- `ForceUpdateLightsStart` and `ForceUpdateLightsEnd` are empty `[Obsolete]` declarations (`P:\scripts\4_world\entities\vehicles\carscript.c:2805-2809`), and `P:\scripts\4_world\entities\vehicles\carscript.c` holds no `ToggleHeadlights` at all.
- `SpawnUniversalParts` adds the four `HeadlightH7` bulbs with `CreateInInventory` (`P:\scripts\4_world\entities\vehicles\carscript.c:2500-2506`).
- Vanilla material paths have no leading backslash: the `hiddenSelectionsMaterials[]` of `CivilianSedan` start at `dz\` (`P:\DZ\vehicles\wheeled\config.cpp:5180`).
- The vehicle light key is `UAToggleVehicleLights` (`P:\scripts\4_world\classes\useractionscomponent\actioninput.c:855`); `UAToggleHeadlight` is the head torch (`P:\scripts\4_world\classes\useractionscomponent\actioninput.c:782`).

## Five failures that look like a broken material and are not (added 2026-08-17; all measured in game on SUB_BRZ)

- **Light-selection preflight.** Before reassigning a rear lamp, print every light hidden selection's face count and bbox. A lateral selection whose bbox crosses `x=0` owns centre geometry (e.g. `x=-0.12` to `0.65` = the tailgate bar); dozens of faces compressed into ~1 cm (here 44 faces in 0.01 m) are degenerate and draw nothing. Brake and tail must own disjoint faces; if they overlap the later `SetObjectMaterial` wins and the result is indeterminate.

- **The `CarScript` light-selection ABI is positional (added 2026-08-31).**
  `carscript.c:174-182` fixes indices 0/1 front, 2/3 brake, 4/5 reverse, 6/7 rear
  position and 8 dashboard. Names are free; list order is not. Indices `>=9` have
  no native `CarScript` light meaning and require the mod's own driver. Indices 2/3
  and 6/7 must resolve to disjoint face sets, or the later `SetObjectMaterial` wins.
- **With both headlight bulbs active, `*_dir` does not steer the beam.**
  `CarHeadlightBulbsState.BOTH` attaches one aggregated light at the midpoint of
  `light_left` and `light_right` (`carscript.c:1892-1896`). Measure that midpoint
  against the centre-line body surface; a point inside the shell traps the beam.
  Apply the same check to `light_reverse` (`carscript.c:1934`).

A car whose lights "do not work" almost never has a broken `.rvmat`. Five distinct causes were
separated in one session by measurement; each has a cheap discriminator. Run them in this order,
because the first one invalidates every test downstream.

### 1. A leading backslash in a material path is rejected in SILENCE

`SetObjectMaterial` accepts `MOD\data\x.rvmat` and **rejects** `\MOD\data\x.rvmat`. No error, no
log line: the readback simply still shows the old material. Proven with an A/B that held the car,
the selection, the index and the target file fixed and changed only the leading character:

```
asked \SUB_BRZ\data\brz_light_brake_on.rvmat  ->  got \sub_brz\data\brz_light_brake_off.rvmat   REJECTED
asked  SUB_BRZ\data\brz_light_brake_on.rvmat  ->  got  SUB_BRZ\data\brz_light_brake_on.rvmat    APPLIED
```

Vanilla never writes the leading backslash on a material path — `CivilianSedan` has 25 of them,
all starting at `dz\` (`P:\DZ\vehicles\wheeled\config.cpp:5180`). Neither does a working modded
glowing item. **But `model=` paths keep their leading backslash and resolve fine**, which is why
the inconsistency survives review: half the file uses one form, half the other, and only the
material half breaks.

Applies to `hiddenSelectionsMaterials[]` and to every `*MatOn` / `*MatOff` key.
Grep before blaming anything else: `"\\MOD[^"]*\.rvmat"`.

### 2. A lamp whose faces are in NO hiddenSelection can never light

Rip-imported cars arrive with the lamp split in two: a large piece (`tail`, `light_left_static`,
`light_right_static`, `light_dashboard_static`) that is absent from `hiddenSelections[]`, plus a
small switchable insert that is in it. On SUB_BRZ that was **19.310 faces that nothing can ever
switch** against inserts of 42 and 318 faces.

The symptoms read as material bugs and are not:
- "the red piece is always faintly lit and has no glass" -> the big piece wears a crude constant
  emissive that no setter reaches.
- "only one bulb of the two lights up" -> only the insert is in the selection.
- "the position lamps do not light" -> they do; 42 lit faces against 1.555 unlit around them.

Discriminator, before touching any material: count faces per selection and cross them with
membership. A bounding box is NOT enough — `tail` spanned 3.788 mm of a 4.086 mm car and still was
only the two rear clusters plus two corner markers. Plot every face centroid; the distribution
answers what the box cannot.

### 3. Engine-off and lights-off on driver exit are TWO different bugs

**Engine** is script and is fixable. `CarScript.OnDriverExit` calls `EngineStop()` when the gear
is not neutral (`carscript.c:940-948`); `Transport.OnDriverExit` is a no-op
(`3_game/vehicles/transport.c:224`), so an override that does not call `super` loses nothing. Add
`ShiftTo(GetNeutralGear())` (`car.c:260`, `:251`) or a running engine plus `Brake.driverless`
makes the car creep. Measured working: `engine=ON` on client and server, at the event and at
+500 ms and +2 s.

**On 1.29, lights are NOT fixable that way.** The native forces `LightIsOn()` false on the CLIENT as soon
as the driver seat empties, and vanilla's `m_Headlight` is slaved to it
(1.29 `carscript.c:2116-2156`; on 1.30 the front light of `VehicleLightsComponent`, `carscript.c:1874-1908`), so the beam is always destroyed and **re-asserting server-side cannot
bring it back**. The working pattern decouples the beam from `LightIsOn()`:

1. a synced `bool` intent + an own `CarLightBase` member;
2. `RegisterNetSyncVariableBool` on the intent in the constructor;
3. `ToggleHeadlights` override that records the intent and `SetSynchDirty()` on server — the
   native exit-clear does NOT call `ToggleHeadlights`, which is exactly why the intent survives it;
4. a `ManageExitLight()` that creates/destroys the own beam edge-triggered, attached at the
   midpoint of the two headlight memory points, called from a `UpdateLightsClient` override;
5. `EEDelete` cleanup so the beam cannot outlive the car.

To make the parked beam appear promptly, copy vanilla's own line rather than inventing one:
`ForceUpdateLightsStart(); g_Game.GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(ForceUpdateLightsEnd, 100, false);`
(1.29 `carscript.c:535-536`; the pair is defined at 1.29 `:2981` and `:2990`).


**On 1.30 there is nothing to fix.** Measured on 1.30.164200, `LightIsOn()` stays true on the server and on the client when the driver gets out with the lights on, so the pattern above finds nothing to do; its step 3 no longer compiles (`ToggleHeadlights` was deleted), and `ForceUpdateLightsStart`/`End` are empty `[Obsolete]` declarations (`carscript.c:2805-2809`). See `dayz-1-30-vehicles.md`.

### 4. No bulbs mounted = brake and tail never light, and it reads as a failed fix

`m_HeadlightsState` stays `NONE` without HeadlightH7 in the reflector slots, and the rear beams
are gated on it (`carscript.c:522-543`, `:1929`). Testing brake lights on a car whose bulbs sit in
the cargo produces a confident false FAIL.

Related and cheap: `OnDebugSpawn` must use **`CreateAttachment`**, not `CreateInInventory`.
Vanilla's `SpawnUniversalParts` (`carscript.c:2500-2528`) drops everything into cargo, so every
test cycle starts with manual assembly and one forgotten bulb poisons the run.

### 5. Measure the setter against a VANILLA car spawned alongside

`SetObjectMaterial` / `GetObjectMaterial` are `proto native` (`entityai.c:2884-2885`): whether they
work is not decidable by reading source. Probing only the car under test cannot separate "our model
is wrong" from "this build does not apply overrides at all". Spawn a stock `CivilianSedan` next to
it and run the identical call, into the SAME log:

| vanilla switches | ours switches | conclusion |
|---|---|---|
| yes | yes | no override fault; it was the bake |
| yes | no  | the fault is in OUR model |
| no  | no  | the environment does not apply overrides; the probe never measured the setter |
| no  | yes | incoherent, repeat |

Resolve the selection **by name** with `GetHiddenSelectionIndex` (`entityai.c:2778-2781`) and print
the resolved index; never hardcode an index onto a vanilla car. If the resolve fails, SKIP — do not
fall back to 0, which is the front-left light of the CarScript ABI (`carscript.c:174-182`) and
corrupts both the car and the measurement.

And adjudicate by photo: the `got=` of a readback is the setter's echo, not proof that the engine
drew anything.

## Invariant 15d: two hidden selections cannot own the same face

**Two hidden selections cannot own the same face: a hiddenSelection that overlaps
another one never gets a material slot, and `SetObjectMaterial(index, ...)` on it is a
SILENT no-op (measured 2026-09-10, Arma2Quad; closed in game).** The quad's third bulb
(`light_dashboard`, `hiddenSelections[8]`, which is `SELECTION_ID_DASHBOARD_LIGHT` at
`scripts/4_world/entities/vehicles/carscript.c:182`) never lit, while `light_1_1` and
`light_2_1` lit from the SAME rvmat pair through the SAME call
(1.29 `carscript.c:2487`; on 1.30 the same `SetObjectMaterial` call is in `VehicleLightsComponent.SetSelectionMaterial`, `vehiclelightscomponent.c:79`, with the dashboard pair registered at `carscript.c:230-231`). The only difference lived in the model: the bulb's 12 faces were
also claimed by `camo1`, which is `hiddenSelections[9]`. camo1 won the faces, so index 8
addressed nothing.
**The diagnostic is a face-ownership census INSIDE the same file**, listing for every
`sections[]` entry which OTHER selections claim its faces. Every light that worked came
back exclusive; the dead one was the only shared one. That is a relative measurement
through one reader, so it holds regardless of how your p3d library reports conventions.
**Overlap with an ANIMATION selection is fine and must be preserved** - here the same 12
faces are also in `drivewheel`, the handlebar bone, because the bulb has to turn with the
bars. Only hiddenSelections compete for a material slot.
**Being listed in model.cfg `sections[]` is necessary but NOT sufficient**:
`light_dashboard` was in `sections[]` the whole time.
Fix by removing the faces from the other hiddenSelection, and drop a point from it only
when no REMAINING face of that selection still uses it, so shared border vertices survive.
Three hypotheses were checked and refuted BEFORE this one, each worth a build+test cycle:
(a) "the faces need their own material" - given to 48 faces across LODs 0-4, still dead;
(b) "the selection is empty in the ViewPilot LOD" - every light selection is empty there,
including the ones that work; (c) "the engine renumbers by real sections so index 8 is
lost" - malformed, because `hiddenSelections[]` and `sections[]` agree on indices 0-8 and
only diverge at 9. Confirmation is cheap and does not need the light to work: with the
lights OFF the bulb switched from the body material to the lights material, which alone
proves index 8 now reaches those faces.
Corollary that removes a suspect: `UpdateLightsServer` is NOT server-only - `carscript.c:1853-1859`
guards only the CLIENT half with `#ifndef SERVER`, so `SetObjectMaterial` runs on the client
too and replication is never the explanation for a light material that fails to apply.

## Reading dark dashboard art at night

**Reading a dark-art dash at night (added 2026-08-19):**
Instrument-cluster art driven by `dashboardMatOff` (emissive 0) is invisible in an in-game
night, which reads exactly like "the texture never applied". Pin server time
(`serverTime="YYYY/M/D/12/0"` in serverDZ.cfg) before judging any interior art gate, and
give the OFF material a faint emissive so the furniture stays readable after dark.
