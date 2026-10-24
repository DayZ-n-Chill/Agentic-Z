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

## Mass is not a named property

Physics uses the sum of the point masses on the Geometry LOD, which Object Builder sets with its mass tool and the audit prints (`check_geometry_mass` in `.claude/skills/dayz-p3d-audit/scripts/audit_p3d.py`). Six vanilla gear models also carry a `mass` named property, but the audit and physics read the point masses. Take the value from the matching vanilla `config.cpp` or an MLOD sample, and see `_shared/physics/mass-and-weight.md` for how it relates to config `weight`.

## autocenter

`autocenter = 0` is for placed objects only. Never set it on kits or handheld items: on those it makes the item float when dropped (`.claude/skills/dayz-p3d-audit/references/p3d-killers.md` section 3).

A placed object needs all three:

1. The `autocenter` = `0` named property on the Geometry LOD, and on any GeoPhys or Fire Geometry LOD the model has. The audit checks it (`check_autocenter_prop` in `.claude/skills/dayz-p3d-audit/scripts/audit_p3d.py`).
2. A `pos center` memory point at `(0,0,0)` in the Memory LOD (`p3d-killers.md` section 5, and `memory-points.md`).
3. `autocenter = 0;` in the object's class in `config.cpp` (`.claude/skills/dayz-p3d-audit/references/config-rvmat-checks.md`, "Required Properties for Placed Objects"). dayz-object-builder sends this line to dayz-config-specialist.
