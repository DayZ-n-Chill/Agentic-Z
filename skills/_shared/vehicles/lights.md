# Vehicle lights

Why a car's lights do not switch, in the order to check it: material paths, which faces each light selection owns, bulbs, driver exit, and how to test the material setter against a vanilla car. An LED or indicator built from a hidden selection and a scripted point light is in `emissive-leds-and-dynamic-lights.md`.

## The light selections script expects

`CarScript` fixes the light selection indices by position, from `SELECTION_ID_FRONT_LIGHT_L` onward (`P:\scripts\4_world\entities\vehicles\carscript.c:174` to `:182`):

| Index | Constant |
|---|---|
| 0, 1 | `SELECTION_ID_FRONT_LIGHT_L`, `_R` |
| 2, 3 | `SELECTION_ID_BRAKE_LIGHT_L`, `_R` |
| 4, 5 | `SELECTION_ID_REVERSE_LIGHT_L`, `_R` |
| 6, 7 | `SELECTION_ID_TAIL_LIGHT_L`, `_R` |
| 8 | `SELECTION_ID_DASHBOARD_LIGHT`, registered with `dashboardMatOn` and `dashboardMatOff` (`carscript.c:230` and `:231`) |

The selection names are free; their order in `hiddenSelections[]` is not. Index 9 and above has no light meaning in `CarScript` and needs the mod's own script.

`VehicleLightsComponent.SetSelectionMaterial` (`P:\scripts\4_world\entities\vehicles\components\vehiclelightscomponent.c:66`) applies each material with `SetObjectMaterial` (`vehiclelightscomponent.c:79`). `SetObjectMaterial` and `GetObjectMaterial` are native (`P:\scripts\3_game\entities\entityai.c:2884` and `:2885`). `UpdateLights` runs `UpdateLightsClient` inside `#ifndef SERVER` and `UpdateLightsServer` on both sides (`carscript.c:1853` to `:1858`), so the material call also runs on the client and replication never explains a light material that does not apply.

The key that switches vehicle lights is `UAToggleVehicleLights` (`P:\scripts\4_world\classes\useractionscomponent\actioninput.c:855`); `UAToggleHeadlight` is the head torch (`actioninput.c:782`).

## Where the beams attach

With both headlight bulbs in place (`CarHeadlightBulbsState.BOTH`), one combined front light attaches at the midpoint of the two headlight memory points (`carscript.c:1891` to `:1896`), so a `*_dir` point does not steer the beam. Measure that midpoint against the body surface on the centre line; a point inside the shell traps the light. The front light is handled in `carscript.c:1874` to `:1908`: with one bulb it attaches on that headlight's own point in `VehicleLightMode.SEGREGATED`; with both it uses `AttachLightOnObject` at the midpoint in `VehicleLightMode.AGGREGATED`. Check the reverse light point the same way: the rear light attaches at `m_ReverseLightPoint` (`carscript.c:1934`).

## Check the selections before the materials

Before reassigning a lamp, print the face count and bounding box of every light selection (measured on a test car):

- A left or right selection whose bounding box crosses `x=0` owns centre geometry, such as a tailgate bar.
- Dozens of faces packed into about 1 cm (44 faces in 0.01 m on the test car) are degenerate and draw nothing.
- Brake (2, 3) and tail (6, 7) must own separate faces. If they overlap, the later `SetObjectMaterial` wins and the result is unpredictable.

A bounding box is not enough to know what a selection holds: a `tail` selection spanning 3,788 mm of a 4,086 mm car held only the two rear clusters and two corner markers. Plot every face centre.

## A leading backslash on a material path

`SetObjectMaterial` accepts `MyMod\data\x.rvmat` and rejects `\MyMod\data\x.rvmat` without an error or a log line; reading the material back still shows the old one. Measured in game with only the leading character changed.

Vanilla never writes the backslash on a material path: every `hiddenSelectionsMaterials[]` entry of `CivilianSedan` and every `*MatOn` and `*MatOff` key after it starts at `dz\` (`P:\DZ\vehicles\wheeled\config.cpp:5180` to `:5210`). `model=` paths keep their leading backslash and resolve fine, which is why a mixed file passes review. Apply this to `hiddenSelectionsMaterials[]` and every `*MatOn` and `*MatOff` key, and Grep for `"\\MyMod[^"]*\.rvmat"` before blaming anything else.

## Lamp faces outside every hidden selection

A ripped car often arrives with each lamp in two pieces: a large piece (`tail`, `light_left_static`, `light_right_static`, `light_dashboard_static`) that is not in `hiddenSelections[]`, and a small switchable insert that is. On a test car, 19,310 faces could never switch, against inserts of 42 and 318 faces.

The symptoms read as material bugs:

- A lamp piece always faintly lit with no glass: the large piece wears a constant emissive that no setter reaches.
- Only one of two bulbs lights: only the insert is in the selection.
- Position lamps that seem dead: they light, but 42 lit faces sit among 1,555 unlit ones.

