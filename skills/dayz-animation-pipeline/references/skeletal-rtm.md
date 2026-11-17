# Skeletal animation through `.rtm` (legacy clips)

`.rtm` is the animation format of the older Real Virtuality engine. In DayZ it is the legacy route: it is not how characters, infected, animals with graphs or weapons are animated (that is `.anm`, see `skeletal-anm-enfusion.md`). Where vanilla still references `.rtm` files is listed in `skills/_shared/animation/rtm-and-character-animation.md`: face poses such as `RTM_Face` (`P:\DZ\characters\heads\config.cpp:4682`), lip sync shapes, and simple animals such as the butterfly.

Nothing below about the format and the tools can be checked on `P:\`, which holds no `.rtm` files under `P:\DZ`.

## The format is reverse engineered

Bohemia does not document `.rtm`; the structures are internal. Treat every description of the format as reverse engineering, not a contract: it can differ between engine versions.

## Shape of the file

- **Plain (`RTM_0101`).** An optional `RTM_MDAT` header (frame properties as name and value at float phases), then `RTM_0101`: a motion vector of three floats, the frame count, the bone count, bone names of a fixed 32 bytes each, and for every frame one transform per bone as a 4 by 3 float matrix. Byte offsets were not checked against a vanilla file.
- **Binarized.** A separate compact format, versions 3, 4 and 5 (Arma 2 and Arma 3). Its layout is not known here; only its existence is.

## What can write an `.rtm`

- The package in `scripts/tools/dayz-animation-formats/` reads and writes one unbinarized `RTM_0101` block with an optional `RTM_MDAT` before it (`read_rtm`, `write_rtm`), and refuses anything else. Its output was read back by Arma 3 Object Builder 2.5.1 with motion, phases, metadata and transforms preserved. That is a file check, not proof the game accepts the clip.
- Nothing here writes binarized `.rtm`.
- Do not promise that a hand written `.rtm` plays in game until it has been through the user's converter and an in-game test.
- Reading `.rtm` in Python is well trodden: the `rtm_import` Blender addon parses it (import only).

For authoring, prefer Blender or `FBXToRTMGui.exe` over writing matrices by hand.

## The pipeline (the user's tools)

```
Blender (keyframes against the target skeleton)
  -> .rtm directly        Arma 3 Object Builder export        or
  -> FBX -> .rtm          FBXToRTMGui.exe, in DayZ Tools
       -> referenced from config -> pack -> sign -> test in game
```

- **Arma 3 Object Builder** (a Blender 4.2+ addon) exports `.rtm` from a timeline range. The phase runs from 0.0 to 1.0 across the render range, so a wrong range squashes or clips the animation. The only frame property known is `StepSound`. It carries Arma's name, but the format is the same one.
- **`FBXToRTMGui.exe`** (DayZ Tools): set the bind pose FBX and the `modelbox.xml`, pick the skeleton (`ManSkeleton`), the root bone (`Hips`), and a frame rate equal to the source's. Not tried on the current DayZ Tools.

## Traps

- Bone names must match the target skeleton exactly, the same rule as on the `.anm` route.
- The frame rate must be the same in the source file and in the converter, or the clip's speed drifts.
- Scale between Blender meters and the engine's space: the factor for DayZ was not established.
- MotionBuilder: FBX to RTM is documented as working with MotionBuilder 2009 and broken with 2015. Newer versions were not checked.
- DayZATool is the `.anm` tool. Do not use it for `.rtm` round trips; its extracted rigs are unreliable.

## When to use `.rtm` and when `.anm`

- `.rtm`: a face pose or a simple animal state in the shape vanilla uses, or a legacy clip. A prop that only turns or slides does not need a clip at all; that is a `model.cfg` animation (`config-driven-animation.md`).
- `.anm`: anything on a character, infected, graph driven animal or weapon. Never use `.rtm` for a player weapon animation; it is the most common wrong turn.

## The tools by name

- Arma 3 Object Builder: the Blender addon that imports and exports `.rtm`; its documentation lists the `.rtm` properties.
- ArmAToolbox: an older Blender `.rtm` export.
- `rtm_import`: a Blender addon that reads `.rtm` (import only).
- FBX to RTM: `FBXToRTMGui.exe` in DayZ Tools, documented on the Bohemia Interactive community wiki.
