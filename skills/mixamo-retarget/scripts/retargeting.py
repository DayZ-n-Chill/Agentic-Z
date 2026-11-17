"""
Animation Retargeting Module
Functions for retargeting animation in Blender.

Main features:
- Armature and bone queries
- Automatic bone mapping (fuzzy matching)
- Animation retargeting
- Animation playback and NLA track management
- FBX and DAE import
- Storing and loading bone maps
"""

import os
from typing import Dict, List, Optional

import bpy

# Fuzzy bone matching utilities
from bone_matching import (
    fuzzy_match_bones,
    get_match_quality_report,
)

# Logging utilities
import logging
def get_logger(name): return logging.getLogger(name)

# Module logger
logger = get_logger('retargeting')


# ============================================================================
# Armature & Bone Query Functions
# ============================================================================

def list_armatures() -> List[str]:
    """
    Return the names of all armature objects.

    Returns:
        List of armature object names
    """
    return [obj.name for obj in bpy.data.objects if obj.type == 'ARMATURE']


def get_bones(armature_name: str) -> List[Dict[str, Optional[str]]]:
    """
    Get the bones of an armature.

    Args:
        armature_name: Name of the armature object

    Returns:
        List of bone records (name, parent, children)

    Raises:
        ValueError: If the armature is not found
    """
    armature = bpy.data.objects.get(armature_name)
    if not armature or armature.type != 'ARMATURE':
        raise ValueError(f"Armature '{armature_name}' not found")

    bones = []
    for bone in armature.data.bones:
        bones.append({
            "name": bone.name,
            "parent": bone.parent.name if bone.parent else None,
            "children": [child.name for child in bone.children]
        })

    return bones


# ============================================================================
# Bone Mapping Functions
# ============================================================================

