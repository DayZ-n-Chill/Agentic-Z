# Named selections

What a named selection in a `.p3d` is, which LOD each kind belongs in, who reads it, and how tools lose it without a word.

## What a selection is

A named selection is a set of the points and faces of one LOD, each with a weight. It is the set that matters, not the name: a selection whose name is present but which holds no points does nothing. Every LOD has its own selections, so a name that exists in the visual LOD does not exist in the Fire Geometry LOD until it is made there too.

Binarize stores selection names in lower case. The wooden case's collision component is written `Component01` in Object Builder and reads `component01` in `P:\DZ\gear\camping\wooden_case.p3d`. In the one case measured in game the case made no difference: `component01` collided exactly like `Component01` (`dayz-p3d-audit/references/killers-detail.md`, "No component selection"). Other names were not measured, so spell a selection as the config or script that uses it does.

## Which LOD, and who reads it

| Kind | LOD | Read by |
|---|---|---|
| Hidden selection (texture or material swap) | every visual LOD | `hiddenSelections[]` in config, then `GetHiddenSelectionIndex` (`P:\scripts\3_game\entities\entityai.c:2778`) and `SetObjectTexture` (`:2881`). Vanilla: `camoGround` on the wooden case (`P:\DZ\gear\camping\config.cpp:10180`). |
| Bone of a moving or hideable part | every visual LOD, and each collision LOD that should move with it | the `Animations` class in `model.cfg` (`selection=`), driven from script with `SetAnimationPhase` (`P:\scripts\3_game\entities\entity.c:15`); `HideSelection` and `ShowSelection` are wrappers over it (`P:\scripts\3_game\entities\entityai.c:3355`) |
| Axis of that part | Memory | the same animation class (`axis=`); see `memory-points.md` |
| Collision component `Component01`, `Component02` ... | Geometry, View Geometry, Fire Geometry | the engine; without one a collision LOD collides with nothing (`dayz-p3d-audit/references/p3d-killers.md` sections 2 and 8) |
| Damage zone part | Fire Geometry | `componentNames[]` of a zone in `class DamageSystem` (`MediumTent` zone `Body`, `P:\DZ\gear\camping\config.cpp:242`) |
| Action part (a door, a seat, a lid) | View Geometry | `GetActionComponentName` and `IsActionComponentPartOfSelection` (`P:\scripts\3_game\entities\object.c:186` and `:195`), both of which take the geometry to look in |
| Seat action `seat_driver`, `seat_coDriver`, `seat_cargo1` ... | View Geometry of a vehicle body | `actionSel` of the seat in `class Crew` (`P:\DZ\vehicles\wheeled\config.cpp:269`) |
| Wheel slot `wheel_1_1`, `wheel_1_2` ... | Fire Geometry of a vehicle body, holding the wheel's proxy triangle | `selection` of the slot in `CfgSlots` (`Slot_NivaWheel_1_1`, `P:\scripts\config.cpp:1030` to `:1034`) |
| Proxy `proxy:<path>.<index>` | every visual LOD where the other model shows | the engine; see `proxies.md` |
| Named point | Memory | script, by name; see `memory-points.md`. A selection's position is read with `GetSelectionPositionLS` and `GetSelectionPositionMS` (`P:\scripts\3_game\entities\object.c:863` and `:864`). |

The names buildings carry (door leaves, ladders, the points of the Paths LOD, loot and rain sound points) and the `liquid_source` selection of a well are in `building-selections.md`.

One name has no reader: `zbytek`, Czech for "the rest", is the selection Bohemia's models use for everything that is in no other selection. 275 of the 572 models under `P:\DZ\gear\` store it (for example `P:\DZ\gear\books\book_kniga.p3d`). A mod model does not need it, but generators often write it for the static part of a model.

A selection that only swaps a texture or material (a hidden selection) belongs in the visual LODs and nowhere else. A bone belongs in a collision LOD only when the collision has to move with the part; a checker that reports every visual selection missing from Geometry, Fire Geometry or View Geometry is asking a question, not naming an error.

