# Get-in actions and proxy pose

How the get-in prompt decides a seat, which two registrations a cursor action on a vehicle needs, how to keep a proxied submodel where you placed it, where the occupant's pose really comes from, and why a part's `model=` changes both the fitted part and the loose item.

The symptom-first get-in checks are in `invariants-get-in-and-seats.md` and in `attachments-and-crew.md`, section "When a seat or door action does not appear"; the 1.30 changes to the condition are in `dayz-1-30-get-in-and-boats.md`. Proxy placement and detachable parts are in `proxies-and-detachable-parts.md`. Vanilla facts cite `P:\` (DayZ 1.30); the measured cases come from mod test vehicles (a helicopter, two quads, a coupe) and are mod behaviour.

## The get-in condition, link by link

`ActionGetInTransport.ActionCondition` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:26` to `:69`) offers a seat only when every link passes, in this order:

| Step | Check | Source |
|---|---|---|
| 1 | `CanGetIn()` on the vehicle; `Transport` returns `true`, and `Motorbike_01_ColorBase` overrides it | `actiongetintransport.c:36`; `P:\scripts\3_game\vehicles\transport.c:675`; `P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\motorbike_01.c:89` to `:95` |
| 2 | The ViewGeometry component under the cursor maps to a crew index through `CrewPositionIndex(componentIndex)` | `transport.c:182` |
| 3 | `CrewCanGetThrough(crewIndex)` is true; `Transport` returns `false` unless `CFGMODS_DEFINE_TEST` is defined, so a custom vehicle's script class must override it | `actiongetintransport.c:54`; `transport.c:727` to `:734` |
| 4 | `IsAreaAtDoorFreeDiag`, the collision box check around the `CrewEntry` transform | `actiongetintransport.c:54`; overloads of `IsAreaAtDoorFree` at `transport.c:853` to `:908`, default extents (0.5 m wide, 1.7 m tall) at `:898` to `:907`; the diag menu option `TRANSPORT_FREESPACE_DISABLED` skips it (`:910` to `:924`) |
| 5 | At least one seat selection passes `CanReachSeatFromDoors` | `actiongetintransport.c:64`; `P:\scripts\4_world\entities\vehicles\carscript.c:2177` to `:2199` |

For step 5, `GetDoorConditionPointFromSelection` maps `seat_driver`, `seat_codriver`, `seat_cargo1` and `seat_cargo2` to `seat_con_1_1`, `seat_con_2_1`, `seat_con_1_2` and `seat_con_2_2` (`carscript.c:2141` to `:2160`). `CanReachSeatFromDoors` needs that memory point to exist, ignores height and allows 1 m horizontally: vanilla script calls it with `1.0` as `pDistance` and the player's position as `pFromPos` (`actiongetintransport.c:64`), and `1.0` is also the signature's default (`carscript.c:2177`). The motorbike `SeatDriver` check inside `CanGetIn()` is in `motorbike-invariants.md`.

Fix the links in order. One envelope component in front of the seat components makes step 2 fail even when the seat cubes are valid, and rebuilding `seat_con_*` cannot help while the cursor hits that envelope; script changes cannot help while the model lacks the memory point. The envelope failure was seen on a custom vehicle; the order is vanilla's.

## Instrument before moving the condition point

`OffroadHatchback` and `Van_01` override `GetDoorConditionPointFromSelection` to return centred points (`P:\scripts\4_world\entities\vehicles\inheritedcars\offroadhatchback.c:364`; `P:\scripts\4_world\entities\vehicles\inheritedcars\van_01.c:269`). That is not enough to predict a change on your own model. A quad returning the approach points `pos_driver` and `pos_codriver` was changed to return centred crew points, with two vanilla cars, a sibling mod and offline distances of 0.85 m and 0.83 m all in favour. In game the driver entering from the right ended up turned 15 to 20 degrees, and the co-driver could not be reached from either side. It was reverted.

Before changing which point the method returns, override it to log `pSeatSelection`, `pFromPos` and `pDistance` on every call; one run settles which point and distance each call uses. If you cannot log it, ship that change alone so the result can be traced to it.

## A cursor action on a vehicle needs two registrations

A custom `ActionInteractBase` offered while the player looks at a vehicle needs both:

1. Its typename added in a `modded class ActionConstructor` override of `RegisterActions(TTypenameArray actions)`, after `super` (`P:\scripts\4_world\classes\useractionscomponent\actionconstructor.c:27`; vanilla inserts `ActionGetInTransport` at `:302`).
2. `AddAction(MyMod_Action)` in the vehicle script class's `SetActions()` override, after `super`.

The cursor reads the target's own action list. `ActionInteractBase.GetInputType` returns `InteractActionInput` (`P:\scripts\4_world\classes\useractionscomponent\actions\actioninteractbase.c:61`), which inherits `ContinuousInteractActionInput` (`P:\scripts\4_world\classes\useractionscomponent\actioninput.c:558`), and that sets `m_DetectFromTarget = true` (`:552`), so `UpdatePossibleActions` (`:354`) collects the actions of `target.GetObject()` and its parent (`:382` to `:386`). Vanilla relies on it: `CarScript.SetActions` adds `ActionOpenCarDoorsOutside`, `ActionCloseCarDoorsOutside` and `ActionGetInTransport` (`carscript.c:2315` to `:2317`), and none of them is in `PlayerBase.SetActions`.

