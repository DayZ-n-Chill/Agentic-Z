# Gauge fuel panel

How to add a fuel gauge panel to a model: padding the art, choosing a UV window that matches the face, where the pivot falls, sizing the needle, and which angles carry over from one model to another.

The wiring is in `gauge-needles.md`, the frame in `gauge-dial-frame.md` and the padding rule in `gauge-dial-art.md`. The numbers come from one fuel panel artwork mounted on two test quads; they are not checked on `P:\`.

## The art

The fuel art is 1536 by 1024 px, not a power of two. Pad it to 2048 by 1024 with black, centred (256 px each side); never stretch it, or the arc becomes an ellipse.

The arc's centre and radius come from a circle fitted to the ticks from E to F and checked by drawing over them, not from the face's bounding box. Empty (E) is the red mark at 130.0 degrees, full (F) the last tick at 48.5 degrees, so the sweep from E to F is 81.5 degrees, clockwise.

| Value | In the padded texture | In the art alone |
|---|---|---|
| Centre, across | (256 + 940) / 2048 = 0.58398 of width | 940 / 1536 = 0.6120 of width |
| Centre, down from the top | 968.7 / 1024 = 0.94600 | 0.9460 |
| Radius | 634.7 / 2048 = 0.30991 of width | 634.7 / 1536 = 0.4132 of width |

The pivot sits 5.4 percent above the bottom edge, so the arc is very open.

## Pick a window that matches the face

Map V as row divided by height, without `1 -`, with u the driver's right and w up in the anchored frame. Choose the window by the face's aspect ratio:

| Face | Window | Centre and radius to use |
|---|---|---|
| 2:1, the padded texture's shape | U 0 to 1, V 0 to 1; the black bands (12.5 percent per side) stay on the face | The padded texture's (0.58398, 0.94600, 0.30991) |
| 1.5:1, the art's shape | U 0.125 to 0.875, V 0 to 1; no bands | The art's (0.6120, 0.9460, 0.4132) |
| 1.98:1, the drawing inside the art | U 0.1489 to 0.8506 (305 / 2048 to 1742 / 2048), V 0.1455 to 0.8545 (149 / 1024 to 875 / 1024); corner to corner, no overflow | Of the drawing box: centre 0.6200 of width, radius 0.4417 of width |

The art carries its own black border; the drawing box is x 305 to 1742, y 149 to 875 (1437 by 726 px). The third row reaches the same arc by a different route (0.6200 times 1437 plus 305 gives 1196 px in the texture, which is 940 px in the art; 0.4417 times 1437 gives 634.7 px), which is a useful cross-check.

Do not copy a window that spans the full texture width with the height taken from the face's ratio. On a 1.84:1 face that overflows 44 px top and bottom (V outside 0 to 1) and relies on black art and wrapping; at 1.5:1 it would overflow 170 px and wrap the hub rows onto the top of the face. In general a face of ratio A spans V from 0.5 - 1/A to 0.5 + 1/A.

## Where the pivot falls

With the drawing window (V up to 0.8545) the arc centre (V 0.9460) falls below the face's bottom edge, 3.3 mm on a quad. A needle drawn from the hub would then stick out under the panel, so build a short pointer from 0.55 to 0.96 of the arc radius instead. With the full art window (V up to 1.0) the pivot stays inside and the hub sits flush with the bottom edge.

One quad is enough for the panel. A face that is part of the pod needs no `lift`; a new face over a pod uses whatever `lift` the model's painted discs already use (0.0012 on one quad). A blade 1.89 mm in front of its disc works.

## Pivot, push and needle size

- Pivot: the arc centre, mapped back through the same face mapping, plus a push of 0.0004 m in front of the face along its normal, so it does not z-fight with the face.
- Reach: the radius in metres, the radius fraction times the window width in metres (`FUEL_R_U * 2048 * metres_per_px` for the padded window).
- Needle: the canonical needle (`gauge-needle-part.md`) scaled by reach over tip length. On one quad that was 0.665: a built tip of 0.01220 against a canonical tip of 0.02239, through a scale of 0.82.

Put the new panel geometry and its points in the animated selection with the needle, hanging from the dashboard or handlebar bone (`fuel` from `drivewheel` on a quad), or the panel stays behind when the part turns.

## What carries over to another model

The art's angles (130.0 and 48.5 degrees) and the sweep (81.5) carry over, as long as the window is not stretched or mirrored. The rest angle does not: it is the tip direction of the `fuel` selection measured in the built model in the anchored frame.

- With a rest of 0.90 degrees one quad gets `angle0 = "rad -129.1"`, `angle1 = "rad -47.6"`.
- A canonical needle mounted with its tip along +u has a rest near 0, giving about -130.0 and -48.5.
- A needle built pointing up (rest 90) on another quad gives `"rad -40.0"` and `"rad 41.5"`, sweep +81.5. In game, with the tank full, it pointed at F, turned by +41.5 degrees, which is its `angle1`; the panel showed FUEL, E, 1/2 and F, readable and not mirrored. Its offline check read determinant -231.92, anisotropy 1.0049, residual 5.0e-07.

Never copy another model's angle pair; measure the rest angle on yours.

## Checklist

- The arc drawn over the art passes through the ticks from E to F.
- V is row over height, without `1 -`.
- The frame is anchored to the model's right, and the panel's frame is projected from it with `<u_part, anchored right>` positive.
- You know whether the pivot falls inside the face or below it; below means a short pointer, not a needle from the hub.
- The rest angle is measured on the built model.
- Panel and needle are in the turning selection.
- The determinant is negative in the anchored frame.
