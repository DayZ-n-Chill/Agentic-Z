"""Strict DayZ animation interchange formats."""

from .errors import AnimationFormatError
from .rtm import read_rtm, read_rtm_bytes, write_rtm, write_rtm_bytes
from .seanim import (
    AnimType,
    read_seanim,
    read_seanim_bytes,
    write_seanim,
    write_seanim_bytes,
)


__all__ = [
    "AnimationFormatError",
    "AnimType",
    "read_rtm",
    "read_rtm_bytes",
    "read_seanim",
    "read_seanim_bytes",
    "write_rtm",
    "write_rtm_bytes",
    "write_seanim",
    "write_seanim_bytes",
]
