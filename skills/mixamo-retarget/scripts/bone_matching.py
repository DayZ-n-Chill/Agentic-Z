"""
Fuzzy Bone Matching Utilities
Automatic bone matching based on bone-name similarity.
"""

import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple, Union


def normalize_bone_name(name: str) -> str:
    """
    Normalize a bone name.
    - convert to lower case
    - replace special characters with an underscore
    - collapse consecutive underscores
    - strip underscores from both ends

    Examples:
        "Left_Arm" -> "left_arm"
        "left-arm" -> "left_arm"
        "LeftArm" -> "leftarm"
        "Left Arm" -> "left_arm"
    """
    # Lower case
    normalized = name.lower()

    # Replace special characters with an underscore (keep letters, digits and dots)
    normalized = re.sub(r'[^a-z0-9.]', '_', normalized)

    # Collapse consecutive underscores into one
    normalized = re.sub(r'_+', '_', normalized)

    # Strip underscores from both ends
    normalized = normalized.strip('_')

    return normalized


def calculate_similarity(name1: str, name2: str) -> float:
    """
    Similarity between two bone names (0.0 to 1.0).

    Algorithm:
    1. SequenceMatcher on the normalized names (base score)
    2. substring match bonus
    3. prefix and suffix match bonuses
    4. shared keyword bonus

    Args:
        name1: first bone name
        name2: second bone name

    Returns:
        Similarity score (0.0 = nothing in common, 1.0 = identical)
    """
    # Normalize
    norm1 = normalize_bone_name(name1)
    norm2 = normalize_bone_name(name2)

    # Exact match
    if norm1 == norm2:
        return 1.0

    # Base similarity from SequenceMatcher
    base_score = SequenceMatcher(None, norm1, norm2).ratio()

    # Bonus score
    bonus = 0.0

    # 1. Substring bonus (one name contains the other)
    if norm1 in norm2 or norm2 in norm1:
        bonus += 0.15

    # 2. Prefix bonus (left, right and so on)
    common_prefixes = ['left', 'right', 'up', 'low', 'upper', 'lower']
    for prefix in common_prefixes:
        if norm1.startswith(prefix) and norm2.startswith(prefix):
            bonus += 0.1
            break

    # 3. Suffix bonus (l, r and so on)
    underscore_l_match = norm1.endswith('_l') and norm2.endswith('_l')
    underscore_r_match = norm1.endswith('_r') and norm2.endswith('_r')
    dot_l_match = norm1.endswith('.l') and norm2.endswith('.l')
    dot_r_match = norm1.endswith('.r') and norm2.endswith('.r')

    if underscore_l_match or underscore_r_match or dot_l_match or dot_r_match:
        bonus += 0.1

    # 4. Number bonus (Spine1, Spine2 and so on)
    digits1 = re.findall(r'\d+', norm1)
    digits2 = re.findall(r'\d+', norm2)
    if digits1 and digits2 and digits1 == digits2:
        bonus += 0.1

    # 5. Keyword bonus (arm, hand, leg, foot and so on)
    keywords = ['arm', 'hand', 'leg', 'foot', 'finger', 'thumb', 'index',
                'middle', 'ring', 'pinky', 'shoulder', 'elbow', 'wrist',
                'hip', 'knee', 'ankle', 'toe', 'spine', 'neck', 'head']

    for keyword in keywords:
        if keyword in norm1 and keyword in norm2:
            bonus += 0.05
            break

    # Final score (capped at 1.0)
    final_score = min(base_score + bonus, 1.0)

    return final_score


def find_best_match(
    source_bone: str,
    target_bones: List[str],
    threshold: float = 0.6,
    return_score: bool = False
) -> Union[Optional[str], Tuple[Optional[str], float]]:
    """
    Find the most similar bone in a list of target bones.

    Args:
        source_bone: source bone name to match
        target_bones: list of target bone names
        threshold: minimum similarity (0.0 to 1.0)
        return_score: when True, return a (bone_name, score) tuple

    Returns:
        The most similar target bone name, or None (below the threshold);
        a (bone_name, score) tuple when return_score=True
    """
    best_match = None
    best_score = 0.0

    for target_bone in target_bones:
        score = calculate_similarity(source_bone, target_bone)

        if score > best_score and score >= threshold:
            best_score = score
            best_match = target_bone

    if return_score:
        return (best_match, best_score)

    return best_match


def fuzzy_match_bones(
    source_bones: List[str],
    target_bones: List[str],
    known_aliases: Dict[str, List[str]] = None,
    threshold: float = 0.6,
    prefer_exact: bool = True
) -> Dict[str, str]:
    """
    Map a whole skeleton with fuzzy matching.

    Algorithm:
    1. exact matches first (using known_aliases)
    2. fuzzy matching for the rest
    3. keep only matches at or above the threshold

    Args:
        source_bones: list of source bone names
        target_bones: list of target bone names
        known_aliases: known alias dictionary {source: [target_alias1, ...]}
        threshold: minimum similarity
        prefer_exact: when True, exact matches win

    Returns:
        Bone mapping dictionary {source_bone: target_bone}
    """
    bone_map = {}
    target_bone_names_lower = [b.lower() for b in target_bones]
    matched_targets = set()  # prevents matching one target twice

    # Step 1: exact matches (using known_aliases)
    if prefer_exact and known_aliases:
        for source_bone in source_bones:
            if source_bone not in known_aliases:
                continue

            # Find an alias that exists in the target
            for alias in known_aliases[source_bone]:
                alias_lower = alias.lower()
                if alias_lower in target_bone_names_lower:
                    idx = target_bone_names_lower.index(alias_lower)
                    actual_name = target_bones[idx]

                    # Add it unless the target is already matched
                    if actual_name not in matched_targets:
                        bone_map[source_bone] = actual_name
                        matched_targets.add(actual_name)
                        break

    # Step 2: fuzzy matching for the rest
    for source_bone in source_bones:
        # Skip source bones that are already matched
        if source_bone in bone_map:
            continue

        # Only target bones that are not matched yet
        available_targets = [t for t in target_bones if t not in matched_targets]

        if not available_targets:
            continue

        # Find the most similar target
        best_match, _ = find_best_match(
            source_bone,
            available_targets,
            threshold=threshold,
            return_score=True
        )

        if best_match:
            bone_map[source_bone] = best_match
            matched_targets.add(best_match)

    return bone_map


def get_match_quality_report(bone_map: Dict[str, str]) -> Dict[str, Any]:
    """
    Build a quality report for a bone mapping.

    Args:
        bone_map: bone mapping dictionary

    Returns:
        Quality report dictionary
    """
    if not bone_map:
        return {
            'total_mappings': 0,
            'quality': 'none',
            'summary': 'No bone mappings found'
        }

    total = len(bone_map)

    # Critical bones (the ones a usable mapping must have)
    critical_bones = ['Hips', 'Spine', 'Head', 'LeftArm', 'RightArm',
                      'LeftLeg', 'RightLeg', 'LeftHand', 'RightHand']
    critical_mapped = sum(1 for bone in critical_bones if bone in bone_map)

    # Quality rating
    if critical_mapped >= 8:
        quality = 'excellent'
    elif critical_mapped >= 6:
        quality = 'good'
    elif critical_mapped >= 4:
        quality = 'fair'
    else:
        quality = 'poor'

    return {
        'total_mappings': total,
        'critical_bones_mapped': f'{critical_mapped}/{len(critical_bones)}',
        'quality': quality,
        'summary': f'{total} bones mapped, {critical_mapped}/{len(critical_bones)} critical bones'
    }
