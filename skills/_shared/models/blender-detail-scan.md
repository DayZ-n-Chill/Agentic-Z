# Scanning a reference for detail

How to read a reference image zone by zone when you write the detail list of `blender-assembly.md` ("Plan the detail"), which texture details belong in that list and where each lands in the DayZ texture set, and how to tell three kinds of linework apart. It is a planning method, not a fact about the game; the texture destinations follow the suffix roles in `_shared/textures/suffixes-and-sizes.md`.

## Why zone by zone

A list written from one look at the whole reference misses the small marks that make the object itself: a bevel highlight, a row of rivets, a stain. Scan it zone by zone and keep the scan next to the list.

## The scan

- **Method.** Use `component-zones` when the part boundaries are already planned: walk each part's region of the reference. Otherwise use `grid-3x3` and look at every cell. Write the method at the top of the detail list.
- **How many details.** Simple object 3, moderate 6, complex 10, very complex 16. A list below its count stopped early; go back to the reference, not to memory. The separate floor of 3 kinds of feature on a main object still applies.
- **Each row.** Besides the detail, note where it is on the reference (zone or grid cell), whether it was `seen` in a crop or `inferred` from symmetry or occlusion, and a confidence from 0 to 1. Inferred and hidden details score low and do not count toward the floor.
- **Each row names its target.** Every detail names the geometry technique that builds it (`blender-assembly.md`, "Geometry rules") or the texture channel that carries it (table below). A detail that maps to nothing never reaches the model.

## Detail that lives in the textures

These are details too and go in the same list, with their place in the DayZ texture set. The recipes are in the texture pack (`_shared/textures/README.md`), starting with `_shared/textures/surface-recipes.md`.

| Kind | Looks like | Goes to |
|---|---|---|
| Local gloss | A low roughness area or a specular hot spot on one region | A gloss area in the `_smdi`, or the `.rvmat` |
| Stain, patina, fade | Dirt gathered in cavities, streaks running down, an oxidation tint, sun bleaching | A layer in the `_co` |
| Scratch, chip | A thin bright or dark line, sometimes showing the under colour at edges | `_co`, plus detail in the `_nohq` bake |
| Decal, painted line | A flat printed graphic or stripe: colour contrast, no relief | `_co`, or `_ca` when it needs alpha |
| Emissive | A self lit area (LED, screen, ember) | The `.rvmat` emissive settings |

## Three kinds of linework

Linework is three techniques that look different. Pick the one the reference shows; never default to geometry.

- An engraved groove is real relief that catches shadow: `panel_recess` or a boolean.
- A painted line is colour only: `_co`.
- A panel line is a soft dark seam with no depth: the bake, or a darkening in the `_co`.

A hard groove where the reference shows a soft dark line is a wrong detail, even though "a line" is there.