def auto_map_bones(source_armature: str, target_armature: str) -> Dict[str, str]:
    """
    Map bones automatically (Mixamo -> the user's character).
    Uses the fuzzy matching algorithm for better accuracy.

    Args:
        source_armature: Name of the source armature (for example Mixamo)
        target_armature: Name of the target armature (the user's character)

    Returns:
        Bone map dictionary {source bone: target bone}

    Raises:
        ValueError: If the armature is not found
    """
    source = bpy.data.objects.get(source_armature)
    target = bpy.data.objects.get(target_armature)

    if not source or not target:
        raise ValueError("Source or target armature not found")

    # Standard Mixamo bone names and their known aliases (extended: fingers and toes included)
    mixamo_bone_aliases = {
        # Torso (6)
        "Hips": ["hips", "pelvis", "root"],
        "Spine": ["spine", "spine1"],
        "Spine1": ["spine1", "spine2"],
        "Spine2": ["spine2", "spine3", "chest"],
        "Neck": ["neck"],
        "Head": ["head"],

        # Left arm (4)
        "LeftShoulder": ["shoulder.l", "clavicle.l", "leftshoulder"],
        "LeftArm": ["upper_arm.l", "leftarm", "upperarm.l"],
        "LeftForeArm": ["forearm.l", "leftforearm", "lowerarm.l"],
        "LeftHand": ["hand.l", "lefthand"],

        # Right arm (4)
        "RightShoulder": ["shoulder.r", "clavicle.r", "rightshoulder"],
        "RightArm": ["upper_arm.r", "rightarm", "upperarm.r"],
        "RightForeArm": ["forearm.r", "rightforearm", "lowerarm.r"],
        "RightHand": ["hand.r", "righthand"],

        # Left leg (4)
        "LeftUpLeg": ["thigh.l", "leftupleg", "upperleg.l"],
        "LeftLeg": ["shin.l", "leftleg", "lowerleg.l"],
        "LeftFoot": ["foot.l", "leftfoot"],
        "LeftToeBase": ["toe.l", "lefttoebase", "foot.l.001"],

        # Right leg (4)
        "RightUpLeg": ["thigh.r", "rightupleg", "upperleg.r"],
        "RightLeg": ["shin.r", "rightleg", "lowerleg.r"],
        "RightFoot": ["foot.r", "rightfoot"],
        "RightToeBase": ["toe.r", "righttoebase", "foot.r.001"],

        # Left fingers (15)
        "LeftHandThumb1": ["thumb.01.l", "lefthandthumb1", "thumb_01.l"],
        "LeftHandThumb2": ["thumb.02.l", "lefthandthumb2", "thumb_02.l"],
        "LeftHandThumb3": ["thumb.03.l", "lefthandthumb3", "thumb_03.l"],
        "LeftHandIndex1": ["f_index.01.l", "lefthandindex1", "index_01.l"],
        "LeftHandIndex2": ["f_index.02.l", "lefthandindex2", "index_02.l"],
        "LeftHandIndex3": ["f_index.03.l", "lefthandindex3", "index_03.l"],
        "LeftHandMiddle1": ["f_middle.01.l", "lefthandmiddle1", "middle_01.l"],
        "LeftHandMiddle2": ["f_middle.02.l", "lefthandmiddle2", "middle_02.l"],
        "LeftHandMiddle3": ["f_middle.03.l", "lefthandmiddle3", "middle_03.l"],
        "LeftHandRing1": ["f_ring.01.l", "lefthandring1", "ring_01.l"],
        "LeftHandRing2": ["f_ring.02.l", "lefthandring2", "ring_02.l"],
        "LeftHandRing3": ["f_ring.03.l", "lefthandring3", "ring_03.l"],
        "LeftHandPinky1": ["f_pinky.01.l", "lefthandpinky1", "pinky_01.l"],
        "LeftHandPinky2": ["f_pinky.02.l", "lefthandpinky2", "pinky_02.l"],
        "LeftHandPinky3": ["f_pinky.03.l", "lefthandpinky3", "pinky_03.l"],

        # Right fingers (15)
        "RightHandThumb1": ["thumb.01.r", "righthandthumb1", "thumb_01.r"],
        "RightHandThumb2": ["thumb.02.r", "righthandthumb2", "thumb_02.r"],
        "RightHandThumb3": ["thumb.03.r", "righthandthumb3", "thumb_03.r"],
        "RightHandIndex1": ["f_index.01.r", "righthandindex1", "index_01.r"],
        "RightHandIndex2": ["f_index.02.r", "righthandindex2", "index_02.r"],
        "RightHandIndex3": ["f_index.03.r", "righthandindex3", "index_03.r"],
        "RightHandMiddle1": ["f_middle.01.r", "righthandmiddle1", "middle_01.r"],
        "RightHandMiddle2": ["f_middle.02.r", "righthandmiddle2", "middle_02.r"],
        "RightHandMiddle3": ["f_middle.03.r", "righthandmiddle3", "middle_03.r"],
        "RightHandRing1": ["f_ring.01.r", "righthandring1", "ring_01.r"],
        "RightHandRing2": ["f_ring.02.r", "righthandring2", "ring_02.r"],
        "RightHandRing3": ["f_ring.03.r", "righthandring3", "ring_03.r"],
        "RightHandPinky1": ["f_pinky.01.r", "righthandpinky1", "pinky_01.r"],
        "RightHandPinky2": ["f_pinky.02.r", "righthandpinky2", "pinky_02.r"],
        "RightHandPinky3": ["f_pinky.03.r", "righthandpinky3", "pinky_03.r"],
    }

    # Source bone list (only bones that actually exist)
    source_bones = [bone.name for bone in source.data.bones
                    if bone.name in mixamo_bone_aliases]

    # Target bone list
    target_bones = [bone.name for bone in target.data.bones]

    # Run fuzzy matching (exact matches first, then similarity matches)
    logger.info("Running fuzzy bone matching algorithm...")
    logger.debug("Source bones: %d, Target bones: %d", len(source_bones), len(target_bones))

    bone_map = fuzzy_match_bones(
        source_bones=source_bones,
        target_bones=target_bones,
        known_aliases=mixamo_bone_aliases,
        threshold=0.6,  # similarity of 60% or more
        prefer_exact=True  # exact matches first
    )

    # Match quality report
    quality_report = get_match_quality_report(bone_map)
    logger.info("Auto-mapped %d bones", quality_report['total_mappings'])
    logger.info("Quality: %s", quality_report['quality'].upper())
    logger.info("Critical bones: %s", quality_report['critical_bones_mapped'])
    logger.debug("Bone mapping: %s", bone_map)

    # Console output (feedback for the user)
    print(f"✅ Auto-mapped {quality_report['total_mappings']} bones")
    print(f"   Quality: {quality_report['quality'].upper()}")
    print(f"   Critical bones: {quality_report['critical_bones_mapped']}")

    return bone_map