Two of these rows fail silently when the selection is in the wrong LOD. Measured in game on a custom quad, not checked on `P:\`:

- A wheel-slot selection that exists only in the visual LODs lets the wheel attach as an item but never simulate: `WheelCountPresent()` stays 0 while `WheelCount()` is the full count (`P:\scripts\3_game\vehicles\car.c:348` and `:345`), and no log line says why. `/dayz-p3d-audit` checks this when it is given the vehicle's `config.cpp`.
- A seat selection needs its own View Geometry component: `seat_driver` and `seat_coDriver` must not share one.

## The get-in chain of a vehicle

Every vehicle seat is a chain of four names that must all resolve (`P:\DZ\vehicles\wheeled\config.cpp:269` to `:272`): `actionSel` (a selection in the View Geometry LOD), `proxyPos` (the crew proxy in the visual LODs, for example `crewDriver`), and `getInPos` with `getInDir` (two memory points). Check the chain as one thing, not file by file: the names in the `.p3d`, the same names in `model.cfg` `sections[]` and `skeletonBones[]`, and the `class Crew` fields in `config.cpp`. Each get-in point should lie within about a metre of its seat's proxy. The full gate is in `dayz-p3d-audit/references/vehicle-checks.md`.

## Membership lost by tools

A selection's name can survive a conversion while its points do not. The model then looks fine in a list of names and breaks in game: no door, wheel or suspension axes, no damage zones, no seats. The cases below were measured on one vehicle model and are tool behaviour, not checked on `P:\`.

- An ODOL to MLOD converter. In the binarized file a selection's members are stored as lists of faces and of vertices, with a separate list of weights that only skinned selections have. A converter that copies members only where weights exist drops every memory selection, since axes, damage zones and get-in points have no weights. The result was an MLOD with all 79 memory selection names and no points in any of them. The fix in that converter was to copy every listed vertex as a member with weight 1, which gave 79 of 79 selections their points back (two per axis, one per damage zone and get-in point):

  ```python
  # broken: members copied only when the selection has weights
  if ns.selected_vertices and ns.vertex_weights: ...

  # fixed: every listed vertex is a member
  if ns.selected_vertices:
      for vi in ns.selected_vertices:
          if vi < len(dst.points):
              sel.points[dst.points[vi]] = 1
  ```

  The same converter also skipped members whose weight byte was 0, which is suspect for skinned selections too, since a stored 0 can stand for full weight.
- The p3d inspector builder of `/dayz-model-tools`. Rebuilding a model from its Recipe can wipe the Memory LOD's selections; see `tools-p3d-inspector-round-trip.md`.
- An ODOL v55 reader. The same kind of converter, on a v55 vehicle model, did not parse the animation section: the reading went out of step there (not in the animation class itself), so damper and animation offsets could not be recovered from that file. Rebuild those animations from the source, or read them from a model you binarized yourself.

In a binarized model the selections of the visual LODs are stored as faces, so their points have to be read through the face corners. Memory and Geometry LOD selections list vertices directly. A check written for one kind reads nothing on the other.

Check membership, not names. After any conversion or rebuild, read the model with py3d and confirm each selection that matters still has members, the `_axis` selections of the Memory LOD first:

```python
for name, sel in lod.selections.items():
    print(name, len(sel.points), len(sel.faces))
```

`lod.selections` is a dictionary keyed by name, and `sel.points` and `sel.faces` are dictionaries keyed by the point or face object (`_shared/py3d-mlod-notes.md`).

## Placing parts from a selection

When a model breaks into separate part models (planks of a crate, debris), spawn each part at the centroid of the selection of that name in Visual LOD 0 of the whole model, not at the bounding box of the part's own `.p3d`. Object Builder recentres a part when it is exported on its own, so the two can differ by several centimetres and the part spawns sunk or floating (measured on a mod model, not checked on `P:\`).

```python
visual = next(l for l in model.lods if l.resolution == 0.0)
pts = [p.coords for p in visual.selections["plank_front"].points]
offset = tuple(sum(c[i] for c in pts) / len(pts) for i in range(3))
```
