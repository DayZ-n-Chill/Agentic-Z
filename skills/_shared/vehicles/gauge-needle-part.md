# Gauge needle part

How to build a gauge needle mesh that can be reused across vehicles, how to cut a real needle out of an imported cluster object, how to measure its rest angle and depth, and the two signs every new cluster face must copy from its neighbours.

The wiring in `model.cfg` is in `gauge-needles.md`. Everything here was measured offline on mod test vehicles (two quads and a coupe) and in game where it says so; it is not checked on `P:\`.

## A reusable needle

Keep two needles, large and small, each as a `.p3d` to drop in and an `.obj` to edit:

| Needle | Length | Width | Thickness | Triangles |
|---|---|---|---|---|
| Large | 0.02596 m | 0.00714 m | 0.00261 m | 182 |
| Small | 0.01298 m | 0.00357 m | 0.00130 m | 182 |

The small one is the large one at 50 percent. Sizes are unscaled; multiply if the vehicle is scaled uniformly.

Both sit in a canonical pose: pivot at the origin, tip along +X, rotation axis along +Z, with `needle_pivot`, `needle_axis` and `needle_tip` in the Memory LOD. Mounting one is a move to the dial centre plus a rotation that takes +Z to the dial normal. The pose is what makes it reusable; a needle saved at the angle and position its OBJ gave it is useless to another model. The pivot is the centre of the black hub, not of the whole object.

The 182 triangles of LOD 0 are a hub ring of 32 quads (64), a 32-sided cap (30), a hub skirt of 32 quads (64), and a blade of two octagons (12) and six sides (12). The selections are cut by radius: `hub` (158) and `blade` (24). The back of the blade sits at z = 0 and the whole part at z of 0 or more, with the hub cap a hair in front of the blade root.

Dial faces to go with them: a speedometer printed 0 to 150 km/h, a tachometer printed 0 to 6 (times 1000) with red from 5 to 6, and a fuel panel printed E, half and F. Check which way a replaced dial was printed before touching any angle: an old ATV tachometer printed 0 to 8 counterclockwise, so a needle turning counterclockwise over it was correct.

## The object called "needle" is not a needle

An imported cluster's needle object (`aguja_derecha`, Spanish for "right needle", in the source OBJ) has 105 faces:

| Part | Faces | Radius in canonical pose | Depth relative to hub |
|---|---|---|---|
| Hub: black ring and 32-sided cap | 33 | up to 0.0029 | 0 |
| Hub skirt: 32 quads, a closed collar | 32 | 0.0029 to 0.0036 | -0.0026 to 0 |
| Blade: two octagons and six side quads | 8 | 0.0029 to 0.02239 | -0.0026 to -0.0009 |
| Dial disc: 32 quads | 32 | 0.0036 to 0.02544 | -0.00235, flat |

Saving it whole files a gauge under a needle's name. The bounding box `0.0509 x 0.0509 x 0.0026` looks reasonable until you notice 0.0509 is the disc's diameter: the blade tip is at 0.88 of the object's largest radius, and the farthest vertex belongs to the disc. Drawing the silhouette shows it at once; measuring did not.

Cut by radius. Take `r_obj`, the largest in-plane radius of the whole object; drop every non-black face with any vertex beyond 0.95 times `r_obj`; require exactly 32 OBJ faces (64 triangles) to be dropped and stop with an error otherwise. Shift the canonical depth so the back of the blade sits at 0.

Do not cut by angular width from the hub. A blade triangle near the pivot covers a wide angle because it is close, not because it is a wedge. A 5 degree filter left 10 triangles of sliver at the tip, invisible in game; applied to another object it kept both octagons and five sides with no cap and the blade behind the hub. The rule gives different pieces on different objects, and none is the needle. "Bad" is not "invisible" either: that second piece, mounted on another quad, sat 1.89 mm in front of its painted disc and showed. Visibility is decided by each disc's `lift`, not by the part.

## A count is not a shape

One fuel needle passed through three wrong shapes:

- The angular width filter left a sliver at the tip (radius 0.01122 to 0.01217).
- Keeping everything made the farthest vertex a disc vertex (0.02544): the scale dropped from 0.665 to 0.585, the blade reached 88 percent of the arc and the whole disc landed on it. It passed a face count (182) and a review. It was caught by the rest angle jumping from 0.90 to 5.63 degrees with 32 ring points discarded, and by a drawing of the part.
- In both, the blade sat behind the hub plane and the pivot only 0.0004 m in front of the panel, so 360 of 546 vertices were behind the panel. Nothing measured depth until a check was added: flag any blade vertex behind the panel face (z below -0.0003).

The correct needle, cut by radius: 118 triangles in the `Gauges` material (cap 30, octagons 12, quads 76), tip at radius 0.0122 on the arc, no vertex behind the panel, rest 0.90 degrees with no ring points, angles unchanged.

Ask what else could produce a given count; if "the whole object" could, the count does not discriminate. A reviewer given the same criterion inherits its blind spot. Measure every dimension the player sees, including depth against what it covers, and look at a drawing of the part.

## Measure the rest angle on the built model

`rest` is the screen angle of the blade in the built `.p3d`. Taking the farthest point of the needle selection can return a hub disc vertex instead: a 32-sided ring at the same radius as the dial face (32 points at r = 0.0209 against the face at 0.0208, while the blade reaches only 0.0184). The angle then depends on set iteration order. Discard any ring of points at near-constant radius (a band beyond 0.97 times the largest radius, 10 or more points, spread over more than 90 degrees), then take the farthest remaining point.

Measured along the axis from the driver's eye on a quad: the painted disc at -0.3 mm with a bad `lift` of -0.0003 covered everything; blade at 0; hub from +0.8 to +2.5 mm; the original panel at +1.5 mm. With `lift` 0.0012 the disc sits between the blade and the panel.

When a needle object brings its own disc, keep the disc out of the animated selection. On one quad the original disc still travels inside `kmh` and `rpm`; that it stays hidden behind the new dial is assumed, not checked.

## New geometry joins no selection

Faces you add as new geometry are in no selection. On a test quad the 64 new dial disc faces were outside `drivewheel` while the needles were in it, and in game "when turning, both circles stay behind (the needles do rotate)". Put new faces and their points in the animated selection in every LOD that has dials. The symptom only shows while steering; no still screenshot reveals it.

A cheap check of the dial mapping: scaling the gauge in its own plane must change neither the UVs nor the angles (measured: UVs moved by 0.000000 px, angles 102.55 / 405.45 and 71.95 / 315.16 before and after). If they change, scale and mapping disagree.

## Two signs on every new face

A new face carries two independent signs: winding (vertex order, which decides culling) and the stored per-vertex normal (which decides lighting). Neither follows from "it must face the driver". Read both from neighbouring faces that already render correctly, and check them separately:

- `sign(<cross, axis>)` equal to that of the visible discs.
- `<stored_normal, cross>` of 0 or more at every vertex. A 60 degree smoothing never drops below 0.5.

Each failed once while the other was right:

- Stored normal wrong: winding matched the discs (`<cross, axis>` of -1.000), but the fuel panel and needle had stored normals written "toward the driver" (+1.000). By day they looked like the dials; at night they did not shine under the same material.
- Winding wrong: stored normals equalled the cross product everywhere, but the needle generator forced `<cross, axis> > 0` with the axis toward the driver while every other cluster face (discs, rings, numbers, panel, the imported needles) had it negative. Its 182 triangles were culled from the seat. Offline renders missed it because they draw both sides.

In an MLOD the raw cross product of a face points into the solid: on a quad 94 to 97 percent of flank faces do. So "the axis matches the dial's own cross product" means the axis points inward. To read a model's convention, pick faces whose outside is beyond doubt, such as the outermost flanks in X, and check the sign of `dot(normalize(cross), (1, 0, 0))`. Pick them carefully: a top strip with a roof rack gave 38 percent and decides nothing, while the flanks gave 3 and 6 percent over 2,400 faces each. Do not use a pilot point as judge: `dot(axis, pilot - pivot)` flips with which point you take (+0.142 against the pelvis, -0.994 against the eye on a quad whose cluster sits between them).

Leave out the functional LODs (Geometry `1e13`, View Geometry `6e15`, Fire Geometry `7e15`) when counting: they carry one or two untextured faces with normals at +0.6 that are never drawn. Decimated LODs of a base model can ship a few faces whose smoothed normal opposes the cross product (5 to 7 faces per LOD on one quad); report those apart from the gauge faces. Plant a known defect (negate one selection's normals in memory) and make sure the check flags every face of it.

## Judge winding by a visible flat neighbour

Counting faces whose cross product points away from the mesh centroid works on a convex solid and means nothing in a cockpit. Inside a test coupe it reported 0.0 percent "toward the driver", as if the whole model were reversed; it was not. A cockpit is a shell seen from inside and a cluster is almost a torus, so the centroid lies outside the material. Signed volume did not settle it either: it was negative for both variants, and neither mesh was watertight.

What decides is a flat surface in the same file that is known to be visible. The dashboard light face gave `<cross, axis>` of -1.0000 and the navigation screen -0.9858; the 100 nearly parallel faces of the new needle had the same sign. Flipping by the centroid count would have introduced the defect. Use centroid statistics only on convex shapes and signed volume only on meshes you have checked are watertight.