def get_preset_bone_mapping(preset: str) -> Dict[str, str]:
    """
    Return a predefined bone map preset.

    Args:
        preset: Preset name (for example "mixamo_to_rigify")

    Returns:
        Bone map dictionary
    """
    presets = {
        "mixamo_to_rigify": {
            "Hips": "torso",
            "Spine": "spine",
            "Spine1": "spine.001",
            "Spine2": "spine.002",
            "Neck": "neck",
            "Head": "head",
            "LeftShoulder": "shoulder.L",
            "LeftArm": "upper_arm.L",
            "LeftForeArm": "forearm.L",
            "LeftHand": "hand.L",
            # ... more mappings
        }
    }

    return presets.get(preset, {})


def store_bone_mapping(
    source_armature: str, target_armature: str, bone_mapping: Dict[str, str]
) -> str:
    """
    Store a bone map in Scene properties.

    Args:
        source_armature: Name of the source armature
        target_armature: Name of the target armature
        bone_mapping: Bone map dictionary

    Returns:
        Result message
    """
    scene = bpy.context.scene

    # Clear the existing map
    scene.bone_mapping_items.clear()

    # Store the new map
    for source_bone, target_bone in bone_mapping.items():
        item = scene.bone_mapping_items.add()
        item.source_bone = source_bone
        item.target_bone = target_bone

    # Store the armature names
    scene.bone_mapping_source_armature = source_armature
    scene.bone_mapping_target_armature = target_armature

    print(f"✅ Stored bone mapping: {len(bone_mapping)} bones")
    return f"Bone mapping stored ({len(bone_mapping)} bones)"


def load_bone_mapping(source_armature: str, target_armature: str) -> Dict[str, str]:
    """
    Load a bone map from Scene properties.

    Args:
        source_armature: Name of the source armature
        target_armature: Name of the target armature

    Returns:
        Bone map dictionary

    Raises:
        ValueError: If no map is stored or the armatures do not match
    """
    scene = bpy.context.scene

    # Check the armatures
    if not scene.bone_mapping_source_armature:
        raise ValueError(
            "No bone mapping stored. Store one first with store_bone_mapping."
        )

    if (scene.bone_mapping_source_armature != source_armature or
        scene.bone_mapping_target_armature != target_armature):
        raise ValueError(
            f"Stored mapping for ({scene.bone_mapping_source_armature} → "
            f"{scene.bone_mapping_target_armature}) doesn't match requested "
            f"({source_armature} → {target_armature})"
        )

    # Load the map
    bone_mapping = {}
    for item in scene.bone_mapping_items:
        bone_mapping[item.source_bone] = item.target_bone

    if not bone_mapping:
        raise ValueError("Bone mapping is empty. Please generate mapping first.")

    print(f"✅ Loaded bone mapping: {len(bone_mapping)} bones")
    return bone_mapping


# ============================================================================
# Animation Retargeting Functions
# ============================================================================

