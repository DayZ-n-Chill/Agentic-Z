#!/usr/bin/env python3
"""
gen_model_cfg.py - write a DayZ model.cfg (CfgSkeletons + CfgModels + class
Animations) from one small description, so the animation names stay the same
across model.cfg, config.cpp and script. A mistyped name fails with no error in
game, which is the most common reason a config driven animation does nothing.

Layer 1 (config driven animation), pure text. The output goes in the mod's
folder next to the .p3d. This generator does not touch the .p3d, .rtm or .anm
files; it only writes the config that binds named selections to animations.

The property names it writes are the ones in
references/config-driven-animation.md. It warns on an animation type outside
its checked set (for example translationModelX or direct): check such a type
against a vanilla model.cfg first and add it by hand.

Description format (JSON):
{
  "model": "MyObject",                 # must equal the .p3d file name (MyObject.p3d)
  "skeleton": "MyObjectSkeleton",
  "skeletonInherit": "",               # parent skeleton or ""
  "bones": [                           # (bone, parent) pairs; parent "" = root
      ["door", ""],
      ["door_handle", "door"]
  ],
  "animations": [
    {
      "name": "Door1",                 # the class name; keep it equal to the AnimationSources class and the SetAnimationPhase argument
      "type": "rotation",              # rotation[/X/Y/Z], translation[/X/Y/Z], hide
      "source": "Door1",               # a "user" source is declared in config.cpp AnimationSources
      "selection": "door",             # named selection in the .p3d (must be a bone above)
      "axis": "door_axis",             # axis selection (2 memory points); leave out for hide
      "minValue": 0, "maxValue": 1,
      "angle0": 0, "angle1": "rad 90"  # rotation; offset0/offset1 for translation; hideValue for hide
    }
  ]
}

Usage:
  python gen_model_cfg.py spec.json > model.cfg
  python gen_model_cfg.py --self-test
"""
import json
import sys

# Animation types this generator writes without a warning. A hide animation
# hides its selection once the phase reaches hideValue (phase 1 hides, 0 shows).
VERIFIED_TYPES = {
    "rotation", "rotationX", "rotationY", "rotationZ",
    "translation", "translationX", "translationY", "translationZ",
    "hide",
}

# Keys written in a fixed order. Any other key is passed through as it is (so a
# checked property can be added without editing this file), with a warning on
# stderr so an invented key does not slip in unseen.
KNOWN_ANIM_KEYS = [
    "type", "source", "selection", "axis", "begin", "end", "memory",
    "minValue", "maxValue", "minPhase", "maxPhase", "sourceAddress",
    "animPeriod", "angle0", "angle1", "offset0", "offset1", "hideValue",
]


def _fmt_value(v):
    """Render a value the way model.cfg expects: strings such as 'rad 90' or
    'clamp' are quoted, numbers stay bare, strings already quoted stay as they are."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    s = str(v)
    # already quoted
    if s.startswith('"') and s.endswith('"'):
        return s
    # looks like a number: leave bare
    try:
        float(s)
        return s
    except ValueError:
        return f'"{s}"'


def _emit_animation(a):
    name = a["name"]
    t = a.get("type")
    if t not in VERIFIED_TYPES:
        sys.stderr.write(
            f"WARNING: animation '{name}' type '{t}' is not in the checked set "
            f"{sorted(VERIFIED_TYPES)}. Check it against a vanilla model.cfg before shipping.\n"
        )
    lines = [f"            class {name}", "            {"]
    emitted = set()
    for k in KNOWN_ANIM_KEYS:
        if k in a:
            lines.append(f"                {k}={_fmt_value(a[k])};")
            emitted.add(k)
    # pass any other key through as it is, with a warning
    for k, v in a.items():
        if k in ("name",) or k in emitted:
            continue
        sys.stderr.write(
            f"WARNING: animation '{name}' has unrecognized key '{k}'. Passing it "
            f"through as it is - confirm it is a real model.cfg property.\n"
        )
        lines.append(f"                {k}={_fmt_value(v)};")
    lines.append("            };")
    return "\n".join(lines)


def generate(spec):
    model = spec["model"]
    skel = spec.get("skeleton", model + "Skeleton")
    inherit = spec.get("skeletonInherit", "")
    bones = spec.get("bones", [])
    anims = spec.get("animations", [])

    # every animation selection must be a declared bone
    bone_names = {b[0] for b in bones}
    for a in anims:
        sel = a.get("selection")
        if sel and sel not in bone_names:
            sys.stderr.write(
                f"WARNING: animation '{a.get('name')}' selection '{sel}' is not in "
                f"skeletonBones[] - the engine will log a bone error and skip it.\n"
            )

    out = []
    out.append("class CfgSkeletons")
    out.append("{")
    out.append(f"    class {skel}")
    out.append("    {")
    out.append(f'        isDiscrete=1;')
    out.append(f'        skeletonInherit="{inherit}";')
    bone_pairs = []
    for b in bones:
        bone_pairs.append(f'"{b[0]}","{b[1]}"')
    out.append("        skeletonBones[]=")
    out.append("        {")
    out.append("            " + (",\n            ".join(bone_pairs) if bone_pairs else ""))
    out.append("        };")
    out.append("    };")
    out.append("};")
    out.append("")
    out.append("class CfgModels")
    out.append("{")
    out.append(f"    class {model}")
    out.append("    {")
    out.append(f'        skeletonName="{skel}";')
    out.append('        sectionsInherit="";')
    out.append("        sections[]={};")
    out.append("        class Animations")
    out.append("        {")
    out.append("\n".join(_emit_animation(a) for a in anims) if anims else "")
    out.append("        };")
    out.append("    };")
    out.append("};")
    return "\n".join(out) + "\n"


def _self_test():
    spec = {
        "model": "MyObject",
        "skeleton": "MyObjectSkeleton",
        "skeletonInherit": "",
        "bones": [["door", ""], ["door_handle", "door"], ["barrel_1", ""]],
        "animations": [
            {"name": "Door1", "type": "rotation", "source": "Door1",
             "selection": "door", "axis": "door_axis",
             "minValue": 0, "maxValue": 1, "angle0": 0, "angle1": "rad 90"},
            {"name": "hide_barrel1", "type": "hide", "source": "hide_barrel1",
             "selection": "barrel_1", "minValue": 0, "maxValue": 1, "hideValue": 0.5},
        ],
    }
    out = generate(spec)
    assert "class CfgSkeletons" in out
    assert 'skeletonName="MyObjectSkeleton";' in out
    assert "class Door1" in out and 'angle1="rad 90";' in out
    assert "class hide_barrel1" in out and "hideValue=0.5;" in out
    assert '"door",""' in out and '"door_handle","door"' in out
    print(out)
    sys.stderr.write("\nself-test OK\n")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        _self_test()
    elif len(sys.argv) == 2:
        with open(sys.argv[1], encoding="utf-8") as f:
            spec = json.load(f)
        sys.stdout.write(generate(spec))
    else:
        sys.stderr.write(__doc__)
        sys.exit(1)
