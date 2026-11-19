# View Pilot LOD of a proxied car

What the View Pilot LOD (resolution 1100) of a car built as a shell plus proxies must carry, how to tell its three possible states apart, how to create it when it is missing, and how to count what the seated view holds before an in-game test. What the View Pilot is for, and how first person draws proxies, is in `view-pilot-and-first-person.md`; closing gaps the rider sees through is in `view-pilot-closures.md`. The cases were measured on mod vehicles: two imported cars and two quad bikes.

## The shell's View Pilot needs the body, not only proxy triangles

When a player gets in, the engine switches the shell to its View Pilot LOD. On an imported sports car the body then went invisible for seconds in first person, which vanilla never does. The shell's 1100 held 7 faces, only the proxy triangles (interior, doors, wheels), while the unbinarized vanilla `CivilianSedan` used as control carries 11,977 real faces there (interior, body and glass) plus 13 proxies. With only proxy anchors in the LOD, the body vanished until the proxies resolved. The interior file's 1100 was its full visual LOD, not the subset it was meant to be.

The fix merges the shell's LOD 0 into the 1100:

- Copy the shell's own geometry with point and normal indices remapped, and get or create its named selections, so `camo` and `light_*` keep working in first person.
- Copy the proxies only LOD 0 has exactly as they are (points, face and selection); a convenience proxy constructor would lose the frame. Leave out the faces and anchor points of proxies the 1100 already has.
- Check before saving: the original proxy selections intact (one face and three points each), the proxy set equal to the originals plus the copied ones, the number of bone companion selections unchanged, and the resolved vertices printed against the design budget (about 16k on that car). Binarize kept the merge exactly: 22,849 faces and 11 proxies.

A check of `facenormals <= 32768` is not an engine or load limit. Keep that number only as a declared local budget. For a load verdict, count a known-good model taken from the deployed PBO by the same MLOD or binarized route, then use the three verdicts of `binarize` (`binarize-vertex-budget.md`). A warning threshold alone never justifies cutting geometry, and the seed for a missing 1100 is not chosen by it.

## Three states, three fixes

A second imported car, opened with py3d, had ten LODs and no 1100: resolutions 0, 1, 2, 3, 4 and 10000, then Geometry (1e13), Memory (1e15), View Geometry (6e15) and Fire Geometry (7e15). The merge would have targeted a LOD that does not exist. So before the first in-game cycle, compare the shell's 1100 with the `CivilianSedan`'s and sort it into one of three states:

| State | What it is | Fix |
|---|---|---|
| Populated | The 1100 has geometry of its own | None |
| Proxies only | The 1100 exists but holds only proxies | The merge above |
| Absent | There is no 1100 | Create it; the merge does not apply |

## Creating a missing View Pilot

This is checked offline only; confirm it in game before trusting it.

- Create the 1100 only in the assembler that builds the model, or in a fix that runs again after texturing and changes nothing on a second run. A copy made before texturing can keep `texture=(none)` and drift from later visual edits.
- Use a complete visual LOD only as the seed, chosen by the curated View Pilot rules in `view-pilot-and-first-person.md`: keep the structural faces, judge the whole assembled first-person scene, and keep material ownership. Do not choose it by a fixed face normal limit.
- Copy geometry with remapped indices; keep proxy triangles and frames exactly; keep named selections, sharp edges and LOD properties. Never rebuild existing proxies with a constructor that changes their frame.
- Stop before writing anything if an 1100 already exists. Before saving, check the seed against its source, all expected proxies and selections, and the curated content. After saving, read the model back, prove every other LOD unchanged, and run the fix a second time to show it changes nothing. The last check is still an in-game first-person cycle.

## Count what the seated view holds before testing from the seat

A View Pilot (resolution 1100 or 1200) is not a decimation of LOD 0; it is assembled by hand, and what its builder left out is simply not there. Two quad bike mods from the same source tree gave opposite results:

| | Quad A | Quad B |
|---|---|---|
| Body | 25,234 faces (LOD 0: 76,044) | 2,294 faces (LOD 0: 9,011) |
| Dashboard | Complete: `light_dashboard` 744 faces, as in LOD 0 | `light_dashboard` 0 faces (LOD 0: 12) |
| Attachment proxies | 0 of 7 (only the interior and the two crew proxies) | 3 of 17 |

So checks run from the seat can mislead both ways:

- A false pass: "with empty slots no proxy is seen" passes from the seat whether fixed or not, because the attachment proxies are not in the view. Check it from outside, in third person.
- A false fail: "sit down and check the dashboard lights up" always fails on a model whose `light_dashboard` never reached the view, however correct the material and script.

Count against LOD 0, not in absolute terms. Zero faces in the 1100 does not tell "the view dropped it" from "it never existed"; only the pair does. On one quad, four of nine light selections had zero faces in every LOD, a defect of the source model, not of the view.

```python
for L in sorted(p3d.lods, key=lambda l: getattr(l, "resolution", 0)):
    if getattr(L, "resolution", 0) not in (1.0, 1100.0, 1200.0):
        continue
    # for each class the test needs: lights, proxies, gauge textures
    lights = {n: len(s.faces) for n, s in L.selections.items() if n.startswith("light_")}
    prox = [n for n in L.selections if n.lower().startswith("proxy:")]
```

Sort each selection into one of three groups: present from the seat (faces in LOD 0 and in the 1100), dropped by the view (faces in LOD 0, none in the 1100), or a source defect (no faces in LOD 0). Ask what kind of thing is missing, not whether the whole LOD is present, because two views from the same source can miss different things.

The only vanilla file on `P:\` this file relies on is the control car, `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d`, loaded by `CivilianSedan` (`P:\DZ\vehicles\wheeled\config.cpp:5118`); its counts here come from an unbinarized copy read with py3d.
