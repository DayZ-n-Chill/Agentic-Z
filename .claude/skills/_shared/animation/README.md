# Animation pack

Reference for `dayz-animation-specialist`: moving parts in `model.cfg`, the config entries that feed them, the script that plays them, RTM files and the Blender handoff. Open only the file the task needs.

Vanilla ships `model.cfg` only inside the packed `.p3d` files, so there is no vanilla `model.cfg` text on `P:\` to copy from. The names and values these files quote from vanilla models are the ones stored in the shipped `.p3d` files under `P:\DZ\`; the `model.cfg` key names come from the Binarize input format and are marked as such where they appear.

| Question | Open |
|---|---|
| How do I write the skeleton bones and the `Animations` block? Which keys, units and names? | `model-cfg-animations.md` |
| What goes in `config.cpp` so an animation can be driven: `AnimationSources`, building `Doors`? | `animation-sources.md` |
| Which script call plays the animation, on which side, and how do clients see it? | `script-hooks.md` |
| Where does DayZ use `.rtm` files, and how is that different from character animation? | `rtm-and-character-animation.md` |
| What must the user keep straight when the model comes from Blender? | `blender-handoff.md` |

## Worked vanilla examples

These three vanilla objects cover the common cases. Every file in the pack refers back to them.

| Case | Config | Script | Model |
|---|---|---|---|
| Building door, no mod script | `P:\DZ\structures\residential\config.cpp:7341` (`Land_HouseBlock_3F_Corner1`, `class Doors` at :7357) | `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actionopendoors.c:1` | `P:\DZ\structures\Residential\HouseBlocks\houseblock_3f_corner1.p3d` |
| Item lid that hides and shows | `P:\DZ\gear\containers\config.cpp:99` (`Barrel_ColorBase` `AnimationSources`) | `P:\scripts\4_world\entities\itembase\barrel_colorbase.c:144` | `P:\DZ\gear\containers\55galDrum.p3d` |
| Gate that rotates with a custom range | `P:\DZ\gear\camping\config.cpp:4418` (`Fence` `AnimationSources`) | `P:\scripts\4_world\entities\itembase\basebuildingbase\fence.c:488` | `P:\DZ\gear\camping\fence.p3d` |
