import hashlib

from .errors import AnimationFormatError
from .rtm import ANIMATION_SIGNATURE, MDAT_SIGNATURE, read_rtm_bytes
from .seanim import MAGIC as SEANIM_MAGIC, read_seanim_bytes


def inspect_bytes(data):
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("inspect data must be bytes-like")
    payload = bytes(data)
    if payload.startswith(SEANIM_MAGIC):
        document = read_seanim_bytes(payload)
        summary = {
            "anim_type": document["anim_type"],
            "bone_count": len(document["bones"]),
            "frame_count": document["frame_count"],
            "framerate": document["framerate"],
            "looped": document["looped"],
            "modifier_count": sum(
                bone["modifier"] is not None for bone in document["bones"]
            ),
            "note_count": len(document["notes"]),
            "position_key_count": sum(
                len(bone["position_keys"]) for bone in document["bones"]
            ),
            "precision": document["precision"],
            "rotation_key_count": sum(
                len(bone["rotation_keys"]) for bone in document["bones"]
            ),
            "scale_key_count": sum(
                len(bone["scale_keys"]) for bone in document["bones"]
            ),
        }
    elif payload.startswith((MDAT_SIGNATURE, ANIMATION_SIGNATURE)):
        document = read_rtm_bytes(payload)
        summary = {
            "bone_count": len(document["bones"]),
            "frame_count": len(document["frames"]),
            "metadata_count": len(document["metadata"]),
            "motion": document["motion"],
            "transform_count": sum(
                len(frame["transforms"]) for frame in document["frames"]
            ),
        }
    else:
        raise AnimationFormatError(
            "ANIM_FORMAT_UNSUPPORTED",
            "input is not SEAnim v1 or unbinarized RTM",
            0,
        )
    return {
        "format": document["format"],
        "schema_version": 1,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "summary": summary,
        "version": document["version"],
    }
