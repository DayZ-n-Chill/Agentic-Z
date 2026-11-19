"""Where Bohemia's vanilla script tree lives on this machine, if anywhere.

The tree is not redistributed, so every consumer must cope with its absence:
the vanilla control SKIPs, and ES-UNDEFINED-CLASS-REF reports itself as not
run instead of judging a reference it cannot resolve.
"""

import os
from pathlib import Path


PDRIVE_SCRIPTS = Path(r"P:\scripts")


def resolve_vanilla_root(explicit=None):
    """Return (path, None) or (None, reason).

    Order: the explicit argument, then DAYZ_VANILLA_ROOT, then P:\\scripts.
    An explicit or env path that is not a directory is a reason, never a
    silent fallback to the next candidate.
    """
    if explicit:
        path = Path(explicit)
        if path.is_dir():
            return path, None
        return None, "vanilla tree not found: %s" % explicit
    env = os.environ.get("DAYZ_VANILLA_ROOT")
    if env:
        path = Path(env)
        if path.is_dir():
            return path, None
        return None, "vanilla tree not found: %s (DAYZ_VANILLA_ROOT)" % env
    if PDRIVE_SCRIPTS.is_dir():
        return PDRIVE_SCRIPTS, None
    return (
        None,
        "vanilla tree not found. Set --vanilla-root or DAYZ_VANILLA_ROOT, "
        "or place the tree at P:\\scripts",
    )
