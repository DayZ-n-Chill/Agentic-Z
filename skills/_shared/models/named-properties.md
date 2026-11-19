# Named properties

Key and value pairs set on a LOD in Object Builder (the LOD's Named Properties dialog). Binarize keeps them in the ODOL file as plain text, so vanilla values can be read back.

## What vanilla gear sets

A scan of the 572 models under `P:\DZ\gear\` for known keys stored with their values. A model is counted once per key.

| Key | Models | Values seen | Example |
|---|---|---|---|
| `lodnoshadow` | 418 | `1` on almost every hit | `P:\DZ\gear\camping\barbed_wire.p3d` |
| `placement` | 71 | `slopelandcontact`, `slope` | `P:\DZ\gear\camping\cartent.p3d`, `P:\DZ\gear\cultivation\cannabis_plant.p3d` |
| `damage` | 56 | `wall`, `tent`, `no` | `P:\DZ\gear\camping\fence_folded.p3d`, `P:\DZ\gear\camping\camo_net_shelter.p3d`, `P:\DZ\gear\containers\55galdrum.p3d` |
| `prefershadowvolume` | 40 | `0`, `1` | `camo_net_shelter.p3d`, `P:\DZ\gear\camping\cable_reel.p3d` |
| `sbsource` | 38 | `shadowvolume`, `explicit` | `cable_reel.p3d` |
| `forcenotalpha` | 23 | `1` | `P:\DZ\gear\consumables\chemlight.p3d` |
| `class` | 21 | `house`, `bushsoft`, `treehard` | `P:\DZ\gear\camping\bonfire.p3d`, `P:\DZ\gear\camping\underground_stash.p3d` |
| `map` | 14 | `house`, `hide`, `tree` | `cable_reel.p3d`, `barbed_wire.p3d` |
| `mass` | 6 | `40.000000`, `10.000000`, `0.150000` and others | `P:\DZ\gear\camping\wooden_case.p3d`, `P:\DZ\gear\medical\iodinetincture.p3d` |

`autocenter` is covered by its own rule, below. The meaning of each other key is Bohemia format knowledge that no vanilla script shows. When a mod model needs one, copy the key and value from the closest vanilla model of the same kind and say which model it came from.

## What vanilla buildings and props set

The same scan over the 8,256 models under `P:\DZ\` outside the Takistan folders (`structures_takistan`, `plants_takistan` and the other `*_takistan` folders, 2,370 more models that were not counted), for the keys buildings and placed props use. A model is counted once per key and value.

| Key | Models | Values seen (models) | Example |
|---|---|---|---|
| `class` | 2,922 | `pond` 1,176, `house` 821, `road` 362, `treehard` 193, `man` 113, `treesoft` 77, `clutter` 51 | `house`: `P:\DZ\structures\industrial\garages\garage_small.p3d` |
| `map` | 2,217 | `hide` 477, `house` 354, `building` 270, `tree` 219, `main road` 159, `tsign` 113, `track` 110 | `building`: `garage_small.p3d` |
| `damage` | 2,608 | `no` 1,717, `tree` 707, `wall` 98, `tent` 48, `building` 33 | `no`: `garage_small.p3d` |
| `lodnoshadow` | 3,337 | `1` 3,326, `0` 13 | `P:\DZ\structures\industrial\farms\barn_wood1.p3d`, once per visual LOD |
| `canocclude` | 357 | `0` 353, `1` 4 | `1`: `P:\DZ\structures\residential\misc\ladder.p3d`; `0`: `P:\DZ\gear\camping\t_fagussylvatica_2fmesh.p3d` |
| `drawimportance` | 806 | `0.1` 249, `0.01` 197, `0.05` 53, `0.3` 50 and others | `0.02`: `P:\DZ\structures\furniture\various\ladder_a_wood.p3d` |
| `autocenter` | 2,730 | `0` 2,723 | see below |

Which LOD carries what, read from the order the values sit in the file:

- **Building, Geometry LOD:** `class` = `house`, `map` = `building`, `damage` = `no`, stored together (`garage_small.p3d`; `barn_wood1.p3d` stores the three twice).
- **Visual LODs:** `lodnoshadow` = `1`, one copy per visual LOD (`barn_wood1.p3d` has five visual LODs and five copies).
- **View Geometry LOD** (by a reading of models converted back to MLOD; the file order alone only shows it is not the Geometry LOD): `canocclude`. Only four vanilla models set it to `1`, the climbable ladder props among them (`ladder.p3d`, `P:\DZ\structures\residential\offices\proxy\ladderlong.p3d`); 353 set it to `0`. Do not add `canocclude` = `1` to a model by habit.
- **Loose props and building part proxies:** `autocenter` = `0`, often with `drawimportance` (`ladder_a_wood.p3d` stores `0.02`; `P:\DZ\structures\Proxy_BuildingParts\ladders\ladder_long_proxy.p3d` stores `autocenter` alone).
- **Ladder sound, Geometry LOD:** `laddertype` is the one named property vanilla script reads. `ActionEnterLadder` looks it up on the Geometry LOD and defaults to `metal`; only `wood` changes the climbing sound (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actionenterladder.c:137` to `:149`; `P:\scripts\4_world\entities\dayzplayerimplement.c:3643`). The deer stands store `wood` (`P:\DZ\structures\residential\misc\misc_deerstand1.p3d`).

