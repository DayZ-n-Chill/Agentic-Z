# DayZ asset conventions (Tier 2 topic)

Part of Tier 2. Asset conventions (textures, materials, models) and the DayZ LOD resolution table. Read it together with the core rules in `skills/_shared/dayz-conventions.md`, which still apply.

## Asset conventions

- Textures are `.paa` only, and every texture name ends in a role suffix. ImageToPAA picks compression and color space from the suffix (rules in `<DayZ Tools>\Bin\ImageToPAA\TexConvert.cfg`). Vanilla gear uses three:
  - `_co`: color (diffuse); `_ca` when it carries alpha
  - `_nohq`: normal map
  - `_smdi`: specular
- The other suffixes `/dayz-pack-texture` accepts (all with TexConvert rules and all used by vanilla textures under `P:\DZ`): `_lco`, `_lca` (terrain layer color), `_no`, `_non`, `_nopx` (other normal maps), `_sm` (specular), `_as`, `_ads`, `_adshq` (ambient shadow), `_mc`, `_mco` (macro, multiply color), `_dt`, `_detail`, `_cdt`, `_dtsmdi` (detail), `_mask` and `_sky`.
- A few vanilla textures use further suffixes that also have TexConvert rules but that `/dayz-pack-texture` rejects: `_nofhq` (`P:\DZ\data\data\water_nofhq.paa`), `_can` (`P:\DZ\plants_bliss\bush\data\b_betula_nana_lod1_can.paa`), `_dxt5` (`P:\DZ\plants\tree\data\t_base_dxt5.paa`), `_dxt1` (`P:\DZ\data\data\edgefoam_dxt1.paa`), `_4444` (`P:\DZ\data\data\detailmap_4444.paa`) and `_raw` (`P:\DZ\data\data\noise_raw.paa`).
- Materials are `.rvmat` files referencing the textures and assigning shaders.
- Models are `.p3d` files exported from Object Builder. Code that reads `.p3d` with py3d follows `skills/_shared/py3d-mlod-notes.md`.

## LOD canonical resolutions (DayZ-specific)

DayZ inherits Bohemia's `.p3d` scheme where a LOD's resolution value is its type tag. Some online guides quote `7e13` for ViewGeometry and `3e13` for FireGeometry; those values misclassify DayZ LODs.

| LOD | DayZ resolution | Purpose |
|---|---|---|
| Visual | `0.0`, `1.0`, `2.0`, ... | LOD0 = base, then progressively simplified |
| ShadowVolume | `10000`, `11000` (range 10000 to 19999) | Shadow casters |
| Geometry | `1.0e+13` | Physics collision |
| Memory | `1.0e+15` | Named memory points |
| GeoPhys | `4.0e+13` | PhysX geometry. Only 8 vanilla models carry one (pillows, stretchers, two cylinders, a wall); the audit classifies it but never asks for it |
| LandContact | `2.0e+15` | Foot/wheel contact |
| Roadway | `3.0e+15` | Surface characters walk on (buildings, rocks, the base building fence). A new item never needs one |
| Paths | `4.0e+15` | Walking routes inside buildings |
| HitPoints | `5.0e+15` | Hit points of vehicles, wrecks and many buildings and walls (for example `P:\DZ\structures\residential\houseblocks\houseblock_1f_corner.p3d`, `P:\DZ\structures\walls\wall_gate_camp.p3d`) |
| ViewGeometry | `6.0e+15` | Cursor / action raycast. Recommended: vanilla interactive gear carries one; proxies and clutter cutters don't |
| FireGeometry | `7.0e+15` | Bullet / projectile collision |

Verified by reading the LOD resolution list in the file header of vanilla `P:\DZ\gear\camping\wooden_case.p3d`: 9 LODs, with Visual(1..4), Geometry(`1e13`), Memory(`1e15`), LandContact(`2e15`), ViewGeo(`6e15`), FireGeo(`7e15`). `classify_lod()` in `skills/dayz-p3d-audit/scripts/audit_p3d.py` uses these values. A header scan of 4,000 vanilla binarized models under `P:\DZ\` found `1e13` in 3,758, `6e15` in 2,569, `7e15` in 2,627; a later scan of all 8,256 found `4e13` in 8 (for example `P:\DZ\structures\furniture\beds\pillow_grey.p3d`) and `2e13` only in `P:\DZ\vehicles\water\boat_01\boat_01.p3d`, as its buoyancy geometry; among `gear\` models with a Geometry LOD, 531 also have ViewGeo and 32 (proxies, clutter cutters, a bonfire) don't. The audit therefore treats Visual, Geometry and Memory as required (CRITICAL when missing), ViewGeo and FireGeo as recommended (NOTE when missing), and GeoPhys as optional (not reported).

The Roadway, Paths and HitPoints values were read the same way: the header of `P:\DZ\structures\specific\churches\chapel.p3d` lists `3e15`, `4e15` and `5e15` between Memory and ViewGeo, `P:\DZ\vehicles\wheeled\transitbus\transitbus.p3d` lists `5e15`, and `P:\DZ\gear\camping\fence.p3d` lists `3e15`. How many vanilla models carry each, and what they hold, is in `skills/_shared/models/lods.md`. The audit names these three and runs no check on them.

A `classify_lod()` that uses those values (a grep for `7e13` or `3e13` finds them) reports ViewGeo and FireGeo as unknown. The engine is unaffected, but the audit then reports "missing FireGeo / ViewGeo" on models that have them and skips its FireGeo checks, so real collision problems (bullets passing through, no action cursor) go undiagnosed.

Classify a LOD by a band around its value, never by equality: the header stores each value as a 32-bit float, and `classify_lod()` tests `5.9e15..6.1e15` for ViewGeo and the matching band for every other special LOD.
