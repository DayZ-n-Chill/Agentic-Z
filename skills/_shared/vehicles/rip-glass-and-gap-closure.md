# Rip glass bands and gap closure

How to close the see-through gap between a ripped car's glass and its body without greying the windows, how to transfer materials when authored LODs carry foreign geometry, where a rally lift belongs, and how to apply a structural fix without losing a working get-in.

Measured offline, with ray checks, and in game on a car built from a rip (`rip-import.md`); none of it is vanilla behaviour. Winding rules are in `visual-gates-and-winding.md`. Facts read from the vanilla sedan come from a converted copy of `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d` (**model knowledge**).

## Changing a face's role needs an orientation decision

When a rule changes what a face is for, its inherited winding is wrong for the new role. Inner pane glass faces retyped as a black band to be seen from outside kept the pane's cabin-facing winding and were culled from outside: rays reached the ground through the car (529 of 4431 through the rear slot, 70 of 4893 through the cowl) while no ray lacked geometry. Pair every retype with a choice: flip, or double (an antiparallel twin with the same per-vertex UVs, so reversed per-corner UV rows) when both sides are seen. Add twins after the majority repair of the orientation rule; before it they make every band edge non-manifold and break the flood fill. Check offline first with an orientation count and an occlusion ray test, using a pair-aware count, since a nearest-match count always picks the original of a coincident pair.

Doubling the whole band is a fault of its own. The inner pane sits 0 to 1 mm behind the outer glass, so a 15 cm black band visible from outside paints over the window: 68 to 100% of every window view went black in game, while the occlusion check passed because it measures coverage, not appearance. Double only the faces that carry load: cast rays (a ring, a grid over each pane's box and oblique rays at 60 and 30 degrees from the pane's outward direction) and twin the first double-sided hit of any ray that would otherwise end below the floor. On one car that was 129 of 463 band faces (63 on the windscreen, 66 at the rear, none on the sides). The check's rays must be a subset of the probe's rays, and an appearance check (which band faces show first through each pane) must run next to the occlusion check: coverage and appearance limit each other.

## Close the gap with new geometry

When load-bearing twins run out, close the gap between glass and body with authored opaque geometry in the gap itself. Any band face visible from outside draws in front of the glass, the grey window fault; on that car the band overlapped all six panes completely. Keep new geometry at least about 8 mm from any transparent glass so it can never grey a window:

- A skirt lofted from the outer pane's boundary ring to the nearest opaque body edge. Walk the boundary edge loops for continuity, not points sorted by angle, and overshoot the body by about 15% plus 1 cm so the tip tucks into the body with no crack.
- A sunken band for the cowl and rear slots seen from above: copy the inner pane frit faces about 10 cm down, like the plenum or dash top a real car has there.

Double these: a one-sided strip is culled from one half of the views (wound inward it shows from the side but is culled from above, because the glasshouse centre sits above the rear deck). Doubling is safe here because the strip stays clear of the glass. Check from above (no see-through), with a sideways first-hit count, and relative to the last deployed build, since absolute side counts include harmless existing rim cracks. A side wedge under the mirror, looking through the glass edge into a deep cabin, needs a targeted twin at the glass that risks greying; judge it by eye in game.

A gap seen only from the seat closes the other way: one sided, in the View Pilot LOD only, behind whatever passes through the rider's line of sight (`view-pilot-closures.md`).

## Material transfer and foreign geometry

An authored LOD can carry geometry from another part: one badge's LOD 2 held fascia trim, its extent 8.4 times the full part's bounding diagonal, with 175 of 183 faces more than 25 mm from any donor face in the same part. A per-part nearest transfer can only offer the badge's own type (chrome) and paints the trim grey.

Scan every part for a LOD extent more than 1.5 times its full detail extent and warn. For those parts only, let faces whose nearest donor in the part is more than 25 mm away re-vote against all parts' full detail faces, where the overlapping neighbour types them right. Do not re-vote everywhere: decimation alone moves centroids past 25 mm, and the global pool then votes in brighter neighbours (a diffuser shipped 8 black faces as metal and chrome, donors 23 to 46 mm away). Report far-donor counts either way.

A numpy fixed-width string array truncates silently: assigning `'PLASTIC'` into a `<U6` array stores `'PLASTI'`, an unknown type that falls back to the default colour. Promote the array to the pool's dtype before assigning across parts.

## A rally lift belongs to the body

A stance lift raises the body (`Y0`), not the wheel hubs. A builder that placed hubs at `WHEEL_R + LIFT` buried each hub 18 cm above the knuckle, cancelled the visible stance and cut chassis clearance to 7.6 cm (the sedan has 25.8 cm), a likely "won't drive off-road". Give the profile a separate `hub_lift`, 0 by default, so hubs sit at the rim contact (`WHEEL_R`), the wheel meets the knuckle and the body lift becomes real stance. `config.cpp` and `model.cfg` need no change: they reference names, and the `*_axis` points ride the hub. Check that the four wheel anchors equal `WHEEL_R` in every structural LOD, the knuckle to hub gap is at most 2 cm and chassis clearance is at least 0.20 m. Measured offline.

## Patch the deployed structure, do not regenerate it

A deployed structural model can hold get-in work that the builder does not reproduce. On one car the deployed View Geometry had a 23-component hull, the `crewdriver` and `crewcodriver` bone selections that `proxyPos` needs, and wheel proxies added after the build, while the builder produced a 3-component View Geometry with no crew selections. A full transplant would have undone a get-in that took many game tests.

Before a structural transplant, compare the fresh build with the deployed one LOD by LOD. If the get-in selections differ, apply the geometric fix (hub height, crew position, `#Mass#`) as a scripted patch of the deployed model that moves only the wheel, crew and mass selections by identity, checks per point that nothing else moved and that the crew selections survive, keeps a backup and reads the file back. Test the patch on a copy, never on the live file. Folding the hull and crew selections into the builder is separate work.
