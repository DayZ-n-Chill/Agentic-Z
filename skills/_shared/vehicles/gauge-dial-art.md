# Gauge dial art

How to measure the printed arc of a dial, why each dial gets its own padded texture, what limits legibility on screen, and how stale textures slip into a build.

The frame and the angle formula are in `gauge-dial-frame.md`. Everything here was measured on mod test vehicles and is not checked on `P:\`.

## Propose the scale and check it by drawing

Detecting the printed arc automatically failed four ways on clean black art with no noise:

1. Ring centroid: the centroid of a partial arc is not the circle's centre, so iterating centre, ring, centre diverges. The centre ended in a corner with a radius larger than the image.
2. Largest angular gap: discrete ticks always leave gaps, so "largest" picks any of them. The centre label (`km/h`, `RPM x1000`) fills the lower sectors and splits the real gap, and red redline ticks vanish in greyscale and invent a gap.
3. Label blobs: the centroid of `150` does not sit at the same radius or with the same bias as that of `0`; a line fit left 8 degrees of residual.
4. Major ticks by depth: the count was wrong (15 of 16, 9 of 7) and steps ran 16 to 23 degrees on a regular scale.

What works is cheap: propose a scale and draw a needle over each printed value; the image shows whether it is right. On the speedometer all 16 needles landed on their numbers first time; on the tachometer the first guess failed, was corrected with the two lone ticks beside the gap, and 0 and 6 landed on the second try. Write the value to tick pairs down and re-measure them with a tolerance (0.5 degrees) so a moved tick fails the check instead of quietly producing other angles.

The final check depends on no convention: rasterize the real UVs of the built `.p3d` onto the texture, sampling V the same way the model's other UVs do, and draw the needle over every printed value, not just the ends. A line fitted to two endpoints passes through both by construction. A synthetic render on an invented disc carries none of the UVs the model wrote and proves nothing.

Mind entry and exit ticks beyond the last label: on one tachometer the ticks cover 299 degrees and the printed scale 240.

## Reading ticks

- Judge ink by the largest colour channel, not luminance. A red tick (255, 0, 0) is 76 in greyscale, so an ink threshold of 110 drops the whole redline band and the last major tick with it. The empty end of a fuel gauge is usually a red mark, so luminance measures an arc that falls short exactly at the end that sets `angle0`.
- Measure how far ink reaches in from the rim, and stop early: a gap tolerance of about 2 samples and a scan depth of about 0.16 of the radius. With a looser tolerance the scan jumps from a tick to the number beside it. On one dial minor ticks reach 0.07 to 0.11 of the radius and majors 0.15 or more; a major cut at 0.13 separates them. Settings that worked: ink 110 on the largest channel, 160 samples at 0.001 of the radius, stop after more than 2 empty samples.
- Do not accept a ring because it returns as many groups as there are major ticks. One ring returned exactly 16 groups spread over 62 degrees on a dial that sweeps 290.
- Use the scale's own regularity as a check. If detected ticks are not evenly spaced within a narrow margin, the detection is wrong and its number is not used. On the speedometer ring detection gave 46 clusters with steps of 1.5 to 15.8 degrees and was discarded; the three large ticks still fixed the circle, and from that centre the ten fuel ticks came out 9.0 to 9.4 degrees apart, which passed.

A needle turns linearly, so a printed scale squeezed at one end cannot match everywhere. Fit the line to the regular part the vehicle actually uses (0 to 100 km/h on a quad, 1.53 degrees residual over 11 major ticks) and let the error fall where the vehicle never goes. The fuel E and F angles (130.0 and 48.5) come from the arc fit checked by drawing; the depth centroid of those long marks lies 8 degrees off.

## One texture per dial

Dials placed as islands in the body atlas cost two things. Resolution: digits are 2.8 to 4.5 percent of the dial's diameter, so a 12 px digit needs a 270 to 430 px island, and on 80 px islands a digit is 2 to 4 px. And the window: an island means measuring centre and radius inside the atlas, which is the measurement that fails. One texture per dial gives full resolution and a UV window of exactly 0 to 1 with nothing to crop.

The real limit is the screen. On one quad the complaint "pixelated texture" was not the texture: the dial covered 110 px of a 1920 px screen while the texture supplied 501 (4.6 texels per pixel), so a digit at 3 percent of the diameter was 3.3 px. Shrinking the art to 110 px offline reproduced the in-game look exactly, so neither DXT1 nor mipmaps were at fault. A bigger texture fixes nothing; a bigger dial does (radius 0.027 to 0.038 m, about 150 px on screen, made the numbers legible), or fewer, larger numbers. From the seat a dial typically covers about 90 px of 1920.

## Pad, never stretch

A texture must be a power of two. A 1536 by 1024 fuel panel stretched to 2048 by 1024 (1.333 in x only) turns the tick arc, a circle in the art, into an ellipse: the fitted circle misses the marks, the pivot sits at a false centre and the needle passes over E and F without touching them. Pad the sides with black instead (the art background is usually black anyway); the arc stays a circle and positions convert directly: `u_2048 = (pad + x_art) / 2048`.

An angle does not survive a mapping that scales the two axes differently. Before using an angle measured on the texture as a screen angle, check in the 2 by 2 fit that `|dU/dright|` and `|dV/dup|` are equal. If not, transform the angle, or express the radius in the same units on both axes.

That stretch can be absorbed in the art, which is usually cheaper. If a face already has a good UV window (exactly 0 to 1, not mirrored, negative determinant) and the only problem is unequal scale, draw the art pre-squeezed by the inverse factor. A coupe's panel measures 264.78 by 105.61 mm (2.5072:1) against a 2:1 texture, so the art was drawn squeezed horizontally by 0.797711; the face then measured 1.0000, 1.0053 and 0.9947 for isotropy, without touching the UVs of a 20 MB model you do not own. This works only when the unequal scale is constant across the face (fit residual near zero, 5e-07 there); if it varies, remap the UVs.

## Stale textures

A converter that skipped any `.paa` already on disk, without checking date or content, kept packing old dial faces: the packed faces predated the art, so a tachometer fix and a speedometer revert never reached the game and every in-game look checked the old texture. Store a SHA-256 of the source PNG next to each PAA (`<paa>.src.sha256`) and convert again when it changes. That cache did not cause the mirror, though for a while it looked like it: two real defects can sit on one path, and the first one found need not explain the symptom.

Stamp files and backups inside the mod tree end up in the PBO if packing copies the whole tree: 95.7 MB instead of 21.8, with "Build Successful". Exclude them when packing and check the PBO size.
