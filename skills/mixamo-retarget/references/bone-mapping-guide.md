# Bone mapping guide

How the automatic bone matching works for animation retargeting, how to review a map, the common naming patterns per rig family, and how to fix bad matches.

This is a guide to a Blender tool, not to the game, so it cites no vanilla file. Every step runs as a Python call through the Blender MCP (see `SKILL.md`); there is no command line and no Blender panel, so the map is reviewed by printing and editing the dict. Scores and outputs marked "measured" were produced with the shipped `bone_matching.py`.

## Contents

- [Overview](#overview)
- [Bone mapping modes](#bone-mapping-modes)
- [Auto bone matching algorithm](#auto-bone-matching-algorithm)
- [Two-phase workflow](#two-phase-workflow)
- [Quality assessment](#quality-assessment)
- [Reviewing the map](#reviewing-the-map)
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

**How it works:**
1. Reads the bone names of the source (Mixamo) and the target (your character)
2. Uses the fuzzy matching algorithm to find the best matches
3. Builds the map and prints its quality rating
4. Returns the map; print the dict to review it
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

**When to use:** as a starting point for a Rigify rig, after fixing it against that rig's bone list.

```python
bm = get_preset_bone_mapping("mixamo_to_rigify")
```

**How it works:**
- Uses a predefined Mixamo to Rigify bone map
- Instant map, no matching pass

**As shipped, the preset matches neither Rigify rig.** It mixes names from the generated control rig (`torso`, `neck`, `head`, `shoulder.L`) with names that exist only in the metarig (`spine`, `spine.001`, `spine.002`, `upper_arm.L`, `forearm.L`, `hand.L`). On either rig some entries name no bone, and `retarget_animation` skips those entries without a warning. Before use, print the bone names of the actual target rig and correct every entry against that list.

**The preset the shipped `retargeting.py` holds** is ten bones, named as below:

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

It stops at the left hand; the right arm, the legs and the fingers are not in it, so extend it before use. A fuller table that uses the FK control names instead (`hips`, `spine_fk`, `upper_arm_fk.L`, ...) is under "Common mapping patterns". Pick the set that matches the bones your rig actually has.

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

The dot is kept on purpose: it is what lets the `.l` and `.r` suffix bonus work.

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

These values matter for one reason: `LeftArm` against `LeftLeg` is above the default threshold of 0.6, while `LeftArm` against `RightArm` is below it. A shared side prefix counts for more than a shared limb keyword, so a missing arm bone in the target can pull a leg bone of the same side into the map.

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
    quality = 'excellent'  # Quick review still required
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

The skill uses a two-phase workflow so the map is right before anything is baked.

### Phase 1: generate and display

**What happens:**
1. Import the animation FBX into Blender (`import_fbx`)
2. Auto-generate the bone map with fuzzy matching (`auto_map_bones`)
3. The quality rating is printed
4. Print the map

**User actions:**
- Review each bone correspondence (see "Reviewing the map")
- Fix wrong entries in the dict
- Regenerate if needed
- Apply when satisfied

### Phase 2: apply and bake

**What happens:**
1. The user applies the map with `retarget_animation`
2. A constraint-based retargeting setup is created
3. The animation is baked to keyframes over the scene frame range
4. Temporary constraints are cleared by the bake
5. To stack the result, call `add_to_nla` yourself; `retarget_animation` does not add an NLA track

**Result:**
- A retargeted action on your character
- The bones of the rig unchanged; only keyframes are added
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
| **Excellent** | 8-9 | Review still required; the rating does not check that entries are correct |
| **Good** | 6-7 | Quick review recommended |
| **Fair** | 4-5 | Thorough review required |
| **Poor** | 0-3 | Manual mapping required |

### Quality report example

```json
{
  "total_mappings": 47,
  "critical_bones_mapped": "8/9",
  "quality": "excellent",
  "summary": "47 bones mapped, 8/9 critical bones"
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

**Apply without review only if:**
- You load a stored map that was already reviewed for the same pair of rigs

A map from the fuzzy pass is always reviewed, whatever its rating (see the two-phase rule in `SKILL.md`).

---

## Reviewing the map

There is no review panel; the map is a Python dict that is printed, edited and passed to `retarget_animation`.

**Step 1: print the map and its quality**

```python
bm = auto_map_bones("Armature", "Hero")   # prints the quality, the total and the critical-bone ratio
for source_bone, target_bone in bm.items():
    print(source_bone, "->", target_bone)
```

`auto_map_bones` prints three lines of this shape (the first one starts with a check mark character):

```
Auto-mapped 47 bones
   Quality: EXCELLENT
   Critical bones: 8/9
```

**Step 2: review the map**

1. Go through every entry
2. Check each source to target correspondence against the bone list of the target (`get_bones("Hero")`)
3. Pay special attention to the critical bones:
   - Hips (root motion)
   - Spine chain (posture)
   - Arms and legs (animation transfer)

**Step 3: edit the map**

```python
bm["LeftArm"] = "upper_arm.L"   # replace a wrong entry
del bm["LeftToeBase"]           # drop an entry that has no counterpart
```

Repeat for every wrong entry. To regenerate from scratch, call `auto_map_bones` again.

**Step 4: apply**

```python
retarget_animation("Armature", "Hero", bone_map=bm)
```

The animation is applied and baked.

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
   - Check for a `mixamorig:` prefix on the source bones: `auto_map_bones` only reads source bones named exactly like its alias keys, so a prefixed armature maps nothing and the call ends in `KeyError: 'critical_bones_mapped'` (see "Known gaps" in `SKILL.md`)

### Wrong left and right mapping

**Symptoms:**
- Left arm mapped to right arm
- Crossed animations

**Solutions:**
1. **Check the suffix convention**
   - Use .L/.R or _l/_r consistently
   - Verify the suffix matches through the whole rig

2. **Manual correction**
   - Swap the entries in the map dict
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

**For reuse**, keep the reviewed dict, or save it as JSON next to the `.blend`:

```python
import json
with open(r"<path-to>\hero_bone_map.json", "w", encoding="utf-8") as handle:
    json.dump(bm, handle, indent=2)
```

Load it again for every later animation on the same pair of rigs; a map that was reviewed once does not need a second review:

```python
with open(r"<path-to>\hero_bone_map.json", encoding="utf-8") as handle:
    bm = json.load(handle)
retarget_animation("Armature", "Hero", bone_map=bm)
```

### 4. Use a quality threshold

**Use the rating to set how deep the review goes**, never to skip it: every map from the fuzzy pass is reviewed, and only a stored map that was already reviewed is reused without review.

```python
report = get_match_quality_report(bm)
thorough_review = report["quality"] in ("fair", "poor")
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