def retarget_animation(
    source_armature: str,
    target_armature: str,
    bone_map: Dict[str, str],
    preserve_rotation: bool = True,
    preserve_location: bool = False
) -> str:
    """
    Retarget the animation.

    Args:
        source_armature: Name of the source armature
        target_armature: Name of the target armature
        bone_map: Bone map dictionary
        preserve_rotation: Whether to copy rotation
        preserve_location: Whether to copy location

    Returns:
        Result message

    Raises:
        ValueError: If an armature is not found or the source has no animation
    """
    source = bpy.data.objects.get(source_armature)
    target = bpy.data.objects.get(target_armature)

    if not source or not target:
        raise ValueError("Source or target armature not found")

    if not source.animation_data or not source.animation_data.action:
        raise ValueError("Source armature has no animation")

    # Select the target armature
    bpy.context.view_layer.objects.active = target
    target.select_set(True)

    # Switch to Pose mode
    bpy.ops.object.mode_set(mode='POSE')

    # Create a constraint for each bone
    for source_bone_name, target_bone_name in bone_map.items():
        if source_bone_name not in source.pose.bones:
            continue
        if target_bone_name not in target.pose.bones:
            continue

        target_bone = target.pose.bones[target_bone_name]

        # Rotation constraint
        if preserve_rotation:
            constraint = target_bone.constraints.new('COPY_ROTATION')
            constraint.target = source
            constraint.subtarget = source_bone_name

        # Location constraint (normally the root bone only)
        if preserve_location and source_bone_name == "Hips":
            constraint = target_bone.constraints.new('COPY_LOCATION')
            constraint.target = source
            constraint.subtarget = source_bone_name

    # Bake the constraints to keyframes
    bpy.ops.nla.bake(
        frame_start=bpy.context.scene.frame_start,
        frame_end=bpy.context.scene.frame_end,
        only_selected=False,
        visual_keying=True,
        clear_constraints=True,
        bake_types={'POSE'}
    )

    bpy.ops.object.mode_set(mode='OBJECT')

    return f"Animation retargeted to {target_armature}"


# ============================================================================
# Animation Playback Functions
# ============================================================================

def list_animations(armature_name: str) -> List[str]:
    """
    Return the animation actions of an armature.

    Args:
        armature_name: Armature name

    Returns:
        List of action names

    Raises:
        ValueError: If the armature is not found
    """
    armature = bpy.data.objects.get(armature_name)
    if not armature:
        raise ValueError(f"Armature '{armature_name}' not found")

    actions = []
    if armature.animation_data:
        for action in bpy.data.actions:
            if action.id_root == 'OBJECT':
                actions.append(action.name)

    return actions


def play_animation(armature_name: str, action_name: str, loop: bool = True) -> str:
    """
    Play an animation.

    Args:
        armature_name: Armature name
        action_name: Action name
        loop: Whether to loop playback

    Returns:
        Result message

    Raises:
        ValueError: If the armature or the action is not found
    """
    armature = bpy.data.objects.get(armature_name)
    if not armature:
        raise ValueError(f"Armature '{armature_name}' not found")

    action = bpy.data.actions.get(action_name)
    if not action:
        raise ValueError(f"Action '{action_name}' not found")

    if not armature.animation_data:
        armature.animation_data_create()

    armature.animation_data.action = action
    bpy.context.scene.frame_set(int(action.frame_range[0]))
    bpy.ops.screen.animation_play()

    return f"Playing {action_name}"


def stop_animation() -> str:
    """
    Stop the animation.

    Returns:
        Result message
    """
    bpy.ops.screen.animation_cancel()
    return "Animation stopped"


def add_to_nla(armature_name: str, action_name: str, track_name: str) -> str:
    """
    Add an animation to an NLA track.

    Args:
        armature_name: Armature name
        action_name: Action name
        track_name: NLA track name

    Returns:
        Result message

    Raises:
        ValueError: If the armature or the action is not found
    """
    armature = bpy.data.objects.get(armature_name)
    action = bpy.data.actions.get(action_name)

    if not armature or not action:
        raise ValueError("Armature or action not found")

    if not armature.animation_data:
        armature.animation_data_create()

    nla_track = armature.animation_data.nla_tracks.new()
    nla_track.name = track_name
    nla_track.strips.new(action.name, int(action.frame_range[0]), action)

    return f"Added {action_name} to NLA track {track_name}"


# ============================================================================
# Import Functions
# ============================================================================

def import_fbx(filepath: str) -> str:
    """
    Import an FBX file.

    Args:
        filepath: Path of the FBX file

    Returns:
        Result message

    Raises:
        ValueError: If the file is not found
    """
    if not os.path.exists(filepath):
        raise ValueError(f"File not found: {filepath}")

    bpy.ops.import_scene.fbx(filepath=filepath)
    return f"Imported {filepath}"


def import_dae(filepath: str) -> str:
    """
    Import a Collada (.dae) file.

    Args:
        filepath: Path of the DAE file

    Returns:
        Result message

    Raises:
        ValueError: If the file is not found
    """
    if not os.path.exists(filepath):
        raise ValueError(f"File not found: {filepath}")

    bpy.ops.wm.collada_import(filepath=filepath)
    return f"Imported {filepath}"
