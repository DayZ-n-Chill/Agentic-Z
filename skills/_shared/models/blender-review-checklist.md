# What to look for in a render

Which faults to look for when you review a Blender model's renders: general 3D faults, a comparison with a vanilla model, a comparison with a reference image, and scoring likeness to a photo. The capture and the review loop are in `blender-visual-review.md`; winding, which a render cannot judge, is in `blender-winding-flips.md`. It is a review method measured in Blender, not a fact about the game.

Walk every section, every time. The point of a checklist is to catch the fault you were not already worried about, so each item is a signal you can check against a number or a specific thing on screen.

## Every model

- **Orientation.** Does forward point where it should? Is anything upside down or mirrored? Read it against the scale cube and the world axes, not from memory.
- **Proportion and scale.** Measure against the 1 m cube and `result["dims"]`. "Looks small" is a reason to check the number, not a finding.
- **Inverted or black normals.** With the Face Orientation overlay, any red facing the camera is a back face you are looking through. Also watch for surfaces lit as if from inside.
- **Shading faults.** Black facets, pinching, smooth shading bleeding over a hard edge, ngons on curved areas.
- **Exploded or floating parts.** Gaps between parts that should touch, a part hovering off its mount. `verify_overlap` (`blender-assembly-checks.md`) catches the ones you can measure; the eye catches the rest.
- **Doubled geometry.** A shimmer that changes between angles means two faces in the same place.
- **Materials in Workbench.** `color_type = 'TEXTURE'` paints one image of the material, not its shading: on a vanilla rock the `rock_*_mask` input rendered as flat mask colours and looked like a fault. Judge materials in EEVEE with the file's own lights.

## Animated parts

Presentation renders show only posed frames, and collisions hide behind walls or closed doors. Check clearance at every keyframe, not per render: evaluate the depsgraph mesh at each keyframe and at points between them along each travel, and run `BVHTree.overlap` between each moving mesh and each fixed mesh, a sweep of fixed points (vertices, face centres, edge centres) that fall inside the part's footprint at rest and along its travel, and section cuts on the travel planes. A flush contact also reports as overlap; tell it from a real collision by how deep the geometry enters the footprint, not by how many triangles cross.

Measured on an animated rock platform: nine presentation cameras showed nothing, while the sweep found a 12 by 14.6 m platform crossing a lip 0.27 m into its footprint, and a lift cabin crossing the top threshold by 0.14 m on every ride, visible only from inside the cabin at one frame.

## Against a vanilla model

Import a known good vanilla model into the same scene at 1:1 and compare side by side. Vanilla models on `P:\` are binarized, so opening one in Blender needs an outside ODOL to MLOD converter, which this repo does not ship.

- **Orientation and scale.** The same forward axis and about the same footprint as the vanilla equivalent.
- **Ride height.** A ground item's lowest vertex (`result["lowest_z"]`) sits at about z 0. A vehicle's wheels touch about ground level and its belly clears it well; a vanilla sedan's belly clearance measured about 0.43 m on its binarized model, not checked against any other vanilla file. A wheel that is too small sinks the body. Measure it; do not judge "looks grounded". The vehicle layout is in `_shared/vehicles/`.
- **Proxies and slots.** Wheels, the Fire Geometry bulk and lights sit where the vanilla model has them.

## Against a reference image

Load the reference as a camera background (`cam_data.show_background_images = True`, then `cam_data.background_images.new().image = bpy.data.images.load(path)`), match the camera to the reference angle, render, and compare named landmarks (roofline, wheel arch, handle position), not the overall impression. Report outline differences, missing or extra masses and proportion drift by pointing at specific places.

## Scoring likeness to a photo

- **One calibrated camera per photo.** Fit each Blender camera by silhouette IoU: maximise the IoU between the Workbench alpha silhouette and the photo mask (Nelder-Mead over position, yaw, pitch, roll and focal length, started from a part of known size such as the tyres from the spec sheet). Judge only photo and render crops from that same camera. With a camera set by eye, a wing out of place or a dome floating 5 cm stays invisible.
- **Poor or partial photos.** Low resolution or off angle photos fit a false camera (IoU 0.81 on a brochure front view). Solve PnP on 6 to 8 points triangulated from other photos instead, and reject any refinement that lowers the IoU: a bundle with 2 anchors moved one camera 38 cm along the view rays and dropped the IoU from 0.936 to 0.923.
- **Silhouette renders.** Set `render.use_compositing = False`; an Alpha Over node makes the whole silhouette opaque when `film_transparent` is on.
- **Judge blind, with another model family.** Measured in Blender 5.1 against studio photos: a model's scores of its own work ran 1 to 2 checklist points above a blind review by a different model family over the same 27 image sets. Use, per criterion, the lower of the two scores.