`PlayerBase.SetActions` (`P:\scripts\4_world\entities\manbase\playerbase.c:1695` to `:1745`) is where actions with no cursor target go, such as those offered to a seated player: start and stop engine with their boat and motorbike variants (`:1707` to `:1712`), `ActionSwitchSeats` (`:1713`), the inside door actions (`:1714`, `:1715`) and `ActionGetOutTransport` (`:1728`). That case is in `seated-actions-and-get-in-faults.md`, section "An action for a seated player needs two registrations".

To find a dead link, log once, rate limited, at registration, at action construction, and in `ActionCondition` after a successful target cast. The first missing line names the broken link.

Several `modded class PlayerBase` files can coexist in one mod, but no two may add the same field or the same new method. A `SetActions` override can go in any of them, and each must call `super.SetActions()`.

When the prompt shows, the hand animation plays and the server logs the door as open, but the door does not move, the script chain is fine. Suspect the animation side: the selection content in the binarized model, the skeleton bone or the axis. `SetAnimationPhase` is the boundary between the two.

## Keep a proxied submodel in place

A visual-only submodel with several LODs and no Geometry LOD, placed in the shell by a proxy, was re-centred when binarized: the offset moved into the ODOL `model_info.bounding_center` while the shell's proxy matrix stayed as authored, so the part shifted. To prevent it:

- Give the submodel a Geometry LOD, even an empty one.
- Set its named property `autocenter=0`.
- After binarizing, read the deployed ODOL and require `model_info.bounding_center == (0,0,0)` within your tolerance.
- Compare the submodel's centroid and the shell's proxy transform with the expected world pose.

Treat a non-zero bounding centre as a risk to the pose, not as the exact visual offset. This was seen on one custom vehicle and checked against working vanilla and community multi-LOD proxies; it is not a claim about every single-LOD proxy.

## The occupant is placed by the ViewGeometry crew proxy

Moving `crewdriver` in the Memory LOD does not move the rider. On a quad, two runs that differed only by that point moved 40 mm forward showed the pelvis and both hands within 5 mm, inside the noise (standard deviation 0.05 to 0.08 mm). The pelvis sat at Z +0.2928 while the ViewGeometry `crewdriver` proxy sat at +0.2948.

The anchors live in three places and must move together:

| LOD | Names | Points |
|---|---|---|
| Memory | `crewdriver`, `crewcodriver` | 1 |
| ViewGeometry | `crewdriver` and `proxy:\dz\vehicles\wheeled\proxies\crew_driver.001` | 3 |
| Geometry | only the `proxy:\...` name, not the `crewdriver` alias | 3 |

The two ViewGeometry names share the same point objects, so a script that walks both selections moves them twice unless it de-duplicates by identity. The Geometry LOD has only the `proxy:\...` name, so a checker that looks up `crewdriver` there raises `KeyError` instead of reporting a difference.

A cheap offline check: the offset from Memory to ViewGeometry must match what the model shipped with, and in a healthy model it is the same for every crew position (0.0, 100.7 and 200.3 mm for driver and co-driver alike on one quad). Different offsets on two seats mean one copy moved and the others did not. On another quad that showed as 18.9 mm of X disagreement on the co-driver, which the player saw as the camera jumping for a moment on getting in: the engine seats you with one anchor and corrects to the other.

## A part's `model=` fills the proxy

The proxy baked into the vehicle reserves a slot and a transform; the mesh comes from the `model=` of whatever item is attached, the same way fitting a ruined wheel changes the wheel you see. Vanilla shows it: `Hatchback_02_Wheel` (`P:\DZ\vehicles\wheeled\config.cpp:8980`) and `Hatchback_02_Wheel_Ruined` (`:9006`) share a proxy and differ in `model=` (the ruined wheel also overrides its radius, width and tyre values), and every door is its own file in a `proxy\` folder: `Hatchback_02_Door_1_1` (driver, `:9019`), `Hatchback_02_Door_2_1` (co-driver, `:9144`) and `Hatchback_02_Door_1_2` (`:9155`). The Niva (`HatchbackWheel` `:853`, `HatchbackWheel_Ruined` `:882`, `HatchbackDoors_Driver` `:908`, `HatchbackDoors_CoDriver` `:1030`) and the `CivilianSedan` (`CivSedanWheel` `:4762`, `CivSedanWheel_Ruined` `:4788`, `CivSedanDoors_Driver` `:4803`, `CivSedanDoors_CoDriver` `:4927`) follow the same pattern.

One `model=` therefore drives both the fitted part and the loose item, because they are the same entity in two states. You cannot use it to fix an inventory preview, a loose item or a fitted mesh alone. Pointing a co-driver door item at the driver door's `.p3d` put a left-hand door on the right side of a deployed test car.

Before changing a part's `model=`, write down what the fitted part and the loose item should each look like. If they differ, the fix belongs in the part's own `.p3d`, a separate item class, or the host's `hiddenSelections`, not in a path swap.