## Mass is not a named property

Physics uses the sum of the point masses on the Geometry LOD, which Object Builder sets with its mass tool and the audit prints (`check_geometry_mass` in `skills/dayz-p3d-audit/scripts/audit_p3d.py`). Six vanilla gear models also carry a `mass` named property, but the audit and physics read the point masses. Take the value from the matching vanilla `config.cpp` or an MLOD sample, and see `_shared/physics/mass-and-weight.md` for how it relates to config `weight`.

## autocenter

`autocenter = 0` is for placed objects only. Never put `autocenter = 0;` in the `config.cpp` class of a kit or handheld item: there it made a kit float when dropped (`skills/dayz-p3d-audit/references/p3d-killers.md`, Script-Side Gotchas).

A placed object needs all three:

1. The `autocenter` = `0` named property on the Geometry LOD, and on any GeoPhys or Fire Geometry LOD the model has. The audit checks it on the Geometry LOD only (`check_autocenter_prop` in `skills/dayz-p3d-audit/scripts/audit_p3d.py`).
2. A `pos center` memory point at `(0,0,0)` in the Memory LOD (`p3d-killers.md` section 5, and `memory-points.md`).
3. `autocenter = 0;` in the object's class in `config.cpp`. This config line is a mod practice that vanilla does not use: vanilla sets `autocenter` in no `CfgVehicles` class and keeps it on the model's Geometry LOD instead (`skills/dayz-p3d-audit/references/config-rvmat-checks.md`, "`autocenter` on placed objects"). dayz-object-builder sends this line to dayz-config-specialist.

### What vanilla stores

The rule above comes from mod debugging. What the vanilla files show, so a reviewer can weigh it:

- 2,730 of those 8,256 models store an `autocenter` property, 2,723 of them with the value `0`. That includes 509 of the 572 gear models, handheld items among them (`P:\DZ\gear\books\book_kniga.p3d`).
- 2,169 of those models store it exactly once. In `P:\DZ\gear\camping\wooden_case.p3d` and `book_kniga.p3d` the one copy sits in the Geometry LOD, next to the `mass` property on the wooden case, and not in the View or Fire Geometry LOD. 561 models store it more than once; `P:\DZ\gear\camping\fence.p3d` stores it seven times, once for each of its seven LODs.
- In vanilla `config.cpp` files the `CfgVehicles` default comes from the base class `All`, which sets `autocenter=1` (`P:\bin\config.cpp:1340`, key at `:1349`), and `Man: All` overrides it with `autocenter=0` (`:1703`, key at `:1709`). No item class sets the key. Outside `CfgVehicles`, `autocenter=0` sits on proxy classes under `CfgNonAIVehicles`, such as `ProxyPart` (`P:\DZ\gear\camping\config.cpp:13397`, key at `:13406`) and `ProxyVehiclePart` (`P:\DZ\vehicles\wheeled\config.cpp:23905`), and `autocenter=1` on four projectile proxies: `ProxyArrow_Composite` and three single round proxies such as `ProxyShotgunShell_pellets` (`P:\DZ\weapons\attachments\magazine\config.cpp:9454` and `:9570` to `:9586`).

So the named property on the Geometry LOD is common in vanilla, handheld items included. The float on drop recorded in `p3d-killers.md` was seen on a kit whose config class set `autocenter = 0`, a key no vanilla item class sets. One measured case where the property on every LOD plus the config line made a placed item float at knee height is in `skills/_shared/vehicles/placement-and-autocenter.md`; that note also covers where `autocenter=0` sits on a vehicle.

### On every collision LOD (not checked on `P:\`)

Measured on a mod's placed objects, not on vanilla: with `autocenter` = `0` on the Geometry LOD only, the Fire Geometry and View Geometry meshes of a placed object were recentered on their own bounding boxes, about 20 to 25 cm away from the visual mesh. Bullets passed through, a hologram stacked on the object fell to the ground, and the action cursor did not find it. Setting the property on every collision LOD the model has (Geometry, Fire Geometry, View Geometry, and Roadway, Hit points and LandContact when present) fixed all three. Vanilla does both, as the counts above show, so treat this as the safe choice for a placed object built from scratch (`generated-model-rules.md`, "`autocenter=0` on every collision LOD").

Also measured on a third-party storage mod, not checked on `P:\`: an invisible entity whose visual LOD holds only proxy triangles, used to carry and draw attachments, needed `autocenter = 0` in its config class. Without it the engine recentered the model and its memory points shifted (`_shared/models/memory-and-selections-authoring.md`).

## Reading and writing them with py3d

Tool knowledge, not a vanilla fact. In an MLOD read with py3d, a LOD's named properties are the dictionary `lod.properties`, and both the key and the value are strings:

```python
geometry_lod.properties["class"] = "house"
geometry_lod.properties["autocenter"] = "0"      # the string "0", not the number 0
print(dict(geometry_lod.properties))
```

A check such as `lod.properties.get("autocenter") != "0"` therefore compares with the string. Properties are set per LOD, so a value that every collision LOD needs is written once on each.
