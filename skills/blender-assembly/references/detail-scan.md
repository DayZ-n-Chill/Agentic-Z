# Detail scan protocol

How to scan a reference image zone by zone when writing the detail list of `blender-assembly` Phase 1.5, which texture-side details belong in the list and where each lands in the DayZ texture set, and how to tell three kinds of linework apart. It is a planning method, not a statement about the game; the texture destinations follow the suffix roles in `skills/_shared/textures/suffixes-and-sizes.md`.

Added 2026-07-30.

## Why scan by zone

A detail list written from one glance misses the small marks that define the object's identity (a bevel highlight, a row of rivets, a stain), because the whole reference gets a single look. Scan zone by zone and record the scan next to the list.

## The scan

- **Scan method.** Use `component-zones` when the part boundaries are already planned: walk each part's region of the reference. Otherwise use `grid-3x3`: inspect every cell, skipping none. Write which method was used at the top of the detail list.
- **Count floor by complexity.** Simple: 3 details. Moderate: 6. Complex: 10. Very complex: 16. A list below its floor means the scan stopped early; go back to the reference, not to memory. The floor of at least 3 distinct feature types on a hero object still applies; this one is about the count.
- **Record per detail.** Each row also carries where it is on the reference (zone or grid cell), the evidence (`seen` in a specific crop, or `inferred` from symmetry or occlusion) and a confidence from 0 to 1. Inferred and occluded details score low and must not be counted toward the floor.
- **Maps-to gate.** Every row names the technique that builds it (Rules 6 to 11) or the texture channel that carries it (the table below). A detail that maps to nothing is a planning failure: nothing reads prose, so it never reaches the model.

## Texture-side detail kinds

The technique column of the detail list covers geometry. These kinds are details too and belong in the same list, with their destination in the DayZ texture pipeline. The recipes are in the `dayz-texture-pipeline` skill and in `skills/_shared/textures/surface-recipes.md`.

| Kind | Reads as | DayZ destination |
|---|---|---|
| Local gloss | A low-roughness zone or a specular hotspot on one region | A gloss zone in the `_smdi`, or the rvmat |
| Stain, patina, fade | Darker dirt biased toward cavities, gravity streaks, an oxidation hue, sun bleaching | A layer in the `_co` composite |
| Scratch, chip | A thin bright or dark line that may expose the underlayer color at edges | `_co`, plus detail in the `_nohq` bake |
| Decal, painted line | A flat printed graphic or stripe: color contrast, zero relief | `_co` (or `_ca` when it needs alpha) |
| Emissive | A self-lit region (LED, screen, ember) | The rvmat's emissive settings |

## Three kinds of linework

Linework is three different techniques that read differently. Pick the one the evidence supports, and never default to geometry:

- An **engraved groove** is real negative relief that catches shadow: `panel_recess` or a boolean.
- A **painted line** is color only: `_co`.
- A **panel line** is a soft dark ambient-occlusion seam with no depth: the bake, or a darkening in the `_co`.

A hard groove where the reference shows a soft dark line is a wrong detail even though "a line" exists.
