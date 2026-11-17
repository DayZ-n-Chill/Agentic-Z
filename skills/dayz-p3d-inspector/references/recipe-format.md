# The Recipe JSON and what the builder writes

The data contract between the extractor, the viewer and the builder of `/dayz-p3d-inspector`: the Recipe's fields, the LOD types it knows, and how each part is turned back into a `.p3d`.

Tool behaviour, not game facts. The LOD resolution values are the Bohemia `.p3d` scheme; the ones vanilla uses are confirmed in `_shared/models/lods.md` from the LOD list in vanilla file headers such as `P:\DZ\gear\camping\wooden_case.p3d`.

## Recipe JSON

```json
{
  "meta": {
    "source": "model.p3d",
    "version": 1,
    "mode": "audit|propose|demo"
  },
  "lods": [
    {
      "type": "visual_0|visual_1|visual_2|visual_3|geometry|fire_geometry|view_geometry|landcontact|roadway|paths|hitpoints|memory|shadow",
      "resolution": 0.0,
      "num_points": 328,
      "num_faces": 640,
      "geometry": { "positions": [], "normals": [], "uvs": [], "material_groups": {} },
      "wireframe": { "positions": [], "edges": [], "faces": [] },
      "selections": { "name": { "vertices": [], "faces": [], "vertex_count": 0, "face_count": 0 } },
      "properties": { "autocenter": "0" }
    }
  ],
  "memory_points": [
    { "index": 0, "position": [0, 0, 0], "selections": ["name"], "category": "center|interaction|axis|placing|port|proxy|other", "label": "name" }
  ],
  "axes": {
    "axis_name": { "points": [[0, 0, 0], [0, 1, 0]], "direction": [0, 1, 0], "length": 0.015 }
  },
  "bounding_box": { "min": [], "max": [], "size": [], "center": [] },
  "referenced_paths": { "textures": [], "materials": [] }
}
```

- `material_groups` keys are `"texture|material"`, joined by a pipe; either side may be empty.
- UVs are stored V-flipped (the glTF convention) so they draw correctly in the viewer. The builder flips them back before writing.
- `geometry.positions` is a triangle soup: three entries per face. `selections[].vertices` index the LOD's unique points instead. Do not mix the two (`round-trip-caveats.md`, "Selection indices").

Python use:

```python
import json, sys
sys.path.insert(0, r"<skill-dir>\scripts")
from p3d_inspector_extract import extract_recipe
from p3d_inspector_viewer import generate_inspector_html
from p3d_inspector_build import build_p3d

recipe = extract_recipe("model.p3d", verbose=True)
generate_inspector_html(recipe, output_path="inspector.html", model_name="My Model")

with open("recipe_edited.json") as f:
    edited = json.load(f)
result = build_p3d(edited, "model_rebuilt.p3d", auto_fix_enabled=True, verbose=True)
# result = {"output_path", "lods_written", "fixes_applied", "warnings"}
```

## LOD types

The extractor maps a LOD's resolution to a type:

| Resolution | Type | Stored as | Notes |
|---|---|---|---|
| `0.0` to `10` | `visual_0` to `visual_3` | full geometry | the drawn LODs |
| `1.0e3` to `1.5e4` | `shadow` | wireframe | shadow volumes |
| `1.0e13` | `geometry` | wireframe | physical collision; needs `Component01` and so on, and mass |
| `1.0e15` | `memory` | points only | memory points and animation axes |
| `2.0e15` | `landcontact` | wireframe | ground contact points |
| `3.0e15` | `roadway` | wireframe | walkable surfaces |
| `4.0e15` | `paths` | wireframe | AI paths inside buildings |
| `5.0e15` | `hitpoints` | wireframe | hit points |
| `6.0e15` | `view_geometry` | wireframe | sight and action cursor |
| `7.0e15` | `fire_geometry` | wireframe | bullets |

Anything else becomes `unknown_<resolution>`, and the builder skips it with a warning. That includes the GeoPhys LOD (`4.0e13`) eight vanilla models carry (`_shared/conventions/assets.md`): a model with one loses it in a rebuild.

An earlier version of the tool used the Arma values `2.0e13` and `3.0e13` for Fire and View Geometry, and treated every resolution over `1.0e14` as `memory`. On real models that folded Memory, LandContact, Roadway, Paths, Hit points, View and Fire Geometry into one `memory` type and overwrote the real memory points. If a Recipe shows one huge memory LOD and no View or Fire Geometry, it came from that version: extract again.

## What the builder writes

- **Visual LODs.** Triangles rebuilt from `geometry.material_groups`, UVs flipped back to the DayZ convention, per-vertex normals merged into one shared normal pool.
- **Wireframe LODs** (`geometry`, `fire_geometry`, `view_geometry`, `landcontact`, `roadway`, `paths`, `hitpoints`, `shadow`). Faces rebuilt from `wireframe.faces`: triangles and quads as they are, larger polygons fanned into triangles. `properties` are kept. `autocenter=0` and `class=house` are added to the Geometry LOD when it has neither. Check both against what the model needs: `autocenter=0` belongs only on items whose config sets it (`_shared/models/named-properties.md`).
- **Memory LOD.** Any `lods` entry of type `memory` is ignored. The LOD is rebuilt from `memory_points` and `axes`, with one selection per name found in `memory_points[].selections[]`. This is where selections can be lost (`round-trip-caveats.md`).
- **Mass.** Written only on `geometry` and `fire_geometry` points. The per-point value comes from, in order:
  1. `lod.properties["_point_mass"]`, a float for that LOD;
  2. `recipe.meta.point_mass_default`, a float for the whole model;
  3. a guess: the builder looks for a material word in `referenced_paths` (metal, steel or iron 7800 kg/m³, wood 600, plastic 1200, otherwise 2000) and spreads `bounding box volume × density` evenly over the points.

  The extractor does not record the model's real point masses, so a rebuild replaces them with this guess unless one of the two overrides is set. Physics reads the point masses of the Geometry LOD (`_shared/models/named-properties.md`); a mass on the Fire Geometry LOD is what the audit reports as `ERR_MASS_ONLY_GEOMETRY` when the DayZ fork of py3d is in use, and on a vehicle it was the measured cause of a spawn below ground (`dayz-p3d-audit/references/vehicle-checks.md`). Remove it from the Fire Geometry LOD with py3d after a build.
- **Auto-fix** (on unless `auto_fix_enabled=False` or `--no-autofix`). When more than half the faces of the first Visual LOD have a stored normal pointing against their cross product, the builder reverses the winding of every face in every LOD and lists that in `result["fixes_applied"]`. Use it with care: that disagreement shows winding and normals disagree, not which is wrong, and reversing every face of a model whose normals were the wrong side turns it inside-out (`dayz-p3d-audit/references/winding-absolute-check.md`).
- **Not written.** Proxies, sharp edges, and anything a check would catch: missing paths, component coverage, action targets. Run `/dayz-p3d-audit` on the result.

## Collision winding after an edit (SP-003)

When a collision LOD was generated or edited, check it per component before deploying: every face that is not a proxy triangle must sit in a closed, convex `ComponentNN` and read inward. A LOD short of those prerequisites, or with a degenerate face, is unresolved, not healthy. A finding that the collision LOD is wound against the Visual LOD only triggers that check; never reverse a collision LOD just to match the Visual LOD. Reverse only the faces that read outward, and set their stored normals as `dayz-p3d-audit/references/killers-detail.md` section 1 says.
