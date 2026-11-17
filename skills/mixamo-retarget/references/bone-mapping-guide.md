# Bone mapping guide

How the automatic bone matching works for animation retargeting, how to review a map, the common naming patterns per rig family, and how to fix bad matches.

This is a guide to a Blender tool, not to the game, so it cites no vanilla file. The guide was written for the full upstream toolkit. Three things it describes are not shipped in this skill: the `blender-toolkit` command line, its TypeScript workflow and its Blender review panel. They are kept below because they explain the intended workflow; each is marked "upstream only". In this skill the same steps run as Python calls through the Blender MCP (see `SKILL.md`). Scores and outputs marked "measured" were produced with the shipped `bone_matching.py`.

## Contents

- [Overview](#overview)
- [Bone mapping modes](#bone-mapping-modes)
- [Auto bone matching algorithm](#auto-bone-matching-algorithm)
- [Two-phase workflow](#two-phase-workflow)
- [Quality assessment](#quality-assessment)
- [Blender review panel (upstream only)](#blender-review-panel-upstream-only)
- [Common mapping patterns](#common-mapping-patterns)
- [Troubleshooting](#troubleshooting)
- [Best practices](#best-practices)

---

## Overview

Bone mapping establishes which bone of the Mixamo animation skeleton corresponds to which bone of your character rig. Accurate bone mapping is essential for a successful retarget.

**Why bone mapping matters:**
- Mixamo uses standardized bone names (for example "mixamorig:Hips", "mixamorig:LeftArm")
- Custom rigs use various naming conventions (for example "Hips", "LeftArm", "left_arm", "arm.L")
- Without a proper map, animations do not transfer correctly
- A wrong map gives twisted limbs, inverted rotations or broken animations

**Core features:**
- **Automatic fuzzy matching**: matches bones by name similarity
- **Review before applying**: the map is reviewed and edited before it is baked
- **Quality assessment**: automatic rating of the map
- **Rigify preset**: a starting map for Rigify rigs
- **Custom maps**: support for non-standard rigs

---

## Bone mapping modes

Three modes are available.

### 1. Auto mode (recommended)

**When to use:** unknown or non-standard rigs.

```python
bm = auto_map_bones("Armature", "Hero")
```

Upstream only:

```bash
blender-toolkit retarget --target "Hero" --file "./Walking.fbx" --mapping auto
```

**How it works:**
1. Reads the bone names of the source (Mixamo) and the target (your character)
2. Uses the fuzzy matching algorithm to find the best matches
3. Builds the map and rates its quality
4. Shows the map for review (the upstream panel; here, print the dict)
5. The user confirms or edits it before it is applied

**Advantages:**
- Works with any rig structure
- No manual configuration required
- Name matching handles various conventions
- The review step keeps it accurate

**Similarity algorithm:**
- Base matching with `SequenceMatcher`
- Bonus for substring matches
- Bonus for common prefixes (left, right, upper, lower)
- Bonus for common suffixes (.L, .R, _l, _r)
- Bonus for number matching (Spine1, Spine2)
- Bonus for anatomical keywords (arm, leg, hand, foot)

### 2. Rigify mode

**When to use:** standard Rigify rigs.

```python
bm = get_preset_bone_mapping("mixamo_to_rigify")
```

Upstream only:

```bash
blender-toolkit retarget --target "Hero" --file "./Walking.fbx" --mapping mixamo_to_rigify
```

**How it works:**
- Uses a predefined Mixamo to Rigify bone map
- Meant for the standard Rigify control rig structure
- Instant map, no matching pass

**Advantages:**
- No configuration for Rigify users
- High accuracy on Rigify rigs
- Can be applied without the review step

**The preset the shipped `retargeting.py` holds** is ten bones, with deform-style names:

```
Mixamo              Rigify (shipped preset)
--------            ------
Hips                torso
Spine               spine
Spine1              spine.001
Spine2              spine.002
Neck                neck
Head                head
LeftShoulder        shoulder.L
LeftArm             upper_arm.L
LeftForeArm         forearm.L
LeftHand            hand.L
```

It stops at the left hand; the right arm, the legs and the fingers are not in it, so extend it before use. The upstream guide lists the FK control names instead (`hips`, `spine_fk`, `upper_arm_fk.L`, ...); that fuller table is under "Common mapping patterns". Pick the set that matches the bones your rig actually has.

### 3. Custom mode

**When to use:** unique rig structures with a known map.

```python
custom_mapping = {
    "Hips": "Root",
    "Spine": "Torso_01",
    "Spine1": "Torso_02",
    "LeftArm": "L_UpperArm",
    "RightArm": "R_UpperArm",
}
retarget_animation("Armature", "MyCharacter", bone_map=custom_mapping)
```

Upstream only (TypeScript workflow):

```typescript
// In your workflow code
const customMapping = {
  "Hips": "Root",
  "Spine": "Torso_01",
  "Spine1": "Torso_02",
  "LeftArm": "L_UpperArm",
  "RightArm": "R_UpperArm"
};

await workflow.run({
  targetCharacterArmature: 'MyCharacter',
  animationFilePath: './Walking.fbx',
  boneMapping: customMapping
});
```

**Advantages:**
- Full control over the map
- Reusable across many animations
- No confirmation needed when the map is trusted

---

## Auto bone matching algorithm

The fuzzy matching algorithm pairs bones of the Mixamo skeleton with bones of your character rig.

### Phase 1: normalization

All bone names are normalized before comparison (measured):

```python
# Input variations
"Left_Arm"    → "left_arm"
"left-arm"    → "left_arm"
"LeftArm"     → "leftarm"
"Left Arm"    → "left_arm"
"left.arm"    → "left.arm"   # dots are kept
```

**Normalization steps:**
1. Convert to lower case
2. Replace special characters with an underscore (letters, digits and dots are kept)
3. Collapse consecutive underscores
4. Strip leading and trailing underscores

The upstream guide showed `"left.arm"` becoming `"left_arm"`. The code keeps the dot, which is what lets the `.l` and `.r` suffix bonus work.

### Phase 2: similarity calculation

Calculates a similarity score (0.0 to 1.0) between two bone names:

```python
def calculate_similarity(name1: str, name2: str) -> float:
    # Base score from SequenceMatcher
    base_score = SequenceMatcher(None, norm1, norm2).ratio()

    # Bonus factors
    bonus = 0.0

    # Substring match: +0.15
    if norm1 in norm2 or norm2 in norm1:
        bonus += 0.15

    # Prefix match (left, right, etc): +0.1
    # Suffix match (.L, .R, etc): +0.1
    # Number match (Spine1, Spine2): +0.1
    # Keyword match (arm, leg, etc): +0.05

    return min(base_score + bonus, 1.0)
```

**Example scores (measured):**

```
"LeftArm" ↔ "left_arm"     = 1.000  (prefix + keyword, capped at 1.0)
"LeftArm" ↔ "L_Arm"        = 0.717  (keyword)
"LeftArm" ↔ "LeftLeg"      = 0.671  (prefix only)
"LeftArm" ↔ "RightArm"     = 0.583  (keyword only)
"LeftArm" ↔ "Head"         = 0.364  (no bonus)
```

The upstream guide gave illustrative values here (0.95, 0.78, 0.65, 0.42, 0.15) that the code does not produce. The measured ones matter for one reason: `LeftArm` against `LeftLeg` is above the default threshold of 0.6, while `LeftArm` against `RightArm` is below it. A shared side prefix counts for more than a shared limb keyword, so a missing arm bone in the target can pull a leg bone of the same side into the map.

### Phase 3: best match selection

Selects the best match for each source bone:

```python
def find_best_match(source_bone, target_bones, threshold=0.6):
    best_match = None
    best_score = 0.0

    for target_bone in target_bones:
        score = calculate_similarity(source_bone, target_bone)

        if score > best_score and score >= threshold:
            best_score = score
            best_match = target_bone

    return best_match
```

**Key points:**
- Only matches at or above the threshold (default 0.6) are considered
- Each target bone can be matched only once (no double mapping)
- Returns `None` when no suitable match is found
- In `fuzzy_match_bones`, exact alias matches are taken first; the fuzzy pass only fills what is left

### Phase 4: quality assessment

Rates the whole map by its critical bones:

```python
critical_bones = [
    'Hips',       # Root motion
    'Spine',      # Torso
    'Head',       # Head orientation
    'LeftArm',    # Upper body
    'RightArm',
    'LeftLeg',    # Lower body
    'RightLeg',
    'LeftHand',   # Extremities
    'RightHand'
]

if critical_mapped >= 8:
    quality = 'excellent'  # Safe to auto-apply
elif critical_mapped >= 6:
    quality = 'good'       # Quick review recommended
elif critical_mapped >= 4:
    quality = 'fair'       # Thorough review required
else:
    quality = 'poor'       # Manual mapping needed
```

The rating counts which of those nine source names have an entry. It does not check that the entry is the right bone.

---

## Two-phase workflow

The toolkit uses a two-phase workflow so the map is right before anything is baked.

### Phase 1: generate and display

**What happens:**
1. Import the animation FBX into Blender
2. Auto-generate the bone map with fuzzy matching
3. Calculate the quality rating
4. Show the map (upstream: in the Blender panel; here: print it)

**The upstream panel shows:**
- The complete bone mapping table
- Source bone to target bone correspondence
- An editable dropdown for each entry
- The quality rating
- An "Auto Re-map" button (regenerate)
- An "Apply Retargeting" button (go to phase 2)

**User actions:**
- Review each bone correspondence
- Fix wrong entries
- Regenerate if needed
- Apply when satisfied

### Phase 2: apply and bake

**What happens:**
1. The user applies the map (upstream: "Apply Retargeting"; here: `retarget_animation`)
2. A constraint-based retargeting setup is created
3. The animation is baked to keyframes
4. The animation is added to an NLA track (here: call `add_to_nla` yourself)
5. Temporary constraints are cleared by the bake

**Result:**
- A retargeted animation on your character
- The animation stored in an NLA track
- The original character rig unchanged
- Ready for further editing or export

---

## Quality assessment

The system rates the map automatically.

### Quality metrics

**Total mappings:**
- Number of bones mapped
- Higher is better

**Critical bones mapped:**
- Nine essential bones for a usable animation
- Shown as a ratio: "7/9 critical bones"

**Quality rating:**

| Rating | Critical bones | Recommendation |
|--------|----------------|----------------|
| **Excellent** | 8-9 | Safe to auto-apply, skipping confirmation |
| **Good** | 6-7 | Quick review recommended |
| **Fair** | 4-5 | Thorough review required |
| **Poor** | 0-3 | Manual mapping required |

### Quality report example

```json
{
  "total_mappings": 52,
  "critical_bones_mapped": "8/9",
  "quality": "excellent",
  "summary": "52 bones mapped, 8/9 critical bones"
}
```

### When to review the map

**Always review if:**
- Quality is "Fair" or "Poor"
- The character uses a non-standard rig
- The animation has unusual requirements
- It is the first time with a new character rig

**Quick review if:**
- Quality is "Good"
- The character is standard Rigify
- Similar maps worked before

**Auto-apply if:**
- Quality is "Excellent"
- You are using a trusted custom map
- You are repeating animations on the same character

In this skill the review is never skipped on a first map for a rig (see the two-phase rule in `SKILL.md`).

---

## Blender review panel (upstream only)

The upstream add-on shows a bone mapping panel in Blender's 3D View sidebar. It is not shipped here; its role is taken by printing and editing the map dict.

### Location

**Path:** View3D, Sidebar (N key), "Blender Toolkit" tab, "Bone Mapping Review"

### Panel components

**1. Mapping table**
```
┌─────────────────────────────────┐
│ Bone Mapping Review             │
├─────────────────────────────────┤
│ Source Bone    → Target Bone    │
│ ─────────────────────────────── │
│ Hips           → [Dropdown: Hips]│
│ Spine          → [Dropdown: Spine]│
│ LeftArm        → [Dropdown: LeftArm]│
│ ...                             │
└─────────────────────────────────┘
```

**2. Quality info**
```
Quality: Excellent
Total: 52 mappings
Critical: 8/9 bones
```

**3. Action buttons**
- **Auto Re-map**: regenerate the map
- **Apply Retargeting**: apply it

### Using the panel

**Step 1: open the panel**
```
1. Press the N key in the 3D View
2. Click the "Blender Toolkit" tab
3. Find the "Bone Mapping Review" panel
```

**Step 2: review the map**
```
1. Scroll through the mapping table
2. Check each source to target correspondence
3. Pay special attention to critical bones:
   - Hips (root motion)
   - Spine chain (posture)
   - Arms and legs (animation transfer)
```

**Step 3: edit the map**
```
1. Click the dropdown next to a wrong entry
2. Select the correct target bone from the list
3. Repeat for every wrong entry
```

**Step 4: apply**
```
1. Click the "Apply Retargeting" button
2. Wait for processing (progress is shown in the console)
3. The animation is applied and baked
```

---

## Common mapping patterns

### Rigify rigs

**Standard Rigify control rig (FK controls):**
```
Mixamo              Rigify
--------            ------
Hips                hips
Spine               spine_fk
Spine1              spine_fk.001
Spine2              spine_fk.002
Neck                neck
Head                head

LeftShoulder        shoulder.L
LeftArm             upper_arm_fk.L
LeftForeArm         forearm_fk.L
LeftHand            hand_fk.L

RightShoulder       shoulder.R
RightArm            upper_arm_fk.R
RightForeArm        forearm_fk.R
RightHand           hand_fk.R

LeftUpLeg           thigh_fk.L
LeftLeg             shin_fk.L
LeftFoot            foot_fk.L

RightUpLeg          thigh_fk.R
RightLeg            shin_fk.R
RightFoot           foot_fk.R
```

### Unreal Engine (UE4 and UE5)

**UE4 Mannequin skeleton:**
```
Mixamo              UE4/UE5
--------            -------
Hips                pelvis
Spine               spine_01
Spine1              spine_02
Spine2              spine_03
Neck                neck_01
Head                head

LeftShoulder        clavicle_l
LeftArm             upperarm_l
LeftForeArm         lowerarm_l
LeftHand            hand_l

RightShoulder       clavicle_r
RightArm            upperarm_r
RightForeArm        lowerarm_r
RightHand           hand_r
```

### Unity Humanoid

**Unity Mecanim Humanoid:**
```
Mixamo              Unity
--------            -----
Hips                Hips
Spine               Spine
Spine1              Chest
Spine2              UpperChest
Neck                Neck
Head                Head

LeftShoulder        LeftShoulder
LeftArm             LeftUpperArm
LeftForeArm         LeftLowerArm
LeftHand            LeftHand
```

---

## Troubleshooting

### "Poor quality" map

**Symptoms:**
- The quality rating is "Poor"
- Fewer than 4 critical bones mapped

**Solutions:**
1. **Check the rig structure**
   - Verify the character has a proper armature
   - Make sure the bones follow a hierarchy
   - Check for missing bones

2. **Use a custom map**
   - Write an explicit bone map dictionary
   - Test with a known-good map first

3. **Review the bone names**
   - Check for unusual naming conventions
   - Look for typos or special characters
   - Check for a `mixamorig:` prefix on the source bones: `auto_map_bones` only reads source bones named exactly like its alias keys, so a prefixed armature maps nothing (see "Known gaps" in `SKILL.md`)

### Wrong left and right mapping

**Symptoms:**
- Left arm mapped to right arm
- Crossed animations

**Solutions:**
1. **Check the suffix convention**
   - Use .L/.R or _l/_r consistently
   - Verify the suffix matches through the whole rig

2. **Manual correction**
   - Swap the entries in the map (upstream: in the Blender panel)
   - Fix all left and right pairs

### Missing critical bones

**Symptoms:**
- Key bones not mapped (Hips, Spine and so on)
- The animation does not transfer properly

**Solutions:**
1. **Lower the threshold**
   ```python
   # In a custom workflow
   bone_map = fuzzy_match_bones(
       source_bones,
       target_bones,
       threshold=0.5  # Lower than the default 0.6
   )
   ```

2. **Check the bone names**
   - Print all bone names in the Blender console
   - Verify the expected bones exist

3. **Use an explicit map**
   - Map the critical bones by hand
   - Let auto-match handle fingers and toes

### Twisted or inverted limbs

**Symptoms:**
- Arms twist incorrectly
- Legs bend backwards

**Causes:**
- Bone roll differences
- Constraint axis misalignment

**Solutions:**
1. **Check the bone roll**
   - Compare source and target bone rolls
   - Adjust in Edit Mode if needed

2. **Post-process the animation**
   - Use constraint influence
   - Add corrective keyframes

---

## Best practices

### 1. Start simple

**First animation:**
- Use a simple animation (Idle, Walking)
- Verify the map quality
- Test full body movement
- Check for issues before complex animations

### 2. Review critical bones first

**Priority order:**
1. **Hips**: root motion and posture
2. **Spine chain**: torso movement
3. **Shoulders**: upper body orientation
4. **Arms and legs**: limb movement
5. **Hands and feet**: extremity position
6. **Fingers and toes**: fine detail (optional)

### 3. Save custom maps

**For reuse** (here: keep the reviewed dict, or save it as JSON next to the `.blend`):

```python
import json
with open(r"<path-to>\hero_bone_map.json", "w", encoding="utf-8") as handle:
    json.dump(bm, handle, indent=2)
```

Upstream only (TypeScript workflow):

```typescript
// Save successful mapping
const myCharacterMapping = {
  "Hips": "root_bone",
  "Spine": "torso_01",
  // ... complete mapping
};

// Reuse for all animations
await workflow.run({
  boneMapping: myCharacterMapping,
  skipConfirmation: true  // Safe with known mapping
});
```

### 4. Use a quality threshold

**Decide the confirmation strategy** (upstream only, TypeScript workflow):
```typescript
// Auto-apply only for excellent quality
if (quality === 'excellent') {
  skipConfirmation = true;
} else {
  skipConfirmation = false;  // Review in UI
}
```

### 5. Document your rigs

**Write a mapping reference:**
```markdown
# Character: Hero
Rig Type: Custom
Created: 2024-01-15

## Bone Mapping
Mixamo → Hero
- Hips → root
- Spine → spine_01
- ...

## Notes
- Uses custom spine chain (4 bones)
- Left/Right suffix: _L / _R
- Tested with: Walking, Running, Jumping
```

### 6. Test before batch processing

**Workflow:**
1. Test the map with one animation
2. Verify quality and appearance
3. Save the map
4. Batch process the remaining animations

### 7. Handle edge cases

**Preparation:**
- Write fallback maps for unusual rigs
- Document special handling requirements
- Test with varied animation types
