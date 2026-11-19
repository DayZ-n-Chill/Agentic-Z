# Open rims on ripped panels

Why a door, hood or tailgate taken from a game rip shows a see-through edge when it opens, which fixes do not close it, and how to check a real cap.

Everything here was measured offline and in game on a test car built from a rip. `doors-and-panel-edges.md` covers measuring a missing door edge and hoods against doors; its section "Close the edge by script" does not fix the rim in game, so close it as this file describes.

## A ripped panel is two skins with an open rim

Any door, hood, tailgate or flap from a game rip is an outer skin and an inner card that never meet at the edge. The source game never shows that edge, so it was never modelled; every DayZ door opens, so every imported door shows it. The vanilla sedan door (`P:\DZ\vehicles\wheeled\civiliansedan\proxy\sedandoors_driver.p3d`) is a closed volume: on a debinarized copy its free edge length is 0 (**model knowledge**; the file on `P:\` is binarized and py3d cannot read it).

Count a free edge over all faces of the LOD, not within one material. An edge the skin shares with glass or trim is covered, not open; counting within a material inflates the count and aims the fix at edges that were never exposed.

## What does not close it

- An extruded skirt. Welding a band to the rim closes that edge and opens a new one at the band's inner boundary. On the test door the true free edge went from 4455 mm to 5036 mm: the hole moved inward.
- The extruded vertices also copy the rim vertex's UV, so every new quad has 3D area and zero UV area: 235 of 235 quads at 0.00000 UV per 3D area, against 0.18 for the skin beside them. The faces draw, so a solid colour render scores them as closed, while the game samples a collapsed mapping and the player sees smeared texture. Near glass the skirt shows as a mark on the glass: 39 quads lay within 5 cm of a pane, the closest at 6.1 mm.
- Re-importing. All six visual groups of the door were already present face for face in the shipped proxy (every face centroid matched within 1 mm), and rebuilding the door from the rip gives 684 mm of free leading edge against the live door's 743 mm and the sedan's 0. The open sandwich is in the source, and rebuilding reproduces it.

## How to cap it

Author the rim as a cap on the vertical leading and trailing edges only. Weld skin edge to card edge with its own UV strip, or give it its own opaque edge material. Do not sweep the whole free perimeter: most of it is never exposed. On the test car only 31.5% of an automatic perimeter skirt landed on the two edges the complaint was about, while 17.4% (663 cm²) landed on the window top and became a new texture fault.

## Checking the fix

Check with a textured render and an in-game capture with the panel open, at the angle of the complaint. A silhouette percentage and a solid colour render both miss the UV fault that decides whether the fix shows at all.

A number that improves while the symptom stays is measuring the fix, not the fault. On the test door "56 of 63 quads face the edge", "cap area from 25 to 40 cm²" and "edge-on silhouette from 15.0% to 25.4% against 26.8% for vanilla" all improved while the rim stayed see-through. Go back to the view the complaint came from.

When three visible improvements each make a metric worse (here 5.2 mm, then 3.4 mm, then 0.5 mm toward negative), the reference is wrong, not the threshold. Check what it measures against: the outer rail must sit on the sheet edge, while the inner rail rightly rises to the glass, so judging the inner rail against the sheet asks it not to do its job.

Before writing a fix for a panel, Grep this pack for the fault itself, not only for the car's name; `doors-and-panel-edges.md` already measured the same rim.