Count faces per selection and cross them with membership before touching a material.

## Two hidden selections on one face

A face claimed by two hidden selections gets a material slot for only one of them, and `SetObjectMaterial` on the other index does nothing, silently. Measured in game on a test quad: the dashboard bulb (`light_dashboard`, index 8) never lit while two other bulbs lit from the same material pair through the same call. Its 12 faces were also in `camo1` at index 9, which took them.

- Find it by listing, for every `sections[]` entry in the model, which other selections claim its faces. Every working light comes back exclusive.
- An overlap with an animation selection is fine and must stay: the same 12 faces are in `drivewheel`, the handlebar bone, so the bulb turns with the bars. Only hidden selections compete for a material slot.
- Being in `model.cfg` `sections[]` is needed but not enough; `light_dashboard` was listed there throughout.
- Fix it by removing the faces from the other hidden selection. Drop a vertex from that selection only when none of its remaining faces uses it, so shared border vertices survive.
- What did not fix it: giving the faces their own material, and the View Pilot LOD, where every light selection is empty, the working ones included. The engine does not renumber indices by real sections either: `hiddenSelections[]` and `sections[]` agree on indices 0 to 8 and only differ at 9.
- To confirm the fix without the light working: with the lights off, the bulb switches from the body material to the lights material, which proves index 8 now reaches those faces.

## Bulbs must be mounted

`m_HeadlightsState` comes from the bulbs in the `Reflector_1_1` and `Reflector_2_1` slots and stays `NONE` without them (`UpdateHeadlightState`, `carscript.c:522` to `:543`; `BOTH` is set at `carscript.c:529`). A ruined bulb counts as missing. The rear light is attached only when it is not `NONE` (`carscript.c:1929`). Testing brake lights on a car whose bulbs sit in cargo gives a confident false fail.

`SpawnUniversalParts` adds the four `HeadlightH7` bulbs with `CreateInInventory` (`carscript.c:2500` to `:2506`), which may put a part in cargo rather than its slot (`P:\scripts\3_game\systems\inventory\inventory.c:876` to `:893`). Use `CreateAttachment` in your own `OnDebugSpawn` so a test does not start with one bulb missing.

## When the driver gets out

The engine side is script. `CarScript.OnDriverExit` calls `EngineStop` when the gear is not neutral (`carscript.c:940` to `:948`), and `Transport.OnDriverExit` is empty (`P:\scripts\3_game\vehicles\transport.c:224`), so an override that skips `super` loses nothing there. Add `ShiftTo(GetNeutralGear())` (`ShiftTo` at `P:\scripts\3_game\vehicles\car.c:260`, `GetNeutralGear` at `car.c:251`, both native), or a running engine with `Brake.driverless` makes the car creep. Measured in game: the engine stays on, on client and server.

The lights side depends on the version. On DayZ 1.30, `LightIsOn()` stays true on server and client when the driver gets out with the lights on (measured in game), so there is nothing to fix. `ForceUpdateLightsStart` and `ForceUpdateLightsEnd` are empty obsolete declarations (`carscript.c:2805` to `:2809`), and `carscript.c` has no `ToggleHeadlights`. On DayZ 1.29 the native cleared `LightIsOn()` on the client when the driver seat emptied (not checked on `P:\`, which holds 1.30). The 1.29 workaround kept its own beam: a net-synced `bool` for the driver's intent, its own `CarLightBase` created and destroyed at the headlight midpoint from an `UpdateLightsClient` override, a `ToggleHeadlights` override to record the intent, and cleanup in `EEDelete`. It is not needed on 1.30, and its `ToggleHeadlights` override no longer compiles. See `dayz-1-30-vehicles.md` for the version changes.

## Test the setter against a vanilla car

Whether the native `SetObjectMaterial` works cannot be read from source. Probing only the car under test cannot tell "our model is wrong" from "this environment applies no overrides". Spawn a stock `CivilianSedan` beside it and run the same call into the same log:

| Vanilla switches | Ours switches | Conclusion |
|---|---|---|
| Yes | Yes | No override fault; look at the bake |
| Yes | No | The fault is in our model |
| No | No | The environment applies no overrides; the probe never measured the setter |
| No | Yes | Inconsistent; repeat |

Resolve the selection by name with `GetHiddenSelectionIndex` (`entityai.c:2778` to `:2781`) and print the index; never hardcode an index on a vanilla car. If the lookup fails, skip the test instead of falling back to 0, which is the front left light. Judge by a screenshot: a material read back is the setter's echo, not proof that anything was drawn.

## Dark dashboard art at night

Instrument art driven by `dashboardMatOff` (emissive 0) is invisible at night in game, which looks exactly like a texture that never applied. Pin the server time to midday (`serverTime="YYYY/M/D/12/0"` in `serverDZ.cfg`) before judging interior art, and give the off material a faint emissive so the dashboard stays readable after dark.
